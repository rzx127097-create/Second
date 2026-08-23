from __future__ import annotations

import torch
from torch import Tensor
from torch.distributions import Categorical


class MaskedCategorical(Categorical):
    """Categorical distribution that rejects replay against a forbidden action."""

    def __init__(self, *, logits: Tensor, behavior_mask: Tensor) -> None:
        self.behavior_mask = behavior_mask
        super().__init__(logits=logits)

    def log_prob(self, value: Tensor) -> Tensor:
        actions = torch.as_tensor(value, device=self.behavior_mask.device)
        if actions.shape != self.behavior_mask.shape[:-1]:
            raise ValueError("action shape does not match behavior mask")
        if torch.is_floating_point(actions):
            if not torch.equal(actions, actions.to(dtype=torch.long)):
                raise ValueError("actions must be integer indices")
        elif actions.dtype == torch.bool:
            raise ValueError("actions must be integer indices")
        actions = actions.to(dtype=torch.long)
        if (actions < 0).any() or (actions >= self.behavior_mask.shape[-1]).any():
            raise ValueError("action is outside the behavior mask")
        allowed = self.behavior_mask.gather(-1, actions.unsqueeze(-1)).squeeze(-1)
        if not allowed.all():
            raise ValueError("action selects a masked behavior action")
        return super().log_prob(actions)


def masked_categorical(logits: Tensor, mask: Tensor) -> MaskedCategorical:
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
    return MaskedCategorical(logits=masked_logits, behavior_mask=mask)


__all__ = ["MaskedCategorical", "masked_categorical"]
