from __future__ import annotations

import argparse
from pathlib import Path

from problem2.experiments.g4_audit import audit_g4_mechanism


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit G4 scarcity mechanism evidence")
    parser.add_argument("--config", default="docs/evidence/g4/g4_contract.yaml")
    parser.add_argument("--output-root", default="outputs/problem2_sr_mappo_v1/g4")
    parser.add_argument("--report", default="outputs/problem2_sr_mappo_v1/g4/g4-mechanism-audit.json")
    args = parser.parse_args()
    report = audit_g4_mechanism(Path(args.config), Path(args.output_root), Path(args.report))
    print(f"status={report['status']} artifacts={len(report['output_artifact_hashes'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
