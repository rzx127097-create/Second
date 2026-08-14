"""Validate event-complete episode records before aggregation."""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = {
    "run_id", "method", "scale", "training_seed", "scenario_id", "config_hash", "git_commit",
    "split", "reduction_rate", "success", "transferred_l",
}
NUMERIC_FIELDS = {
    "total_reward", "reward_control", "reward_service", "reward_coordination", "reward_invalid",
    "wait_s", "pesticide_disabled_s", "vehicle_distance_m", "pesticide_initial_l",
    "pesticide_remaining_l", "pesticide_sprayed_l", "success_threshold", "steps", "event_count",
}


def _parse_success(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value in (0, 1):
        return bool(value)
    raise ValueError("success must be boolean or 0/1")


def _parse_provisional(row: Mapping[str, Any], *, strict: bool) -> bool | None:
    values: list[bool] = []
    if "provisional" in row:
        values.append(_parse_success(row["provisional"]))
    for status_key in ("parameter_status", "status"):
        if status_key not in row:
            continue
        status = row[status_key]
        if isinstance(status, str):
            normalized = status.strip().lower()
            if normalized in {"provisional", "smoke", "true", "1"}:
                values.append(True)
            elif normalized in {"formal", "final", "sealed", "verified", "false", "0"}:
                values.append(False)
            else:
                raise ValueError(f"{status_key} must identify provisional or formal data")
        else:
            values.append(_parse_success(status))
    if not values:
        if strict:
            raise ValueError("missing provisional/parameter_status")
        return None
    if len(set(values)) != 1:
        raise ValueError("provisional and parameter_status disagree")
    return values[0]


def validate_episode_records(records: Iterable[Mapping[str, Any]], *, strict: bool = False) -> list[dict[str, Any]]:
    rows = [dict(record) for record in records]
    if not rows:
        raise ValueError("episode records are empty")
    seen: set[str] = set()
    seen_observations: set[tuple[str, str, int, str]] = set()
    for row in rows:
        missing = REQUIRED_FIELDS - row.keys()
        if not strict:
            missing.discard("split")
        if missing:
            raise ValueError(f"missing episode fields: {sorted(missing)}")
        run_id = str(row["run_id"])
        if not run_id:
            raise ValueError("run_id must be non-empty")
        if strict:
            identity_fields = ("run_id", "method", "scale", "scenario_id", "config_hash", "git_commit", "split")
            if any(not isinstance(row[field], str) or not row[field].strip() for field in identity_fields):
                raise ValueError("identity and split fields must be non-empty strings")
            for status_field in ("parameter_status", "status"):
                if status_field in row and (not isinstance(row[status_field], str) or not row[status_field].strip()):
                    raise ValueError("status fields must be non-empty strings")
        if run_id in seen:
            raise ValueError(f"duplicate run_id: {run_id}")
        seen.add(run_id)
        try:
            raw_seed = row["training_seed"]
            seed = int(raw_seed)
            if isinstance(raw_seed, bool) or float(raw_seed) != seed:
                raise ValueError("training_seed must be an integer")
            reduction = float(row["reduction_rate"])
            transferred = float(row["transferred_l"])
        except (TypeError, ValueError) as exc:
            raise ValueError("training_seed and numeric metrics must be valid numbers") from exc
        if not math.isfinite(reduction) or not math.isfinite(transferred):
            raise ValueError("numeric metrics must be finite")
        if not 0.0 <= reduction <= 1.0:
            raise ValueError("reduction_rate must lie in [0, 1]")
        if transferred < 0:
            raise ValueError("transferred_l must be non-negative")
        for field in NUMERIC_FIELDS:
            if field not in row or row[field] is None:
                continue
            try:
                value = float(row[field])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{field} must be numeric") from exc
            if not math.isfinite(value):
                raise ValueError(f"{field} must be finite")
            if field in {"steps", "event_count", "wait_s", "pesticide_disabled_s", "vehicle_distance_m", "pesticide_initial_l", "pesticide_remaining_l", "pesticide_sprayed_l"} and value < 0:
                raise ValueError(f"{field} must be non-negative")
            if field == "success_threshold" and not 0.0 <= value <= 1.0:
                raise ValueError("success_threshold must lie in [0, 1]")
        if all(field in row for field in ("pesticide_initial_l", "pesticide_remaining_l", "pesticide_sprayed_l")):
            initial = float(row["pesticide_initial_l"])
            remaining = float(row["pesticide_remaining_l"])
            sprayed = float(row["pesticide_sprayed_l"])
            if abs(initial - remaining - sprayed) > 1e-7:
                raise ValueError("pesticide ledger does not conserve volume")
        if "events" in row:
            events = row["events"]
            if not isinstance(events, list):
                raise ValueError("events must be a list")
            for event in events:
                if not isinstance(event, Mapping) or not str(event.get("event_type", "")):
                    raise ValueError("each event must have an event_type")
                for field in ("amount_l", "duration_s", "travelled_distance_m"):
                    if field in event:
                        value = float(event[field])
                        if not math.isfinite(value) or value < 0:
                            raise ValueError(f"event {field} must be finite and non-negative")
        row["success"] = _parse_success(row["success"])
        status = _parse_provisional(row, strict=strict)
        if status is not None:
            row["provisional"] = status
        observation = (str(row["method"]), str(row["scale"]), seed, str(row["scenario_id"]))
        if observation in seen_observations:
            raise ValueError("duplicate method/scale/training_seed/scenario_id")
        seen_observations.add(observation)
        row["training_seed"] = seed
        row["reduction_rate"] = reduction
        row["transferred_l"] = transferred
    return rows


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read one UTF-8 JSON object per non-empty input line."""
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                raise ValueError(f"blank/empty JSONL line at line {line_number}")
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at line {line_number}") from exc
            if not isinstance(value, Mapping):
                raise ValueError(f"JSONL line {line_number} must be an object")
            if "split" not in value:
                raise ValueError("missing episode fields: ['split']")
            records.append(dict(value))
    return validate_episode_records(records, strict=True)
