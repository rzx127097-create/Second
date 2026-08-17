from __future__ import annotations

import numpy as np
import pytest

from problem2.domain.resources import PesticideResources
from problem2.domain.state import UAVState, VehicleState
from problem2.domain.requests import RequestManager, RequestStatus
from problem2.environment.air_ground_env import AirGroundEnv, EnvironmentConfig
from problem2.environment.service_state_machine import ServicePhase, ServiceStateMachine


def make_env() -> AirGroundEnv:
    resources = PesticideResources(
        uavs={
            "uav-1": UAVState(
                uav_id="uav-1", onboard_l=0.20, capacity_l=0.30, spray_flow_l_s=0.10
            )
        },
        vehicles={
            "vehicle-1": VehicleState(
                vehicle_id="vehicle-1",
                inventory_l=0.50,
                capacity_l=0.50,
                transfer_rate_l_s=0.20,
                service_cap_l=0.30,
            )
        },
    )
    return AirGroundEnv(
        pest_density=np.ones((2, 3), dtype=float),
        resources=resources,
        config=EnvironmentConfig(
            decision_dt_s=1.0,
            max_steps=20,
            success_reduction_threshold=0.90,
            request_threshold_ratio=0.50,
            service_setup_s=1.0,
            grid_shape=(2, 3),
        ),
    )


def test_step_applies_uav_spray_and_returns_event_complete_transition() -> None:
    env = make_env()
    observation = env.reset(seed=7)
    assert observation["uav-1"]["position"] == (0, 0)

    next_obs, reward, terminated, truncated, info = env.step(
        {"uav-1": "spray", "vehicle-1": "hold"}
    )

    assert next_obs["uav-1"]["onboard_l"] == pytest.approx(0.10)
    assert reward < 0.0  # pesticide-use cost dominates this one-step demo
    assert not terminated
    assert not truncated
    assert info["step"] == 1
    assert [event["event_type"] for event in info["events"]] == [
        "spray",
        "request_created",
        "field_update",
    ]


def test_request_is_reserved_then_prepared_and_transferred_without_negative_inventory() -> None:
    env = make_env()
    env.reset(seed=1)
    env.step({"uav-1": "spray", "vehicle-1": "hold"})

    _, _, _, _, info = env.step(
        {"uav-1": "hold", "vehicle-1": "next_request_slot"}
    )
    assert info["service_phase"] == "preparing"
    assert env.resources.vehicle("vehicle-1").inventory_l == pytest.approx(0.50)

    _, _, _, _, info = env.step(
        {"uav-1": "spray", "vehicle-1": "hold"}
    )
    assert info["service_phase"] == "transferring"
    assert env.resources.vehicle("vehicle-1").inventory_l == pytest.approx(0.50)

    _, _, _, _, info = env.step(
        {"uav-1": "spray", "vehicle-1": "hold"}
    )
    assert info["service_transfer_l"] == pytest.approx(0.20)
    assert env.resources.vehicle("vehicle-1").inventory_l == pytest.approx(0.30)
    assert env.resources.uav("uav-1").onboard_l >= 0.0
    env.resources.assert_conservation()


def test_locked_uav_cannot_move_or_spray_and_max_horizon_truncates() -> None:
    env = make_env()
    env.config = EnvironmentConfig(
        decision_dt_s=1.0,
        max_steps=3,
        success_reduction_threshold=2.0,
        request_threshold_ratio=0.50,
        service_setup_s=1.0,
        grid_shape=(2, 3),
    )
    env.reset(seed=1)
    env.step({"uav-1": "spray", "vehicle-1": "hold"})
    env.step({"uav-1": "hold", "vehicle-1": "next_request_slot"})
    position_before = env.uav_positions["uav-1"]
    _, _, _, truncated, info = env.step(
        {"uav-1": "right", "vehicle-1": "hold"}
    )
    assert env.uav_positions["uav-1"] == position_before
    assert truncated
    assert info["termination_reason"] == "max_steps"


def test_partial_service_reopens_request_and_releases_service_lock() -> None:
    resources = PesticideResources(
        uavs={
            "uav-1": UAVState(
                uav_id="uav-1", onboard_l=0.10, capacity_l=0.50, spray_flow_l_s=0.01
            )
        },
        vehicles={
            "vehicle-1": VehicleState(
                vehicle_id="vehicle-1", inventory_l=0.50, capacity_l=0.50,
                transfer_rate_l_s=1.0, service_cap_l=0.15
            )
        },
    )
    manager = RequestManager()
    request = manager.create_request("uav-1", requested_l=0.40, step=0)
    service = ServiceStateMachine()
    assert service.reserve(manager, "vehicle-1", step=1, setup_s=0.0) is request
    service.tick(manager, resources, "vehicle-1", dt_s=1.0, step=2)
    transferred = service.tick(manager, resources, "vehicle-1", dt_s=1.0, step=3)

    assert transferred == pytest.approx(0.15)
    assert manager.get(request.request_id).status is RequestStatus.OPEN
    assert manager.get(request.request_id).remaining_l == pytest.approx(0.25)
    assert service.phase is ServicePhase.IDLE
    assert service.request_id is None
    assert service.locked_uav_id is None


def test_multistep_transfer_keeps_service_locked_until_frozen_batch_completes() -> None:
    resources = PesticideResources(
        uavs={"uav-1": UAVState("uav-1", 0.10, 1.00, 0.01)},
        vehicles={
            "vehicle-1": VehicleState(
                "vehicle-1", 1.00, 1.00, 0.20, 0.80,
            )
        },
    )
    manager = RequestManager()
    request = manager.create_request("uav-1", requested_l=0.80, step=0)
    service = ServiceStateMachine()
    service.reserve(manager, "vehicle-1", step=1, setup_s=0.0)

    assert service.tick(manager, resources, "vehicle-1", dt_s=1.0, step=2) == 0.0
    assert service.phase is ServicePhase.TRANSFERRING

    for step in range(3, 6):
        assert service.tick(
            manager, resources, "vehicle-1", dt_s=1.0, step=step,
        ) == pytest.approx(0.20)
        assert service.phase is ServicePhase.TRANSFERRING
        assert manager.get(request.request_id).status is RequestStatus.SERVING

    assert service.tick(
        manager, resources, "vehicle-1", dt_s=1.0, step=6,
    ) == pytest.approx(0.20)
    assert manager.get(request.request_id).status is RequestStatus.COMPLETED
    assert service.phase is ServicePhase.IDLE
    assert resources.uav("uav-1").onboard_l == pytest.approx(0.90)
    resources.assert_conservation()


def test_service_rejects_a_vehicle_that_did_not_reserve_the_request() -> None:
    resources = PesticideResources(
        uavs={"uav-1": UAVState("uav-1", 0.10, 0.50, 0.01)},
        vehicles={
            "vehicle-1": VehicleState("vehicle-1", 0.50, 0.50, 1.0, 0.50),
            "vehicle-2": VehicleState("vehicle-2", 0.50, 0.50, 1.0, 0.50),
        },
    )
    manager = RequestManager()
    request = manager.create_request("uav-1", requested_l=0.20, step=0)
    service = ServiceStateMachine()
    assert service.reserve(manager, "vehicle-1", step=1, setup_s=0.0) is request
    with pytest.raises(ValueError, match="reserved for vehicle-1"):
        service.tick(manager, resources, "vehicle-2", dt_s=1.0, step=2)
