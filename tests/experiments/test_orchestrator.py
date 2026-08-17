from __future__ import annotations

from pathlib import Path

from problem2.experiments.orchestrator import Chapter45Orchestrator


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
