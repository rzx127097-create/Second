"""Shared dry-run CLI guard; Task 8 never executes experiment rows."""
from __future__ import annotations

import argparse
import json
import hashlib
import shutil
import subprocess
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
        checks["frozen_source_remote"] = bool(local and local == remote)
        details["frozen_source_remote"] = f"local={local[:12]} remote={remote[:12]}"
    except (OSError, subprocess.CalledProcessError):
        checks["frozen_source_remote"] = False
    reconciliation = root / "docs/audits/g4-lineage-reconciliation.md"
    checks["g4_reconciliation"] = reconciliation.exists() and "passes" in reconciliation.read_text(encoding="utf-8").lower() if reconciliation.exists() else False
    road_candidates = list((root / "outputs/problem2_sr_mappo_v1/g2/roads").glob("*/metadata.json")) if (root / "outputs/problem2_sr_mappo_v1/g2/roads").exists() else []
    checks["road_cache_provenance"] = False
    for candidate in road_candidates:
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
            required = {"schema_version", "source", "projection", "grid", "topology", "preprocess_version"}
            source = payload.get("source", {})
            checks["road_cache_provenance"] = required <= set(payload) and isinstance(source.get("sha256"), str) and bool(source.get("crs")) and bool(payload.get("grid", {}).get("shape")) and bool(payload.get("topology"))
            if checks["road_cache_provenance"]:
                break
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
    output_root = root / "outputs/problem2_sr_mappo_v1/g5"
    checks["output_confinement"] = output_root.resolve().parent == (root / "outputs/problem2_sr_mappo_v1").resolve() and output_root.resolve().name == "g5"
    try:
        checks["disk_space"] = shutil.disk_usage(root).free > 0
    except OSError:
        checks["disk_space"] = False
    checks["runtime_inventory"] = bool(sys.version_info >= (3, 11) and sys.executable)
    g6_manifest = output_root / "manifests/g6-training-jobs.json"
    try:
        text = g6_manifest.read_text(encoding="utf-8") if g6_manifest.exists() else ""
        checks["no_sealed_identities"] = "30000" not in text and "30099" not in text and "sealed_test" not in text
    except OSError:
        checks["no_sealed_identities"] = False
    details["manifest_sha256"] = hashlib.sha256(g6_manifest.read_bytes()).hexdigest() if g6_manifest.exists() else "missing"
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
