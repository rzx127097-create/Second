from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from problem2.experiments.g5_contract import load_g5_contract
from problem2.experiments.identity import canonical_training_identity, canonical_training_serialization, experiment_identity
from problem2.experiments.matrix import build_training_graph, TrainingGraph
from problem2.experiments.ablation import validate_ablation_diff
from problem2.experiments.sensitivity import validate_sensitivity_diff


ROOT = Path(__file__).resolve().parents[2]
SCALES = (
    "g20x20_d2", "g20x30_d3", "g20x40_d3",
    "g30x30_d3", "g30x40_d4", "g30x50_d4",
)
SEEDS = (42, 123, 2024, 3407, 7919)


def test_g1_identity_serialization_is_preserved_and_family_binding_is_additive() -> None:
    base = canonical_training_identity("sr_mappo_mobile", "g20x20_d2", 42, "cfg", "commit")
    raw = canonical_training_serialization("sr_mappo_mobile", "g20x20_d2", 42, "cfg", "commit")
    assert base == hashlib.sha256(raw.encode()).hexdigest()
    bound = experiment_identity("algorithm_scale", "sr_mappo_mobile", "protocol", base)
    assert bound == "algorithm_scale|sr_mappo_mobile|protocol|" + base


def test_training_graph_has_exact_scale_seed_coverage_and_deduplicated_counts() -> None:
    graph = build_training_graph(load_g5_contract(ROOT))
    assert isinstance(graph, TrainingGraph)
    assert len(graph.unique_jobs) == 375
    base = [job for job in graph.unique_jobs if job.family == "algorithm_scale"]
    assert len(base) == 150
    assert {(job.scale, job.training_seed) for job in base} == set((s, seed) for s in SCALES for seed in SEEDS)
    assert {job.method for job in base} == {
        "sr_mappo_mobile", "mappo_mobile", "ippo_mobile", "maddpg_mobile", "iql_mobile"
    }
    assert graph.family_counts == {
        "algorithm_convergence": 0,
        "algorithm_scale": 150,
        "problem2_required": 90,
        "vehicle_heuristics": 60,
        "sr_mappo_ablation": 25,
        "sr_mappo_sensitivity": 50,
    }


def test_graph_references_share_canonical_jobs_without_unsafe_deduplication() -> None:
    graph = build_training_graph(load_g5_contract(ROOT))
    refs = graph.references
    primary = [ref for ref in refs if ref.condition_id == "sr_mappo_mobile"]
    assert len(primary) >= 150
    assert len({ref.canonical_training_identity for ref in primary}) == 30
    assert all(ref.canonical_training_identity == ref.job.canonical_training_identity for ref in refs)
    assert all(ref.experiment_identity.endswith(ref.canonical_training_identity) for ref in refs)

    with pytest.raises(ValueError):
        graph.assert_safe_deduplication(
            graph.unique_jobs[0],
            graph.unique_jobs[0].__class__(
                **{**graph.unique_jobs[0].__dict__, "config_hash": "different"}
            ),
        )
    tampered = graph.unique_jobs[0].__class__(
        **{**graph.unique_jobs[0].__dict__, "canonical_training_identity": "0" * 64}
    )
    with pytest.raises(ValueError, match="tampered"):
        graph.assert_safe_deduplication(graph.unique_jobs[0], tampered)


def test_ablation_remove_one_groups_and_sensitivity_axes_are_strict() -> None:
    full = {
        "observation_normalization": True,
        "return_normalization": True,
        "orthogonal_initialization": True,
        "layer_normalization": True,
        "value_clipping": True,
        "huber_value_loss": True,
        "learning_rate_decay": True,
    }
    variant = dict(full)
    variant.update(orthogonal_initialization=False, layer_normalization=False)
    assert validate_ablation_diff(full, variant) == "no_network_stabilization"
    invalid = dict(variant, return_normalization=False)
    with pytest.raises(ValueError):
        validate_ablation_diff(full, invalid)

    center = {"learning_rate": 3e-4, "clip_range": 0.20, "entropy_coef": 0.010, "gamma": 0.99, "gae_lambda": 0.95}
    assert validate_sensitivity_diff(center, dict(center, learning_rate=1e-4)) == ("learning_rate", 1e-4)
    with pytest.raises(ValueError):
        validate_sensitivity_diff(center, dict(center, learning_rate=1e-4, gamma=0.95))
    with pytest.raises(ValueError):
        validate_sensitivity_diff(center, dict(center))


def test_manifest_generator_is_byte_deterministic_and_has_no_sealed_payload(tmp_path: Path) -> None:
    import scripts.generate_g5_manifests as generator

    first = tmp_path / "one"
    second = tmp_path / "two"
    generator.generate_manifests(ROOT, first)
    generator.generate_manifests(ROOT, second)
    files_a = sorted(path.relative_to(first) for path in first.rglob("*") if path.is_file())
    files_b = sorted(path.relative_to(second) for path in second.rglob("*") if path.is_file())
    assert files_a == files_b
    for relative in files_a:
        assert (first / relative).read_bytes() == (second / relative).read_bytes()
        payload = (first / relative).read_text(encoding="utf-8")
        assert "30000" not in payload and "30099" not in payload
        assert "sealed_scenario" not in payload
    training = json.loads((first / "g6-training-jobs.json").read_text(encoding="utf-8"))
    assert training["job_count"] == 375
    assert training["decomposition"]["total"] == 375
    jobs = training["jobs"]
    for reference in training["references"]:
        job = jobs[reference["job_index"]]
        assert job["canonical_training_identity"] == reference["canonical_training_identity"]


def test_identity_rejects_malformed_whitespace() -> None:
    with pytest.raises(ValueError):
        canonical_training_serialization(" sr_mappo_mobile", "g20x20_d2", 42, "cfg", "commit")


def test_task7_registry_drift_fails_closed(tmp_path: Path) -> None:
    candidate = tmp_path / "repo"
    shutil.copytree(ROOT / "configs", candidate / "configs")
    (candidate / "docs/evidence").mkdir(parents=True)
    shutil.copytree(ROOT / "docs/evidence/g1", candidate / "docs/evidence/g1")
    shutil.copytree(ROOT / "docs/evidence/g5", candidate / "docs/evidence/g5")
    for name in ("requirements-g2.lock", "requirements-g3.lock", "requirements-g5.lock"):
        shutil.copy2(ROOT / name, candidate / name)
    path = candidate / "configs/problem2/g5/families.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("g20x20_d2", "g20x20_drift"), encoding="utf-8")
    with pytest.raises(Exception, match="Task 7 family"):
        load_g5_contract(candidate)


def test_graph_provenance_is_current_and_registry_bound() -> None:
    graph = build_training_graph(load_g5_contract(ROOT))
    current = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    assert graph.source_commit == current
    assert set(graph.registry_hashes) == {
        "configs/problem2/g5/families.yaml",
        "configs/problem2/g5/ablations.yaml",
        "configs/problem2/g5/sensitivity.yaml",
    }
    assert len({job.config_hash for job in graph.unique_jobs}) == 25
