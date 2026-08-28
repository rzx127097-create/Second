from __future__ import annotations

from pathlib import Path
import sys
import argparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from problem2.experiments.g4_activation import run_probe_matrix
from problem2.experiments.g4_audit import build_g4_artifact_manifest
from problem2.experiments.g4_contract import load_g4_contract, load_g4_probe_manifest
from problem2.experiments.g4_counterfactual import run_counterfactual_probe
from problem2.experiments.ecology_policy import EcologyMode, resolve_output_root


def _write_json(path: Path, payload: object) -> None:
    import json

    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the development-only G4 mechanism probe.")
    parser.add_argument(
        "--ecology-mode",
        choices=tuple(mode.value for mode in EcologyMode),
        default=EcologyMode.DYNAMIC.value,
    )
    args = parser.parse_args()
    contract = load_g4_contract(ROOT / "docs/evidence/g4/g4_contract.yaml")
    manifest = load_g4_probe_manifest(ROOT / "docs/evidence/g4/g4_probe_manifest.yaml")
    try:
        output_root = resolve_output_root(
            ROOT,
            "G4",
            ROOT / contract.output_root,
            primary=True,
            partition="development",
            ecology_mode=args.ecology_mode,
        )
    except ValueError as exc:
        parser.error(str(exc))
    result = run_probe_matrix(contract, manifest, output_root=output_root)
    fixed, mobile = result["arms"]
    counterfactual = run_counterfactual_probe(
        fixed, mobile, output_path=str(output_root / "counterfactual-summary.json")
    )
    lineage = result["lineage"]
    _write_json(
        output_root / "activation-summary.json",
        {
            "schema_version": "g4-activation-index.v1",
            "status": "descriptive",
            "activation_window": result["activation_window"],
            "arms": {
                "fixed_support_probe": "fixed/activation-summary.json",
                "mobile_support_probe": "mobile/activation-summary.json",
            },
            "paired_counterfactual": "counterfactual-summary.json",
            **lineage,
        },
    )
    _write_json(output_root / "provenance.json", lineage)
    _write_json(output_root / "artifact-manifest.json", build_g4_artifact_manifest(output_root))
    print(result["activation_window"])


if __name__ == "__main__":
    main()
