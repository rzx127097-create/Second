"""Shared dry-run CLI guard; Task 8 never executes experiment rows."""
from __future__ import annotations

import argparse
import json
import hashlib
import importlib
import shutil
import subprocess
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for import_root in (ROOT, SRC):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from problem2.evaluation.sealed_lock import SealedAccessError, assert_no_sealed_access, assert_partition_allowed
from problem2.experiments.ecology_policy import EcologyMode, resolve_output_root


_TASK7_REGISTRY_PATHS = frozenset({
    "configs/problem2/g5/families.yaml",
    "configs/problem2/g5/ablations.yaml",
    "configs/problem2/g5/sensitivity.yaml",
})


def _registry_hashes_match(contract_hashes: object, expected_registry: object) -> bool:
    if not isinstance(contract_hashes, dict) or not isinstance(expected_registry, dict):
        return False
    if set(expected_registry) != _TASK7_REGISTRY_PATHS:
        return False
    return all(contract_hashes.get(path) == expected_registry[path] for path in _TASK7_REGISTRY_PATHS)


def read_only_preflight(root: Path = ROOT, *, gate: str = "G6") -> dict[str, object]:
    """Audit frozen inputs without queueing jobs, writing artifacts, or reading sealed rows."""
    root = Path(root).resolve()
    checks: dict[str, bool] = {}
    details: dict[str, str] = {}
    try:
        from problem2.experiments.g5_contract import load_g5_contract
        contract = load_g5_contract(root)
        checks["frozen_contract"] = bool(contract.file_hashes)
        summary_path = root / "outputs/problem2_sr_mappo_v1/g5/manifests/manifest-summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        expected_registry = summary.get("provenance", {}).get("registry_hashes", {})
        checks["registry_hashes"] = _registry_hashes_match(dict(contract.file_hashes), expected_registry)
        details["frozen_contract"] = "loaded strict G5 contract"
    except Exception:
        checks["frozen_contract"] = False
        checks["registry_hashes"] = False
    try:
        status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root, capture_output=True, text=True, check=True).stdout.splitlines()
        checks["frozen_source_clean"] = not status
        details["frozen_source_clean"] = "clean" if not status else f"dirty paths: {len(status)}"
    except (OSError, subprocess.CalledProcessError):
        checks["frozen_source_clean"] = False
        details["frozen_source_clean"] = "git status unavailable"
    try:
        local = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
        remote = subprocess.run(["git", "rev-parse", "@{upstream}"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
        branch = subprocess.run(["git", "branch", "--show-current"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
        ls_remote = subprocess.run(["git", "ls-remote", "origin", f"refs/heads/{branch}"], cwd=root, capture_output=True, text=True, check=True).stdout.strip().split()[0]
        checks["frozen_source_remote"] = bool(local and local == remote == ls_remote)
        details["frozen_source_remote"] = f"local={local[:12]} upstream={remote[:12]} origin={ls_remote[:12]}"
    except (OSError, subprocess.CalledProcessError):
        checks["frozen_source_remote"] = False
    reconciliation = root / "docs/audits/g4-lineage-reconciliation.md"
    g4_audit = root / "outputs/problem2_sr_mappo_v1/g4/g4-mechanism-audit.json"
    try:
        g4_payload = json.loads(g4_audit.read_text(encoding="utf-8"))
        checks["g4_reconciliation"] = reconciliation.exists() and "passes the fail-closed lineage audit" in reconciliation.read_text(encoding="utf-8").lower() and g4_payload.get("audit") == "g4-mechanism-compliance" and g4_payload.get("hard_boundary", {}).get("sealed_test_accessed") is False
    except (OSError, UnicodeError, json.JSONDecodeError):
        checks["g4_reconciliation"] = False
    road_candidates = list((root / "outputs/problem2_sr_mappo_v1/g2/roads").glob("*/metadata.json")) if (root / "outputs/problem2_sr_mappo_v1/g2/roads").exists() else []
    checks["road_cache_provenance"] = False
    for candidate in road_candidates:
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
            required = {"schema_version", "source", "projection", "grid", "topology", "preprocess_version"}
            source = payload.get("source", {})
            checks["road_cache_provenance"] = required <= set(payload) and isinstance(source.get("sha256"), str) and len(source["sha256"]) == 64 and source.get("crs") == "EPSG:4326" and payload.get("projection", {}).get("target_crs") == "EPSG:32643" and bool(source.get("bbox_lonlat")) and len(payload.get("grid", {}).get("shape", [])) == 2 and bool(payload.get("topology")) and payload.get("preprocess_version") == "g2-road-v1"
            if checks["road_cache_provenance"]:
                break
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
    output_root = root / "outputs/problem2_sr_mappo_v1/g5"
    configured_output_parent = ROOT / "outputs/problem2_sr_mappo_v1"
    try:
        output_root.resolve().relative_to(configured_output_parent.resolve())
        checks["output_confinement"] = root == ROOT and output_root.resolve().name == "g5"
    except ValueError:
        checks["output_confinement"] = False
    try:
        checks["disk_space"] = shutil.disk_usage(root).free >= 1024 * 1024 * 1024
    except OSError:
        checks["disk_space"] = False
    checks["runtime_inventory"] = bool(sys.version_info >= (3, 11) and sys.executable and platform.system() and platform.machine())
    g6_manifest = output_root / "manifests/g6-training-jobs.json"
    g7_manifest = output_root / "manifests/g7-sealed-evaluations.json"
    try:
        payloads = {
            path.name: json.loads(path.read_text(encoding="utf-8"))
            for path in list((output_root / "manifests").glob("g6-*.json"))
            + list((output_root / "manifests").glob("g7-*.json"))
        }
        def is_sealed_scenario_id(value):
            if isinstance(value, bool):
                return False
            if isinstance(value, int):
                candidate = value
            elif isinstance(value, str) and value.isascii() and value.isdecimal():
                candidate = int(value)
            else:
                return False
            return 30000 <= candidate <= 30099

        def has_sealed_payload(value):
            if isinstance(value, dict):
                for key, nested in value.items():
                    if key in {"sealed_accessed", "validation_accessed"} and nested is True:
                        return True
                    if key in {"scenario_id", "scenario_ids"}:
                        values = nested if isinstance(nested, list) else [nested]
                        if any(is_sealed_scenario_id(item) for item in values):
                            return True
                    if has_sealed_payload(nested):
                        return True
            elif isinstance(value, list):
                return any(has_sealed_payload(item) for item in value)
            return False
        g6_payloads = [payload for name, payload in payloads.items() if name.startswith("g6-")]
        g7_payload = payloads.get("g7-sealed-evaluations.json")
        g6_safe = not any(has_sealed_payload(payload) for payload in g6_payloads)
        g7_safe = False
        if isinstance(g7_payload, dict):
            scenario_ids = g7_payload.get("scenario_ids")
            g7_safe = (
                scenario_ids == list(range(30000, 30100))
                and g7_payload.get("scenario_content") is None
                and g7_payload.get("evaluation_results") == []
                and g7_payload.get("sealed_accessed") is False
                and g7_payload.get("actual_unlock_count") == 0
                and g7_payload.get("status") == "locked_unexecuted"
            )
        checks["no_sealed_identities"] = g6_safe and g7_safe
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError):
        checks["no_sealed_identities"] = False
    details["manifest_sha256"] = hashlib.sha256(g6_manifest.read_bytes()).hexdigest() if g6_manifest.exists() else "missing"
    freeze_path = output_root / "freeze-manifest.json"
    try:
        freeze_payload = json.loads(freeze_path.read_text(encoding="utf-8"))
        expected_hash = freeze_payload.get("artifacts", {}).get("outputs/problem2_sr_mappo_v1/g5/manifests/g6-training-jobs.json")
        checks["manifest_hash"] = isinstance(expected_hash, str) and details["manifest_sha256"] == expected_hash
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError):
        checks["manifest_hash"] = False
    lock_path = root / "docs/evidence/g1/sealed_test_lock.yaml"
    try:
        import yaml
        lock_payload = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
        checks["sealed_lock"] = lock_payload.get("status") == "locked" and type(lock_payload.get("maximum_unlock_count")) is int and lock_payload.get("maximum_unlock_count") == 1 and type(lock_payload.get("actual_unlock_count")) is int and lock_payload.get("actual_unlock_count") == 0 and lock_payload.get("unlock_gate") == "G7" and lock_payload.get("resource_replenishment") == "pesticide_only" and lock_payload.get("battery_replenishment") == "inactive"
    except Exception:
        checks["sealed_lock"] = False
    details["sealed_lock"] = "read-only; no mutation attempted"
    # G6 replacement manifests are read-only inputs and live in their own
    # dynamic-ecology root.  Keep these checks independent of the historical
    # G5 artifacts above so old evidence remains byte-preserved.
    dynamic_manifest_root = root / "outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/manifests"
    dynamic_training = dynamic_manifest_root / "g6-training-jobs.json"
    dynamic_validation = dynamic_manifest_root / "g6-validation-evaluations.json"
    dynamic_freeze_path = dynamic_manifest_root.parent / "freeze-manifest.json"
    try:
        from scripts.freeze_g5 import freeze_dynamic_replacement

        dynamic_freeze = freeze_dynamic_replacement(root, write=False)
        checks["dynamic_g5_freeze"] = (
            dynamic_freeze.get("schema_version") == "g5-dynamic-replacement-freeze-v1"
            and dynamic_freeze.get("status") == "pass"
            and dynamic_freeze.get("ecology_id") == "dynamic_pest_v1"
            and dynamic_freeze.get("partition") == "development"
            and dynamic_freeze.get("replenished_resource") == "pesticide"
            and dynamic_freeze.get("validation_accessed") is False
            and dynamic_freeze.get("sealed_accessed") is False
            and dynamic_freeze.get("battery_replenishment_enabled") is False
        )
        checks["dynamic_replacement_matrix"] = (
            dynamic_freeze.get("matrix_complete") is True
            and dynamic_freeze.get("counts", {}).get("jobs") == 48
            and dynamic_freeze.get("counts", {}).get("episodes") == 960
            and dynamic_freeze.get("expected_job_identities") == dynamic_freeze.get("completed_job_identities")
        )
        details["dynamic_g5_freeze"] = str(dynamic_freeze_path)
    except Exception as exc:
        checks["dynamic_g5_freeze"] = False
        checks["dynamic_replacement_matrix"] = False
        details["dynamic_g5_freeze"] = f"unavailable: {type(exc).__name__}: {exc}"
    training_payload: dict[str, object] = {}
    validation_payload: dict[str, object] = {}
    try:
        training_payload = json.loads(dynamic_training.read_text(encoding="utf-8"))
        validation_payload = json.loads(dynamic_validation.read_text(encoding="utf-8"))
        if not isinstance(training_payload, dict) or not isinstance(validation_payload, dict):
            raise ValueError("replacement manifests must be JSON objects")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        training_payload = {}
        validation_payload = {}

    jobs = training_payload.get("jobs")
    training_provenance = training_payload.get("provenance")
    validation_provenance = validation_payload.get("provenance")
    if not isinstance(training_provenance, dict):
        training_provenance = {}
    if not isinstance(validation_provenance, dict):
        validation_provenance = {}
    source_commit_values = {
        str(training_provenance.get("source_commit", "")),
        str(validation_provenance.get("source_commit", "")),
    }
    source_scope_values = {
        str(training_payload.get("source_scope_sha256", "")),
        str(validation_payload.get("source_scope_sha256", "")),
    }
    frozen_commit = next(iter(source_commit_values), "")
    checks["frozen_source_commit"] = len(source_commit_values) == 1 and bool(frozen_commit) and all(
        len(value) == 40 and all(char in "0123456789abcdef" for char in value.lower())
        for value in source_commit_values
    )
    frozen_scope = next(iter(source_scope_values), "")
    checks["frozen_source_scope"] = len(source_scope_values) == 1 and bool(frozen_scope) and all(
        len(value) == 64 and all(char in "0123456789abcdef" for char in value.lower())
        for value in source_scope_values
    )
    if isinstance(jobs, list) and checks["frozen_source_commit"]:
        checks["frozen_source_commit"] = all(job.get("git_commit") == frozen_commit for job in jobs if isinstance(job, dict))
    if isinstance(jobs, list) and checks["frozen_source_scope"]:
        checks["frozen_source_scope"] = all(job.get("source_scope_sha256") == frozen_scope for job in jobs if isinstance(job, dict))

    def _module_has(name: str, attribute: str | None = None) -> bool:
        try:
            module = importlib.import_module(name)
            return attribute is None or callable(getattr(module, attribute, None))
        except Exception:
            return False

    checks["runner_available"] = _module_has("problem2.training.formal_g6", "run_formal_job")
    checks["recovery_available"] = _module_has("problem2.experiments.recovery", "recover_checkpoint")
    checks["checkpoint_validator_available"] = _module_has("problem2.evaluation.validator", "validate_long_table")
    checks["validation_evaluator_available"] = _module_has("problem2.training.formal_g6", "evaluate_formal_checkpoint")

    identities = [job.get("canonical_training_identity") for job in jobs if isinstance(job, dict)] if isinstance(jobs, list) else []
    checks["scheduler_order"] = (
        isinstance(jobs, list)
        and len(jobs) == 375
        and isinstance(training_payload.get("scheduler_order"), list)
        and training_payload["scheduler_order"] == sorted(str(value) for value in identities)
        and len(identities) == len(jobs)
        and len(set(identities)) == len(identities)
    )
    expected_storage = training_payload.get("expected_storage_bytes")
    expected_gpu_hours = training_payload.get("expected_gpu_hours")
    headroom = training_payload.get("atomic_storage_headroom_bytes", 0)
    checks["storage_budget"] = type(expected_storage) is int and expected_storage > 0
    checks["gpu_hours"] = isinstance(expected_gpu_hours, (int, float)) and not isinstance(expected_gpu_hours, bool) and float(expected_gpu_hours) > 0.0
    checks["dynamic_ecology"] = (
        training_payload.get("ecology_id") == "dynamic_pest_v1"
        and validation_payload.get("ecology_id") == "dynamic_pest_v1"
        and isinstance(jobs, list)
        and len(jobs) == 375
        and all(isinstance(job, dict) and job.get("ecology_id") == "dynamic_pest_v1" for job in jobs)
    )
    expected_dynamic_root = "outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g6"
    checks["dynamic_output_root"] = (
        training_payload.get("output_root") == expected_dynamic_root
        and validation_payload.get("output_root") == expected_dynamic_root
    )
    restricted_ok = True
    if isinstance(jobs, list):
        for job in jobs:
            if not isinstance(job, dict):
                restricted_ok = False
                break
            if job.get("family") in {"sr_mappo_ablation", "sr_mappo_sensitivity"} and job.get("method") != "sr_mappo_mobile":
                restricted_ok = False
                break
    else:
        restricted_ok = False
    checks["restricted_experiment_families"] = restricted_ok
    checks["validation_panel"] = (
        validation_payload.get("scenario_ids") == list(range(20000, 20050))
        and validation_payload.get("scenario_content") is None
        and validation_payload.get("deterministic_policy") is True
        and validation_payload.get("sealed_accessed") is False
    )
    try:
        import torch

        hardware = {
            "python": platform.python_version(),
            "system": platform.system(),
            "machine": platform.machine(),
            "torch_version": torch.__version__,
            "cuda_available": bool(torch.cuda.is_available()),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "vram_bytes": int(torch.cuda.get_device_properties(0).total_memory) if torch.cuda.is_available() else None,
        }
        checks["hardware_inventory"] = bool(hardware["python"] and hardware["system"] and hardware["machine"] and hardware["torch_version"])
        details["hardware_inventory"] = json.dumps(hardware, sort_keys=True)
    except Exception:
        checks["hardware_inventory"] = False

    try:
        disk = shutil.disk_usage(root)
        expected_bytes = int(expected_storage) if checks["storage_budget"] else 0
        atomic_headroom = int(headroom) if isinstance(headroom, int) and headroom > 0 else max(1, expected_bytes // 10)
        required_bytes = expected_bytes + atomic_headroom
        resource_budget = {
            "expected_storage_bytes": expected_bytes,
            "atomic_headroom_bytes": atomic_headroom,
            "required_bytes_with_atomic_headroom": required_bytes,
            "available_bytes": int(disk.free),
            "expected_gpu_hours": float(expected_gpu_hours) if checks["gpu_hours"] else 0.0,
        }
        checks["disk_budget"] = expected_bytes > 0 and int(disk.free) >= required_bytes
    except OSError:
        resource_budget = {
            "expected_storage_bytes": 0,
            "atomic_headroom_bytes": 0,
            "required_bytes_with_atomic_headroom": 0,
            "available_bytes": 0,
            "expected_gpu_hours": 0.0,
        }
        checks["disk_budget"] = False
    details["resource_budget"] = json.dumps(resource_budget, sort_keys=True)
    result = {
        "gate": gate,
        "checks": checks,
        "details": details,
        "resource_budget": resource_budget,
        "all_pass": all(checks.values()),
        "queue_created": False,
        "sealed_accessed": False,
    }
    return result


def run_cli(name: str, *, default_partition: str = "development", blocked_reason: str | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{name}: G5 dry-run guard only")
    parser.add_argument("--scenario-id", type=int)
    parser.add_argument("--partition", default=default_partition)
    parser.add_argument("--sealed-accessed", action="store_true")
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--ecology-mode",
        choices=tuple(mode.value for mode in EcologyMode),
        default=EcologyMode.DYNAMIC.value,
    )
    args = parser.parse_args()
    try:
        if args.scenario_id is not None:
            assert_partition_allowed(gate="G5", partition=args.partition, scenario_id=args.scenario_id)
        assert_no_sealed_access(gate="G5", scenario_id=args.scenario_id, partition=args.partition, sealed_accessed=args.sealed_accessed)
    except SealedAccessError as exc:
        print(f"sealed access denied: {exc}", file=sys.stderr)
        return 2
    gate = "G7" if "g7" in name else "G6" if "g6" in name else "G5"
    try:
        resolve_output_root(
            args.root,
            gate,
            None,
            primary=True,
            partition=args.partition,
            ecology_mode=args.ecology_mode,
        )
    except ValueError as exc:
        print(f"dynamic ecology denied: {exc}", file=sys.stderr)
        return 2
    if blocked_reason is not None:
        report = read_only_preflight(args.root, gate="G6" if "g6" in name else "G7")
        print(json.dumps(report, sort_keys=True))
        print(f"sealed lock unchanged: {blocked_reason}", file=sys.stderr)
        return 2
    print(f"{name}: dry-run only; no jobs executed")
    return 0
