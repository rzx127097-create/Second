"""Shared dry-run CLI guard; Task 8 never executes experiment rows."""
from __future__ import annotations

import argparse
import json
import hashlib
import shutil
import subprocess
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from problem2.evaluation.sealed_lock import SealedAccessError, assert_no_sealed_access, assert_partition_allowed


def read_only_preflight(root: Path = ROOT, *, gate: str = "G6") -> dict[str, object]:
    """Audit frozen inputs without queueing jobs, writing artifacts, or reading sealed rows."""
    root = Path(root).resolve()
    checks: dict[str, bool] = {}
    details: dict[str, str] = {}
    try:
        from problem2.experiments.g5_contract import load_g5_contract
        contract = load_g5_contract(root)
        checks["frozen_contract"] = bool(contract.file_hashes)
        checks["registry_hashes"] = all(bool(value) for value in contract.file_hashes.values())
        details["frozen_contract"] = "loaded strict G5 contract"
    except Exception:
        checks["frozen_contract"] = False
        checks["registry_hashes"] = False
    try:
        status = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=True).stdout.splitlines()
        status = [line for line in status if "_tmp_docx_assets" not in line]
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
    checks["output_confinement"] = output_root.resolve().parent == (root / "outputs/problem2_sr_mappo_v1").resolve() and output_root.resolve().name == "g5"
    try:
        checks["disk_space"] = shutil.disk_usage(root).free >= 1024 * 1024 * 1024
    except OSError:
        checks["disk_space"] = False
    checks["runtime_inventory"] = bool(sys.version_info >= (3, 11) and sys.executable and platform.system() and platform.machine())
    g6_manifest = output_root / "manifests/g6-training-jobs.json"
    try:
        paths = list((output_root / "manifests").glob("g6-*.json")) + list((output_root / "manifests").glob("g7-*.json"))
        text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        checks["no_sealed_identities"] = "30000" not in text and "30099" not in text and "sealed_test" not in text
    except OSError:
        checks["no_sealed_identities"] = False
    details["manifest_sha256"] = hashlib.sha256(g6_manifest.read_bytes()).hexdigest() if g6_manifest.exists() else "missing"
    checks["manifest_hash"] = details["manifest_sha256"] == "ff4d20a347be565f974d39ba24ec382b231d6def326243c06943bd81f2733553"
    lock_path = root / "docs/evidence/g1/sealed_test_lock.yaml"
    try:
        import yaml
        lock_payload = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
        checks["sealed_lock"] = lock_payload.get("status") == "locked" and type(lock_payload.get("maximum_unlock_count")) is int and lock_payload.get("maximum_unlock_count") == 1 and type(lock_payload.get("actual_unlock_count")) is int and lock_payload.get("actual_unlock_count") == 0 and lock_payload.get("unlock_gate") == "G7" and lock_payload.get("resource_replenishment") == "pesticide_only" and lock_payload.get("battery_replenishment") == "inactive"
    except Exception:
        checks["sealed_lock"] = False
    details["sealed_lock"] = "read-only; no mutation attempted"
    return {"gate": gate, "checks": checks, "details": details, "all_pass": all(checks.values()), "queue_created": False, "sealed_accessed": False}


def run_cli(name: str, *, default_partition: str = "development", blocked_reason: str | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{name}: G5 dry-run guard only")
    parser.add_argument("--scenario-id", type=int)
    parser.add_argument("--partition", default=default_partition)
    parser.add_argument("--sealed-accessed", action="store_true")
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        if args.scenario_id is not None:
            assert_partition_allowed(gate="G5", partition=args.partition, scenario_id=args.scenario_id)
        assert_no_sealed_access(gate="G5", scenario_id=args.scenario_id, partition=args.partition, sealed_accessed=args.sealed_accessed)
    except SealedAccessError as exc:
        print(f"sealed access denied: {exc}", file=sys.stderr)
        return 2
    if blocked_reason is not None:
        report = read_only_preflight(args.root, gate="G6" if "g6" in name else "G7")
        print(json.dumps(report, sort_keys=True))
        print(f"sealed lock unchanged: {blocked_reason}", file=sys.stderr)
        return 2
    print(f"{name}: dry-run only; no jobs executed")
    return 0
