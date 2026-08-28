from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from problem2.ecology.config import (
    DYNAMIC_ECOLOGY_VERSION,
    DynamicEcologyConfig,
    DynamicEcologyConfigError,
    verify_problem1_lineage,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "problem2" / "dynamic_pest_v1.yaml"
LINEAGE_PATH = ROOT / "docs" / "evidence" / "dynamic_pest_v1" / "source_lineage.yaml"


def _write_yaml(tmp_path: Path, name: str, payload: object) -> Path:
    path = tmp_path / name
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _config_payload() -> dict[str, object]:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def _lineage_payload() -> dict[str, object]:
    return yaml.safe_load(LINEAGE_PATH.read_text(encoding="utf-8"))


def test_dynamic_contract_loads_exact_approved_values() -> None:
    cfg = DynamicEcologyConfig.from_yaml(CONFIG_PATH)

    assert DYNAMIC_ECOLOGY_VERSION == "problem2-dynamic-pest-v1"
    assert cfg.version == "problem2-dynamic-pest-v1"
    assert (cfg.beta, cfg.m, cfg.s, cfg.d1, cfg.d2) == (1.5, 2.0, 0.25, 0.3, 0.3)
    assert (cfg.integration_interval, cfg.substeps) == (0.005, 3)
    assert (cfg.effect_amount, cfg.effect_duration, cfg.decay_rate, cfg.spray_radius) == (
        0.85,
        15,
        0.92,
        4,
    )
    assert cfg.predator_sensitivity == 0.1
    assert cfg.wind_strength_range == (0.0, 0.5)
    assert len(cfg.contract_sha256) == 64
    assert cfg.canonical_payload() == {
        "schema_version": "problem2.dynamic-ecology.v1",
        "version": DYNAMIC_ECOLOGY_VERSION,
        "assumption_status": "provisional_normalized_simulation",
        "dynamic_wind": True,
        "replenished_resource": "pesticide",
        "battery_replenishment_enabled": False,
        "beta": 1.5,
        "m": 2.0,
        "s": 0.25,
        "d1": 0.3,
        "d2": 0.3,
        "integration_interval": 0.005,
        "substeps": 3,
        "reaction_clip_bounds": [-0.5, 0.5],
        "prey_extinction_threshold": 1.0e-6,
        "predator_low_prey_decay": 0.1,
        "prey_advection_multiplier": 0.05,
        "predator_advection_multiplier": 0.01,
        "wind_strength_range": [0.0, 0.5],
        "wind_direction_noise_std": 0.1,
        "wind_strength_noise_std": 0.05,
        "wind_slow_direction_amplitude": 0.005,
        "wind_slow_direction_period": 50,
        "effect_amount": 0.85,
        "effect_duration": 15,
        "decay_rate": 0.92,
        "spray_radius": 4,
        "concentration_cap": 1.0,
        "prey_mortality_scale": 2.0,
        "prey_mortality_cap": 0.98,
        "predator_sensitivity": 0.1,
        "predator_mortality_cap": 0.3,
    }


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda payload: payload.pop("beta"), "missing keys"),
        (lambda payload: payload.__setitem__("unknown", "value"), "unknown keys"),
        (lambda payload: payload.__setitem__("beta", True), "finite number"),
        (lambda payload: payload.__setitem__("m", float("nan")), "finite"),
        (lambda payload: payload.__setitem__("substeps", 0), "positive"),
        (
            lambda payload: payload.__setitem__("wind_strength_range", [0.5, 0.0]),
            "bounds",
        ),
        (
            lambda payload: payload.__setitem__("replenished_resource", "battery"),
            "pesticide",
        ),
        (
            lambda payload: payload.__setitem__("battery_replenishment_enabled", True),
            "battery replenishment",
        ),
        (
            lambda payload: payload.__setitem__("version", "problem2-dynamic-pest-v2"),
            "version",
        ),
    ],
)
def test_dynamic_contract_rejects_drift(
    tmp_path: Path, mutate, message: str
) -> None:
    payload = _config_payload()
    mutate(payload)

    with pytest.raises(DynamicEcologyConfigError, match=message):
        DynamicEcologyConfig.from_yaml(_write_yaml(tmp_path, "dynamic.yaml", payload))


def test_lineage_resolves_only_the_approved_commit_and_blobs() -> None:
    resolved = verify_problem1_lineage(LINEAGE_PATH)

    assert resolved["source_commit"] == "1ca9e5ccc5f77ed775cd2b607dd70d635720accf"
    assert resolved["runtime_import_allowed"] == "false"


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda payload: payload.__setitem__("source_commit", "0" * 40),
            "source commit",
        ),
        (
            lambda payload: payload.__setitem__(
                "repository_path", "C:/unapproved-repository"
            ),
            "repository_path",
        ),
        (
            lambda payload: payload["sources"][0].__setitem__("blob_id", "0" * 40),
            "blob",
        ),
        (
            lambda payload: payload.__setitem__("runtime_import_allowed", True),
            "runtime import",
        ),
        (
            lambda payload: payload.__setitem__("checkpoint_import_allowed", True),
            "checkpoint import",
        ),
        (
            lambda payload: payload.__setitem__("output_or_result_import_allowed", True),
            "output import",
        ),
    ],
)
def test_lineage_rejects_identity_or_import_drift(
    tmp_path: Path, mutate, message: str
) -> None:
    payload = _lineage_payload()
    mutate(payload)

    with pytest.raises(DynamicEcologyConfigError, match=message):
        verify_problem1_lineage(
            _write_yaml(tmp_path, "lineage.yaml", payload), resolve_git=False
        )
