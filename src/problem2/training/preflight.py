"""Fail-closed, read-only device checks for the G5 development smoke."""

from __future__ import annotations

import platform
from pathlib import Path
from typing import Any

import torch

from problem2.experiments.g5_contract import load_g5_contract


def run_preflight(device: str = "cpu", root: Path | str | None = None) -> dict[str, Any]:
    repository_root = Path(root or Path(__file__).resolve().parents[3]).resolve()
    requested = str(device).lower()
    report: dict[str, Any] = {
        "schema_version": "g5-smoke-preflight-v1",
        "device": requested,
        "python": platform.python_version(),
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda,
        "cuda_visible": bool(torch.cuda.is_available()),
        "gpu_name": None,
        "vram_bytes": None,
        "deterministic_algorithms": False,
        "cudnn_deterministic": bool(torch.backends.cudnn.deterministic),
        "cudnn_benchmark": bool(torch.backends.cudnn.benchmark),
        "validation_accessed": False,
        "sealed_accessed": False,
        "battery_replenishment_enabled": False,
        "ecology_mode": "dynamic",
    }
    try:
        contract = load_g5_contract(repository_root)
        if contract.validation_accessed or contract.sealed_accessed:
            raise RuntimeError("contract records validation/sealed access")
        if requested not in {"cpu", "cuda"}:
            raise ValueError("device must be cpu or cuda")
        if requested == "cuda":
            if not torch.cuda.is_available():
                raise RuntimeError("CUDA is unavailable")
            index = torch.cuda.current_device()
            report["gpu_name"] = torch.cuda.get_device_name(index)
            props = torch.cuda.get_device_properties(index)
            report["vram_bytes"] = int(props.total_memory)
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        report["deterministic_algorithms"] = bool(torch.are_deterministic_algorithms_enabled())
        report["cudnn_deterministic"] = bool(torch.backends.cudnn.deterministic)
        report["cudnn_benchmark"] = bool(torch.backends.cudnn.benchmark)
        report["status"] = "pass"
    except Exception as error:  # fail closed and make the blocker auditable
        report["status"] = "fail"
        report["reason"] = f"{type(error).__name__}: {error}"
    return report


__all__ = ["run_preflight"]
