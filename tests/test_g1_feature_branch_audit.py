from __future__ import annotations

from scripts.audit_g1_feature_branch import audit_candidate_branch, classify_path


def test_candidate_path_classes_are_stable() -> None:
    assert classify_path("src/problem2/environment/air_ground_env.py") == "source"
    assert classify_path("configs/formal_matrix.yaml") == "configuration"
    assert classify_path("tests/marl/test_masks_and_gae.py") == "test"
    assert classify_path("docs/verification/formal-readiness-final.json") == "report"
    assert classify_path("artifacts/figures/chapter4/fig4-1_air_ground_system.png") == "artifact"
    assert classify_path("README.md") == "documentation"


def test_audit_does_not_report_a_maturity_gate_as_currently_passed() -> None:
    report = audit_candidate_branch(
        "origin/main", "origin/feature/problem2-code-framework"
    )
    assert report["current_branch_maturity"] == "M1"
    assert report["current_gate"] == "G1"
    assert report["read_only"] is True
    assert report["base_commit"] == "2643753855c385253951dfad2c225be0b09b7e00"
    assert report["candidate_commit"] == "52a92c00467fbc3fa6a81e0fcb43469b2f8d1940"
