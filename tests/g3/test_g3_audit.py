from __future__ import annotations

import json
from pathlib import Path

import pytest

from problem2.config import load_g3_config
from problem2.training.train_g3_smoke import run_training_smoke
from scripts.audit_g3_marl import G3AuditError, audit_g3


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "problem2" / "g3_heterogeneous_marl.yaml"


def test_g3_audit_requires_all_acceptance_tests_and_provenance(tmp_path: Path) -> None:
    result = run_training_smoke(CONFIG_PATH, tmp_path, seed=9020, updates=2)
    report_path = tmp_path / "g3-audit.json"

    report = audit_g3(CONFIG_PATH, tmp_path, report_path)

    assert report["status"] == "pass"
    assert report["gate"] == "G3"
    assert report["maturity"] == "M2"
    assert report["algorithm_name"] == "SR-MAPPO"
    assert report["config_hash"] == result["config_hash"]
    assert report["acceptance"]["passed"] == report["acceptance"]["required"]
    assert len(report["acceptance"]["tests"]) == 12
    assert report["training_smoke"]["sealed_test_accessed"] is False
    assert report["training_smoke"]["finite_loss_checks"] is True
    assert report_path.exists()


def test_g3_audit_fails_closed_on_sealed_access(tmp_path: Path) -> None:
    run_training_smoke(CONFIG_PATH, tmp_path, seed=9021, updates=1)
    provenance_path = tmp_path / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["sealed_test_accessed"] = True
    provenance_path.write_text(
        json.dumps(provenance, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(G3AuditError, match="sealed"):
        audit_g3(CONFIG_PATH, tmp_path, tmp_path / "g3-audit.json")


def test_g3_audit_rejects_config_hash_drift(tmp_path: Path) -> None:
    run_training_smoke(CONFIG_PATH, tmp_path, seed=9022, updates=1)
    provenance_path = tmp_path / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["config_hash"] = "f" * 64
    provenance_path.write_text(
        json.dumps(provenance, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(G3AuditError, match="config hash"):
        audit_g3(CONFIG_PATH, tmp_path, tmp_path / "g3-audit.json")
