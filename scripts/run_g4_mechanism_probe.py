from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from problem2.experiments.g4_activation import run_probe_matrix
from problem2.experiments.g4_contract import load_g4_contract, load_g4_probe_manifest


def main() -> None:
    contract = load_g4_contract(ROOT / "docs/evidence/g4/g4_contract.yaml")
    manifest = load_g4_probe_manifest(ROOT / "docs/evidence/g4/g4_probe_manifest.yaml")
    result = run_probe_matrix(contract, manifest, output_root=ROOT / contract.output_root)
    print(result["activation_window"])


if __name__ == "__main__":
    main()
