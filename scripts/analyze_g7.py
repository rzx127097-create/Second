"""JSON adapter for pure G7 analysis helpers; it never opens sealed paths."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
from problem2.statistics.convergence import summarize_convergence
from problem2.statistics.diagnosis import diagnose_result_bundle
from problem2.statistics.mechanism import summarize_mechanism


def _checked_path(path: Path) -> Path:
    resolved = path.resolve()
    root = (REPO_ROOT / "outputs" / "problem2_sr_mappo_v1").resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("input/output must be under the frozen output root") from exc
    if any(any(token in part.lower() for token in ("raw", "sealed")) for part in resolved.parts):
        raise ValueError("raw and sealed locators are forbidden")
    return resolved


def _validated_payload(payload: object) -> dict:
    if not isinstance(payload, dict) or payload.get("validated") is not True:
        raise ValueError("payload requires explicit validated=true")
    provenance = payload.get("provenance")
    if not isinstance(provenance, dict) or provenance.get("status") != "validated":
        raise ValueError("payload requires validated provenance")
    if provenance.get("partition") != "development":
        raise ValueError("partition must be explicit development")
    if any("raw" in str(value).lower() or "sealed" in str(value).lower() for value in provenance.values()):
        raise ValueError("raw/sealed provenance locator is forbidden")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze validated non-sealed G7-compatible rows")
    parser.add_argument("--input", type=Path, help="explicit JSON input path; stdin when omitted")
    parser.add_argument("--output", type=Path, help="explicit JSON output path; stdout when omitted")
    parser.add_argument("--analysis", choices=("convergence", "mechanism", "diagnosis"), default="mechanism")
    parser.add_argument("--budget", type=int)
    args = parser.parse_args(argv)
    try:
        input_path = _checked_path(args.input) if args.input else None
        output_path = _checked_path(args.output) if args.output else None
        source = input_path.read_text(encoding="utf-8") if input_path else sys.stdin.read()
        payload = _validated_payload(json.loads(source))
        rows = payload.get("rows")
        if not isinstance(rows, list):
            raise ValueError("payload requires rows")
        if args.analysis == "convergence":
            budget = args.budget if args.budget is not None else payload.get("budget")
            if not isinstance(budget, int):
                raise ValueError("convergence requires integer budget")
            result = summarize_convergence(rows, budget)
        elif args.analysis == "diagnosis":
            result = diagnose_result_bundle(rows, payload.get("audit_records", []))
        else:
            result = summarize_mechanism(rows)
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
