"""Freeze validation evidence and issue a consumable sealed-test unlock."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from problem2.config import config_identity, load_config_bundle
from problem2.experiments.freeze import create_sealed_unlock, create_validation_freeze
from problem2.experiments.orchestrator import Chapter45Orchestrator
from problem2.experiments.readiness import audit_repository_readiness
from problem2.experiments.recovery import load_job_record
from problem2.experiments.specification import load_experiment_spec, protocol_identity


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))


def _formal_config_ready(config: object, spec: object, readiness: object | None = None) -> None:
    sections = (
        config.parameters,
        config.scales,
        config.environment,
        config.algorithm,
        config.experiments,
    )
    if (
        spec.status != "verified"
        or config.scenario_status != "verified"
        or any(section.get("status") != "verified" for section in sections)
    ):
        raise ValueError("validation freeze requires verified configuration and protocol")
    if readiness is not None and not bool(getattr(readiness, "formal_ready", False)):
        raise ValueError("validation freeze requires a passing readiness gate")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    freeze = subparsers.add_parser("freeze")
    freeze.add_argument("--config-dir", type=Path, required=True)
    freeze.add_argument("--protocol", type=Path)
    freeze.add_argument("--job-file", type=Path, nargs="+", required=True)
    freeze.add_argument("--validation", type=Path, nargs="+", required=True)
    freeze.add_argument("--output", type=Path, required=True)
    freeze.add_argument("--readiness-report", type=Path)

    unlock = subparsers.add_parser("unlock")
    unlock.add_argument("--freeze", type=Path, required=True)
    unlock.add_argument("--output", type=Path, required=True)
    unlock.add_argument("--scenario", action="append", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "unlock":
            manifest = create_sealed_unlock(
                args.output,
                freeze_path=args.freeze,
                sealed_scenarios=args.scenario,
            )
            _emit({
                "status": "completed",
                "command": "unlock",
                "output": str(args.output.resolve()),
                "unlock_id": manifest["unlock_id"],
            })
            return 0

        config = load_config_bundle(args.config_dir)
        protocol_path = args.protocol or (args.config_dir / "experiments" / "chapter4_5.yaml")
        spec = load_experiment_spec(protocol_path, config)
        if args.readiness_report is not None:
            readiness_payload = json.loads(args.readiness_report.read_text(encoding="utf-8"))
            if not bool(readiness_payload.get("formal_ready")):
                raise ValueError("validation freeze requires a passing readiness report")
            readiness = type("Readiness", (), {"formal_ready": True})()
        else:
            readiness = audit_repository_readiness(args.config_dir)
        _formal_config_ready(config, spec, readiness)
        jobs = [load_job_record(path) for path in args.job_file]
        orchestrator = Chapter45Orchestrator(
            args.config_dir,
            args.output.parent / "freeze-planning",
            protocol_path=protocol_path,
        )
        expected_job_ids = tuple(
            planned.identity.job_id
            for family in spec.families
            for planned in orchestrator.plan(family, execution_profile="formal")
        )
        scenarios_by_scale = {
            str(scale): tuple(
                str(scenario_id)
                for scenario_id in config.experiments["validation_scenarios"]
                if str(config.scenarios[str(scenario_id)]["scale"]) == str(scale)
            )
            for scale in spec.scales
        }
        manifest = create_validation_freeze(
            args.output,
            config_hash=config_identity(config),
            protocol_hash=protocol_identity(protocol_path),
            statistics=spec.statistics,
            jobs=jobs,
            expected_job_ids=expected_job_ids,
            validation_paths=args.validation,
            validation_scenarios_by_scale=scenarios_by_scale,
        )
        _emit({
            "status": "completed",
            "command": "freeze",
            "output": str(args.output.resolve()),
            "freeze_hash": manifest["freeze_hash"],
        })
        return 0
    except Exception as exc:  # noqa: BLE001 - preserve machine-readable CLI diagnostics
        _emit({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
