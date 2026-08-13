from __future__ import annotations

import pytest


def test_uav_and_vehicle_actor_gradients_are_role_isolated() -> None:
    torch = pytest.importorskip("torch")
    from problem2.algorithms.sr_mappo.actors import RoleActor

    uav = RoleActor(input_dim=4, action_dim=3, hidden_dim=8)
    vehicle = RoleActor(input_dim=5, action_dim=2, hidden_dim=8)
    loss = uav(torch.ones(2, 4)).sum()
    loss.backward()
    assert any(parameter.grad is not None for parameter in uav.parameters())
    assert all(parameter.grad is None for parameter in vehicle.parameters())

