"""Categorical policies with exact action-mask replay semantics."""

from __future__ import annotations

from typing import Any


def masked_logits(logits: Any, mask: Any) -> Any:
    """Set illegal logits to negative infinity without changing legal logits."""

    try:
        import torch
    except ImportError as exc:  # pragma: no cover - exercised only without torch
        raise RuntimeError("masked_logits requires PyTorch tensors") from exc
    mask = mask.to(dtype=torch.bool, device=logits.device)
    if logits.shape != mask.shape:
        raise ValueError("logits and mask must have identical shape")
    if (~mask).all(dim=-1).any():
        raise ValueError("every action row must contain at least one legal action")
    # Negative infinity is intentional: replaying a now-illegal action must
    # produce ``-inf`` log-probability rather than a tiny but non-zero mass.
    return logits.masked_fill(~mask, float("-inf"))


def masked_categorical(logits: Any, mask: Any):
    """Return a torch Categorical distribution whose illegal actions have zero probability."""

    try:
        import torch.distributions
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("masked_categorical requires PyTorch") from exc
    return torch.distributions.Categorical(logits=masked_logits(logits, mask))


def sample_action(logits: Any, mask: Any, deterministic: bool = False):
    distribution = masked_categorical(logits, mask)
    action = distribution.probs.argmax(dim=-1) if deterministic else distribution.sample()
    return action, distribution.log_prob(action), distribution.entropy()
