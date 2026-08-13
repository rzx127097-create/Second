from __future__ import annotations

import numpy as np
import pytest

from problem2.algorithms.common.gae import compute_gae
from problem2.algorithms.common.masked_distribution import masked_categorical


def test_gae_matches_hand_calculated_terminal_episode() -> None:
    rewards = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    values = np.array([0.5, 1.0, 1.5], dtype=np.float64)
    dones = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    advantages, returns = compute_gae(rewards, values, dones, gamma=0.9, gae_lambda=0.8)
    deltas = np.array([1.4, 2.35, 1.5])
    expected_adv = np.array([
        deltas[0] + 0.9 * 0.8 * (deltas[1] + 0.9 * 0.8 * deltas[2]),
        deltas[1] + 0.9 * 0.8 * deltas[2],
        deltas[2],
    ])
    np.testing.assert_allclose(advantages, expected_adv)
    np.testing.assert_allclose(returns, expected_adv + values)


def test_masked_distribution_has_zero_probability_for_invalid_actions() -> None:
    torch = pytest.importorskip("torch")
    logits = torch.tensor([[2.0, 1.0, 5.0]])
    mask = torch.tensor([[True, False, True]])
    distribution = masked_categorical(logits, mask)
    assert float(distribution.probs[0, 1]) == pytest.approx(0.0)
    assert torch.isneginf(distribution.log_prob(torch.tensor([1]))).item()
    assert torch.isfinite(distribution.log_prob(torch.tensor([0]))).item()


def test_masked_distribution_replay_uses_saved_mask() -> None:
    torch = pytest.importorskip("torch")
    logits = torch.tensor([[0.0, 0.0]])
    action = torch.tensor([1])
    old_mask = torch.tensor([[True, True]])
    new_mask = torch.tensor([[True, False]])
    old_log_prob = masked_categorical(logits, old_mask).log_prob(action)
    new_log_prob = masked_categorical(logits, new_mask).log_prob(action)
    assert torch.isfinite(old_log_prob).item()
    assert torch.isneginf(new_log_prob).item()
