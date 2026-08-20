from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys

from problem2.domain import Event
from problem2.simulation.replay import canonical_event_jsonl, replay_digest


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "problem2" / "g2_deterministic.yaml"


def test_event_json_is_canonical_and_digest_covers_exact_bytes() -> None:
    event = Event(
        step=0,
        phase="action",
        kind="sample",
        entity_id="u0",
        payload=(("b", 2), ("a", 1)),
    )

    rendered = canonical_event_jsonl([event])

    assert rendered == (
        b'{"entity_id":"u0","kind":"sample","payload":{"a":1,"b":2},'
        b'"phase":"action","step":0}\n'
    )
    assert replay_digest([event]) == hashlib.sha256(rendered).hexdigest()


def _run_worker(output_path: Path, hash_seed: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONHASHSEED"] = hash_seed
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "problem2.simulation.replay",
            "--config",
            str(CONFIG_PATH),
            "--output",
            str(output_path),
            "--seed",
            "42",
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def test_hash_seed_does_not_change_full_fixture_trace(tmp_path: Path) -> None:
    first_path = tmp_path / "first.jsonl"
    second_path = tmp_path / "second.jsonl"

    first = _run_worker(first_path, "1")
    second = _run_worker(second_path, "98765")

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert first_path.read_bytes() == second_path.read_bytes()
    assert len(first_path.read_bytes().splitlines()) > 50
