from __future__ import annotations

import json
from pathlib import Path
from subprocess import CompletedProcess

import pytest
import torch

import scripts.audit_g3_marl as g3_audit_module
from problem2.config import load_g3_config
from problem2.training.train_g3_smoke import run_training_smoke
from scripts.audit_g3_marl import G3AuditError, audit_g3


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "problem2" / "g3_heterogeneous_marl.yaml"


def test_g3_audit_requires_all_acceptance_tests_and_provenance(tmp_path: Path) -> None:
    result = run_training_smoke(
        CONFIG_PATH,
        tmp_path,
        seed=9020,
        updates=2,
        allow_noncanonical_output_root=True,
    )
    report_path = tmp_path / "g3-audit.json"

    report = audit_g3(
        CONFIG_PATH,
        tmp_path,
        report_path,
        allow_noncanonical_output_root=True,
    )

    assert report["status"] == "pass"
    assert report["gate"] == "G3"
    assert report["maturity"] == "M2"
    assert report["algorithm_name"] == "SR-MAPPO"
    assert report["config_hash"] == result["config_hash"]
    assert report["acceptance"]["passed"] == report["acceptance"]["required"]
    assert len(report["acceptance"]["tests"]) == len(g3_audit_module.ACCEPTANCE_TESTS)
    assert report["training_smoke"]["sealed_test_accessed"] is False
    assert report["training_smoke"]["finite_loss_checks"] is True
    assert report_path.exists()


def test_g3_audit_fails_closed_on_sealed_access(tmp_path: Path) -> None:
    run_training_smoke(
        CONFIG_PATH,
        tmp_path,
        seed=9021,
        updates=1,
        allow_noncanonical_output_root=True,
    )
    provenance_path = tmp_path / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["sealed_test_accessed"] = True
    provenance_path.write_text(
        json.dumps(provenance, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(G3AuditError, match="sealed"):
        audit_g3(
            CONFIG_PATH,
            tmp_path,
            tmp_path / "g3-audit.json",
            allow_noncanonical_output_root=True,
        )


def test_g3_audit_rejects_config_hash_drift(tmp_path: Path) -> None:
    run_training_smoke(
        CONFIG_PATH,
        tmp_path,
        seed=9022,
        updates=1,
        allow_noncanonical_output_root=True,
    )
    provenance_path = tmp_path / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["config_hash"] = "f" * 64
    provenance_path.write_text(
        json.dumps(provenance, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(G3AuditError, match="config hash"):
        audit_g3(
            CONFIG_PATH,
            tmp_path,
            tmp_path / "g3-audit.json",
            allow_noncanonical_output_root=True,
        )


def test_g3_audit_rejects_checkpoint_provenance_drift(tmp_path: Path) -> None:
    result = run_training_smoke(
        CONFIG_PATH,
        tmp_path,
        seed=9023,
        updates=1,
        allow_noncanonical_output_root=True,
    )
    checkpoint_path = Path(result["checkpoint"])
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    payload["provenance"]["validation_scenarios_accessed"] = True
    torch.save(payload, checkpoint_path)

    with pytest.raises(G3AuditError, match="checkpoint.*validation"):
        audit_g3(
            CONFIG_PATH,
            tmp_path,
            tmp_path / "g3-audit.json",
            allow_noncanonical_output_root=True,
        )


def test_g3_audit_rejects_unbound_source_commit_and_nonpesticide_resource(
    tmp_path: Path,
) -> None:
    result = run_training_smoke(
        CONFIG_PATH,
        tmp_path,
        seed=9024,
        updates=1,
        allow_noncanonical_output_root=True,
    )
    provenance_path = Path(result["provenance"])
    checkpoint_path = Path(result["checkpoint"])
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["source_tree_commit"] = "unknown"
    provenance["replenished_resource"] = "battery"
    provenance_path.write_text(
        json.dumps(provenance, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    payload["provenance"]["source_tree_commit"] = "unknown"
    payload["provenance"]["replenished_resource"] = "battery"
    torch.save(payload, checkpoint_path)

    with pytest.raises(G3AuditError, match="source tree commit|pesticide"):
        audit_g3(
            CONFIG_PATH,
            tmp_path,
            tmp_path / "g3-audit.json",
            allow_noncanonical_output_root=True,
        )


def test_g3_acceptance_audit_rejects_skipped_nodes(monkeypatch: pytest.MonkeyPatch) -> None:
    completed = CompletedProcess(
        args=["pytest"],
        returncode=0,
        stdout="11 passed, 1 skipped in 0.1s\n",
        stderr="",
    )
    monkeypatch.setattr(
        g3_audit_module.subprocess,
        "run",
        lambda *args, **kwargs: completed,
    )

    with pytest.raises(G3AuditError, match="expected"):
        g3_audit_module._run_acceptance_tests(ROOT)


def test_g3_audit_rejects_raw_log_identity_drift(tmp_path: Path) -> None:
    result = run_training_smoke(
        CONFIG_PATH,
        tmp_path,
        seed=9025,
        updates=1,
        allow_noncanonical_output_root=True,
    )
    raw_log_path = Path(result["raw_log"])
    record = json.loads(raw_log_path.read_text(encoding="utf-8").splitlines()[0])
    record["seed"] = 20000
    raw_log_path.write_text(
        json.dumps(record, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(G3AuditError, match="raw log.*seed"):
        audit_g3(
            CONFIG_PATH,
            tmp_path,
            tmp_path / "g3-audit.json",
            allow_noncanonical_output_root=True,
        )


def test_g3_audit_rejects_noncanonical_output_root(tmp_path: Path) -> None:
    run_training_smoke(
        CONFIG_PATH,
        tmp_path,
        seed=9026,
        updates=1,
        allow_noncanonical_output_root=True,
    )

    with pytest.raises(G3AuditError, match="canonical"):
        audit_g3(CONFIG_PATH, tmp_path, tmp_path / "g3-audit.json")


def test_g3_audit_rejects_scenario_seed_manifest_drift(tmp_path: Path) -> None:
    result = run_training_smoke(
        CONFIG_PATH,
        tmp_path,
        seed=9027,
        updates=1,
        allow_noncanonical_output_root=True,
    )
    provenance_path = Path(result["provenance"])
    checkpoint_path = Path(result["checkpoint"])
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["scenario_seed_manifest_sha256"] = "0" * 64
    provenance_path.write_text(
        json.dumps(provenance, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    payload["provenance"]["scenario_seed_manifest_sha256"] = "0" * 64
    torch.save(payload, checkpoint_path)

    with pytest.raises(G3AuditError, match="scenario seed manifest"):
        audit_g3(
            CONFIG_PATH,
            tmp_path,
            tmp_path / "g3-audit.json",
            allow_noncanonical_output_root=True,
        )


def test_g3_audit_rejects_implementation_tree_hash_drift(tmp_path: Path) -> None:
    result = run_training_smoke(
        CONFIG_PATH,
        tmp_path,
        seed=9028,
        updates=1,
        allow_noncanonical_output_root=True,
    )
    provenance_path = Path(result["provenance"])
    checkpoint_path = Path(result["checkpoint"])
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["source_tree_hash"] = "0" * 64
    provenance_path.write_text(
        json.dumps(provenance, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    payload["provenance"]["source_tree_hash"] = "0" * 64
    torch.save(payload, checkpoint_path)

    with pytest.raises(G3AuditError, match="source tree hash"):
        audit_g3(
            CONFIG_PATH,
            tmp_path,
            tmp_path / "g3-audit.json",
            allow_noncanonical_output_root=True,
        )
