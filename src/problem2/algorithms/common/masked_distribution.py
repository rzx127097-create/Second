from __future__ import annotations

import torch
from torch import Tensor
from torch.distributions import Categorical


def masked_categorical(logits: Tensor, mask: Tensor) -> Categorical:
    """Build a categorical distribution from the exact behavior-time mask."""

    logits = torch.as_tensor(logits)
    if not torch.is_floating_point(logits):
        logits = logits.to(dtype=torch.get_default_dtype())
    if logits.ndim == 0:
        raise ValueError("logits must include an action dimension")

    mask = torch.as_tensor(mask, device=logits.device, dtype=torch.bool)
    if mask.shape != logits.shape:
        raise ValueError("logits and mask must have the same shape")
    if not torch.isfinite(logits).all():
        raise ValueError("logits must be finite")
    if not mask.any(dim=-1).all():
        raise ValueError("each row must have at least one valid action")

    masked_logits = logits.masked_fill(~mask, float("-inf"))
    return Categorical(logits=masked_logits)
