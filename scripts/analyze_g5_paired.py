"""JSON adapter for the non-sealed G5 paired estimator."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
from problem2.statistics.paired import hierarchical_paired_bootstrap


def _checked_path(path: Path) -> Path:
    resolved = path.resolve()
    root = (REPO_ROOT / "outputs" / "problem2_sr_mappo_v1").resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("input/output must be under the frozen output root") from exc
    if any(part.lower() in {"raw", "sealed", "sealed_test"} for part in resolved.parts):
        raise ValueError("raw and sealed locators are forbidden")
    return resolved


def _validated_payload(payload: object) -> dict:
    if not isinstance(payload, dict) or payload.get("validated") is not True:
        raise ValueError("payload requires explicit validated=true")
    provenance = payload.get("provenance")
    if not isinstance(provenance, dict) or provenance.get("status") != "validated":
        raise ValueError("payload requires validated provenance")
    if str(provenance.get("partition", "")).lower() in {"sealed", "sealed_test"}:
        raise ValueError("sealed partition is forbidden")
    if any("raw" in str(value).lower() or "sealed" in str(value).lower() for value in provenance.values()):
        raise ValueError("raw/sealed provenance locator is forbidden")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze validated paired G5 rows")
    parser.add_argument("--input", type=Path, help="explicit JSON input path; stdin when omitted")
    parser.add_argument("--output", type=Path, help="explicit JSON output path; stdout when omitted")
    parser.add_argument("--metric", required=False, help="metric name (or payload metric)")
    parser.add_argument("--replicates", type=int, default=10000)
    args = parser.parse_args(argv)
    try:
        input_path = _checked_path(args.input) if args.input else None
        output_path = _checked_path(args.output) if args.output else None
        source = input_path.read_text(encoding="utf-8") if input_path else sys.stdin.read()
        payload = _validated_payload(json.loads(source))
        rows = payload.get("rows")
        metric = args.metric or payload.get("metric")
        if not isinstance(rows, list) or not isinstance(metric, str):
            raise ValueError("payload requires rows and metric")
        result = hierarchical_paired_bootstrap(rows, metric, B=args.replicates)
        encoded = json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":"))
        if output_path:
            output_path.write_text(encoded + "\n", encoding="utf-8")
        else:
            print(encoded)
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
