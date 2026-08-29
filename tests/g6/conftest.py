from __future__ import annotations

from typing import Any

import pytest

from problem2.training.selection import build_formal_freeze_payloads


SOURCE_COMMIT = "c" * 40
SOURCE_SCOPE_SHA256 = "d" * 64
DYNAMIC_OUTPUT_ROOT = "outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g6"


@pytest.fixture(scope="session")
def formal_freeze_payloads() -> dict[str, dict[str, Any]]:
    jobs = [
        {
            "canonical_training_identity": f"{index + 1:064x}",
            "family": "algorithm_scale" if index < 150 else "problem2_required",
            "method": "sr_mappo_mobile",
            "condition_id": "sr_mappo_mobile",
            "scale": "g20x20_d2",
            "training_seed": 42,
            "config_hash": "a" * 64,
            "git_commit": SOURCE_COMMIT,
            "source_scope_sha256": SOURCE_SCOPE_SHA256,
            "ecology_id": "dynamic_pest_v1",
            "output_root": DYNAMIC_OUTPUT_ROOT,
        }
        for index in range(375)
    ]
    return build_formal_freeze_payloads(
        jobs,
        validation_scenario_ids=range(20000, 20050),
        validation_panel_hash="b" * 64,
        sealed_scenario_ids=range(30000, 30100),
        sealed_panel_hash="e" * 64,
        source_commit=SOURCE_COMMIT,
        protocol_hash="f" * 64,
    )
