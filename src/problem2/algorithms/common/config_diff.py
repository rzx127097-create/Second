"""Machine-readable SR-MAPPO versus same-source MAPPO configuration diff."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from collections.abc import Mapping
from typing import Any


_STABILITY_PREFIX = "stability_components."


def _mapping(value: Any) -> dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError("configuration must be a mapping or dataclass")


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key in sorted(value):
            result.update(_flatten(value[key], f"{prefix}{key}."))
        return result
    return {prefix[:-1]: value}


def configuration_diff(
    sr_config: Any,
    mappo_config: Any,
) -> dict[str, Any]:
    """Return a diff that is valid only when stability flags changed."""

    sr = _flatten(_mapping(sr_config))
    mappo = _flatten(_mapping(mappo_config))
    keys = sorted(set(sr) | set(mappo))
    changed = [key for key in keys if sr.get(key) != mappo.get(key)]
    non_stability = [
        key
        for key in changed
        if not key.startswith(_STABILITY_PREFIX)
    ]
    if non_stability:
        raise ValueError(
            "non-stability configuration drift: " + ", ".join(non_stability)
        )
    changes = {
        key: {"sr_mappo": sr.get(key), "mappo": mappo.get(key)}
        for key in changed
    }
    return {
        "algorithm_name": "SR-MAPPO",
        "changed_keys": changed,
        "changes": changes,
        "only_declared_stability_flags_changed": True,
    }


__all__ = ["configuration_diff"]
