from __future__ import annotations

from typing import Mapping


ABLATION_GROUPS = {
    "no_observation_normalization": ("observation_normalization",),
    "no_return_normalization": ("return_normalization",),
    "no_network_stabilization": ("orthogonal_initialization", "layer_normalization"),
    "no_robust_value_update": ("value_clipping", "huber_value_loss"),
    "no_learning_rate_decay": ("learning_rate_decay",),
}


def validate_ablation_diff(full: Mapping[str, object], variant: Mapping[str, object]) -> str:
    if set(full) != set(variant):
        raise ValueError("ablation configuration keys must match")
    changed = {key for key in full if full[key] != variant[key]}
    matches = [name for name, fields in ABLATION_GROUPS.items() if changed == set(fields)]
    if len(matches) != 1:
        raise ValueError("ablation must differ by exactly one declared remove-one group")
    for key, value in full.items():
        if key in changed:
            if value is not True:
                raise ValueError("full ablation configuration must enable declared fields")
        elif value is not variant[key]:
            raise ValueError("ablation variant must preserve undeclared fields exactly")
    for key in changed:
        if variant[key] is not False:
            raise ValueError("ablation remove-one values must be false")
    return matches[0]


__all__ = ["ABLATION_GROUPS", "validate_ablation_diff"]
