"""Audit the dynamic Problem-2 ecology contract with a bounded development probe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from problem2.algorithms.protocol import ActionResult
from problem2.ecology.config import DynamicEcologyConfig
from problem2.ecology.dynamics import advance_holling_tanner
from problem2.ecology.scenario import generate_dynamic_scenario
from problem2.experiments.artifacts import atomic_write_bytes
from problem2.experiments.ecology_policy import EcologyMode, resolve_output_root
from problem2.training.tuning import build_development_environment


CHECK_NAMES = (
    "numerics",
    "scenario_replay",
    "accepted_spray",
    "conservation",
    "fixed_dimensions",
    "signed_reward",
    "static_primary_rejected",
)


def _check(name: str, function: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        details = function()
    except Exception as exc:
        return {
            "name": name,
            "status": "fail",
            "reason": f"{type(exc).__name__}: {exc}",
        }
    return {"name": name, "status": "pass", **details}


def _numerics(config: DynamicEcologyConfig) -> dict[str, Any]:
    prey = np.asarray([[0.08, 0.12], [0.10, 0.06]], dtype=np.float64)
    predator = np.asarray([[0.01, 0.02], [0.015, 0.005]], dtype=np.float64)
    next_prey, next_predator = advance_holling_tanner(
        prey, predator, (0.2, -0.1), config
    )
    if next_prey.shape != prey.shape or next_predator.shape != predator.shape:
        raise AssertionError("dynamic numerics changed field shape")
    if not np.isfinite(next_prey).all() or not np.isfinite(next_predator).all():
        raise AssertionError("dynamic numerics produced non-finite density")
    if np.any(next_prey < 0.0) or np.any(next_predator < 0.0):
        raise AssertionError("dynamic numerics produced negative density")
    if np.any(next_prey > 1.0 / config.beta) or np.any(next_predator > 2.0 / config.beta):
        raise AssertionError("dynamic numerics exceeded ecological bounds")
    return {
        "field_shape": list(prey.shape),
        "substeps": config.substeps,
        "finite": True,
    }


def _scenario_replay(config: DynamicEcologyConfig) -> dict[str, Any]:
    left = generate_dynamic_scenario(
        "development", 10000, "g20x20_d2", (20, 20), config
    )
    right = generate_dynamic_scenario(
        "development", 10000, "g20x20_d2", (20, 20), config
    )
    if left.scenario_sha256 != right.scenario_sha256:
        raise AssertionError("identical dynamic scenario identities did not replay")
    if left.initial_prey.tobytes() != right.initial_prey.tobytes():
        raise AssertionError("prey scenario bytes did not replay")
    if left.initial_predator.tobytes() != right.initial_predator.tobytes():
        raise AssertionError("predator scenario bytes did not replay")
    return {
        "scenario_id": 10000,
        "scenario_sha256": left.scenario_sha256,
        "ecology_source_commit": left.source_commit,
    }


def _action(view: dict[str, Any], uav_actions: list[int]) -> ActionResult:
    return ActionResult(
        actions={
            "uav": np.asarray(uav_actions, dtype=np.int64),
            "vehicle": np.asarray([0], dtype=np.int64),
        },
        masks=view["masks"],
    )


def _accepted_spray(root: Path) -> dict[str, Any]:
    environment = build_development_environment(
        root, scenario_id=10000, scale="g20x20_d2"
    )
    view = environment.reset(scenario_id=10000)
    next_view = environment.step(_action(view, [5, 0]))
    if environment.spray_action_count != 1:
        raise AssertionError("positive physical spray was not accepted")
    if int(environment.ecology.spray_count.sum()) != 1:
        raise AssertionError("accepted spray was not deposited exactly once")
    if not np.any(environment.ecology.concentration > 0.0):
        raise AssertionError("accepted spray did not create pesticide effect")
    if next_view["dynamic_step_count"] != 1:
        raise AssertionError("ecology step did not advance exactly once")
    return {
        "spray_action_count": environment.spray_action_count,
        "dynamic_step_count": next_view["dynamic_step_count"],
    }


def _conservation(root: Path) -> dict[str, Any]:
    environment = build_development_environment(
        root, scenario_id=10000, scale="g20x20_d2"
    )
    view = environment.reset(scenario_id=10000)
    environment.step(_action(view, [5, 0]))
    ledger = environment.state.ledger
    remaining = sum(uav.pesticide_l for uav in environment.state.uavs)
    remaining += environment.state.vehicle.inventory_l
    residual = remaining - (ledger.initial_total_l - ledger.cumulative_sprayed_l)
    if abs(residual) > environment.physical.config.tolerance:
        raise AssertionError(f"resource conservation residual is {residual}")
    return {"resource_conservation_residual_l": float(residual)}


def _fixed_dimensions(root: Path) -> dict[str, Any]:
    environment = build_development_environment(
        root, scenario_id=10000, scale="g20x20_d2"
    )
    view = environment.reset(scenario_id=10000)
    observed = {
        "uav": list(view["observations"]["uav"].shape),
        "vehicle": list(view["observations"]["vehicle"].shape),
        "critic": list(view["critic_state"].shape),
    }
    expected = {"uav": [2, 179], "vehicle": [1, 28], "critic": [185]}
    if observed != expected:
        raise AssertionError(f"fixed observation dimensions drifted: {observed}")
    return {"observation_shapes": observed}


def _signed_reward(root: Path) -> dict[str, Any]:
    environment = build_development_environment(
        root, scenario_id=10000, scale="g20x20_d2"
    )
    view = environment.reset(scenario_id=10000)
    environment.ecology._prey[...] = 0.1
    environment.ecology._predator[...] = 0.001
    next_view = environment.step(_action(view, [0, 0]))
    reward = float(next_view["team_reward"])
    if not np.isfinite(reward) or reward >= 0.0:
        raise AssertionError("dynamic no-spray growth did not produce a negative reward")
    return {"team_reward": reward, "endpoint_reduction_rate": 1.0 - float(next_view["final_total_pest"]) / float(next_view["initial_total_pest"])}


def _static_primary_rejected(root: Path) -> dict[str, Any]:
    try:
        resolve_output_root(
            root,
            "G5",
            None,
            primary=True,
            partition="development",
            ecology_mode=EcologyMode.STATIC_DIAGNOSTIC,
        )
    except ValueError as exc:
        if "dynamic ecology" not in str(exc):
            raise AssertionError(f"wrong static-primary rejection: {exc}") from exc
        return {"rejection": "dynamic ecology required"}
    raise AssertionError("static ecology was accepted for a primary run")


def audit_dynamic_pest(root: Path, output: Path) -> dict[str, Any]:
    root = root.resolve()
    try:
        source_commit = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("current source commit could not be resolved") from exc
    config = DynamicEcologyConfig.from_yaml(
        root / "configs" / "problem2" / "dynamic_pest_v1.yaml"
    )
    checks = [
        _check("numerics", lambda: _numerics(config)),
        _check("scenario_replay", lambda: _scenario_replay(config)),
        _check("accepted_spray", lambda: _accepted_spray(root)),
        _check("conservation", lambda: _conservation(root)),
        _check("fixed_dimensions", lambda: _fixed_dimensions(root)),
        _check("signed_reward", lambda: _signed_reward(root)),
        _check("static_primary_rejected", lambda: _static_primary_rejected(root)),
    ]
    failed = [check for check in checks if check["status"] != "pass"]
    payload = {
        "schema_version": "problem2.dynamic-pest-audit.v1",
        "status": "fail" if failed else "pass",
        "maturity": "M2",
        "ecology_mode": EcologyMode.DYNAMIC.value,
        "ecology_version": config.version,
        "ecology_config_sha256": config.contract_sha256,
        "source_commit": source_commit,
        "replenished_resource": "pesticide",
        "battery_replenishment_enabled": False,
        "validation_accessed": False,
        "sealed_accessed": False,
        "checks": checks,
        "check_names": list(CHECK_NAMES),
    }
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(
        output,
        (json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8"),
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = audit_dynamic_pest(args.root, args.output)
    except Exception as exc:
        payload = {
            "schema_version": "problem2.dynamic-pest-audit.v1",
            "status": "fail",
            "maturity": "M2",
            "ecology_mode": EcologyMode.DYNAMIC.value,
            "battery_replenishment_enabled": False,
            "validation_accessed": False,
            "sealed_accessed": False,
            "source_commit": None,
            "reason": f"{type(exc).__name__}: {exc}",
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_bytes(
            args.output.resolve(),
            (json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8"),
        )
    print(json.dumps({"status": payload["status"], "output": str(args.output.resolve())}, sort_keys=True))
    return 0 if payload["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
