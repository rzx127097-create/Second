from __future__ import annotations

from pathlib import Path

import pytest

from problem2.experiments.orchestrator import Chapter45Orchestrator, select_jobs


ROOT = Path(__file__).resolve().parents[2]


def test_orchestrator_expands_all_families_with_protocol_bound_identities(tmp_path: Path) -> None:
    """Dropping conditions or protocol identity would make formal evidence incomplete."""
    orchestrator = Chapter45Orchestrator(ROOT / "configs", tmp_path)

    expected = {
        "main_comparison": 150,
        "mechanism": 90,
        "sensitivity": 150,
        "adaptation": 120,
        "ablation": 60,
    }
    for family, count in expected.items():
        jobs = orchestrator.plan(family, execution_profile="formal")
        assert len(jobs) == count
        assert len({job.identity.job_id for job in jobs}) == count
        assert all(job.identity.family == family for job in jobs)
        assert all(job.identity.protocol_hash == orchestrator.protocol_hash for job in jobs)
        assert all(job.identity.scenario_split == "train" for job in jobs)
        assert {job.identity.target_updates for job in jobs} == {
            int(orchestrator.config.algorithm["total_updates"]),
        }
        assert all(job.identity.target_updates > 0 for job in jobs)

    main = orchestrator.plan("main_comparison", execution_profile="smoke")[:5]
    assert {job.identity.method for job in main} == {
        "sr_mappo_mobile",
        "sr_mappo_fixed",
        "sr_mappo_astar",
        "mappo_mobile",
        "sr_mappo_two_stage",
    }
    assert {job.intervention.support_mode for job in main} == {"mobile", "fixed"}
    assert list(tmp_path.iterdir()) == []


def test_simulation_profile_uses_full_budget_and_differs_from_smoke(tmp_path: Path) -> None:
    orchestrator = Chapter45Orchestrator(ROOT / "configs", tmp_path)
    simulation = orchestrator.plan("main_comparison", execution_profile="simulation")
    smoke = orchestrator.plan("main_comparison", execution_profile="smoke")

    assert all(job.identity.execution_profile == "simulation" for job in simulation)
    assert {job.identity.target_updates for job in simulation} == {
        int(orchestrator.config.algorithm["total_updates"]),
    }
    assert {job.identity.rollout_horizon for job in simulation} == {
        int(orchestrator.config.algorithm["rollout_horizon"]),
    }
    assert simulation[0].identity.job_id != smoke[0].identity.job_id


def test_job_identity_changes_when_condition_or_protocol_changes(tmp_path: Path) -> None:
    orchestrator = Chapter45Orchestrator(ROOT / "configs", tmp_path)
    first = orchestrator.plan("sensitivity", execution_profile="smoke")[0].identity
    second = orchestrator.plan("sensitivity", execution_profile="smoke")[1].identity

    assert first.condition_id != second.condition_id
    assert first.job_id != second.job_id
    changed = first.__class__(
        **{**first.to_dict(), "protocol_hash": "f" * 64}
    )
    assert changed.job_id != first.job_id


def test_select_jobs_builds_canonical_m3_subset(tmp_path: Path) -> None:
    orchestrator = Chapter45Orchestrator(ROOT / "configs", tmp_path)
    planned = orchestrator.plan("main_comparison", execution_profile="simulation")
    selected = select_jobs(
        planned,
        scales=("s1", "s6"),
        methods=orchestrator.spec.main_methods,
        seeds=(0, 1, 2, 3, 4),
    )

    assert len(selected) == 50
    assert {job.identity.scale for job in selected} == {"s1", "s6"}
    assert {job.identity.method for job in selected} == set(orchestrator.spec.main_methods)
    assert {job.identity.training_seed for job in selected} == {0, 1, 2, 3, 4}
    assert selected == tuple(job for job in planned if job.identity.scale in {"s1", "s6"})
    assert all(job.identity.condition_id != "direct" for job in selected)


def test_select_jobs_normalizes_duplicates_and_rejects_unknowns(tmp_path: Path) -> None:
    orchestrator = Chapter45Orchestrator(ROOT / "configs", tmp_path)
    planned = orchestrator.plan("main_comparison", execution_profile="simulation")

    assert len(select_jobs(planned, scales=("s1", "s1"), seeds=(0, 0))) == 5
    with pytest.raises(ValueError, match="unknown scale.*s9"):
        select_jobs(planned, scales=("s9",))
    with pytest.raises(ValueError, match="unknown method.*happpo"):
        select_jobs(planned, methods=("happpo",))
    with pytest.raises(ValueError, match="unknown seed.*99"):
        select_jobs(planned, seeds=(99,))
