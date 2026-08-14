"""Portable JSON subprocess boundary used by experiment orchestration."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any, Sequence


def run_utf8_json_child(command: Sequence[str], *, cwd: str | Path) -> dict[str, Any]:
    """Run a Python CLI with an explicit UTF-8 pipe contract on Windows."""

    environment = dict(os.environ)
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONUTF8"] = "1"
    result = subprocess.run(
        [str(part) for part in command],
        cwd=Path(cwd),
        env=environment,
        text=True,
        encoding="utf-8",
        errors="strict",
        capture_output=True,
        check=False,
    )
    payload: dict[str, Any]
    if result.stdout.strip():
        parsed = json.loads(result.stdout)
        if not isinstance(parsed, dict):
            raise ValueError("child JSON output must be an object")
        payload = parsed
    else:
        payload = {"status": "failed", "error": result.stderr.strip() or "child produced no JSON output"}
    return {"returncode": int(result.returncode), "payload": payload, "stderr": result.stderr}


__all__ = ["run_utf8_json_child"]
