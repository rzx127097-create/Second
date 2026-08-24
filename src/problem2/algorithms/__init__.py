"""Learning components for the Problem 2 SR-MAPPO implementation."""

from typing import Any

from .protocol import (
    ActionResult,
    HeterogeneousAlgorithm,
    OffPolicyEnvelope,
    OnPolicyEnvelope,
    RoleBatch,
)


def build_algorithm(
    method_id: str,
    contract: Any,
    device: str,
    *,
    candidate_id: str = "c01",
) -> HeterogeneousAlgorithm:
    """Build one frozen G5 method from the validated contract."""

    from problem2.algorithms.ippo.algorithm import IPPOAlgorithm
    from problem2.algorithms.ippo.trainer import IPPOTrainer
    from problem2.algorithms.iql.algorithm import IQLAlgorithm
    from problem2.algorithms.iql.trainer import IQLTrainer
    from problem2.algorithms.maddpg.algorithm import MADDPGAlgorithm
    from problem2.algorithms.maddpg.trainer import MADDPGTrainer
    from problem2.algorithms.mappo.algorithm import MAPPOAlgorithm
    from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm
    from problem2.algorithms.sr_mappo.trainer import SRMAPPOTrainer
    from problem2.config import load_g3_config

    on_policy_methods = ("sr_mappo_mobile", "mappo_mobile", "ippo_mobile")
    off_policy_methods = ("maddpg_mobile", "iql_mobile")
    if method_id not in (*on_policy_methods, *off_policy_methods):
        raise ValueError(f"unknown G5 learning method {method_id!r}")
    if method_id not in getattr(contract, "methods", ()):
        raise ValueError(f"method {method_id!r} is not registered by the G5 contract")
    root = getattr(contract, "source_root", None)
    if root is None:
        raise TypeError("contract must expose its validated source_root")
    g3 = load_g3_config(root / "configs/problem2/g3_heterogeneous_marl.yaml")
    candidates = getattr(contract, "tuning_candidates", {}).get(method_id)
    if not candidates:
        raise ValueError(f"method {method_id!r} has no frozen tuning candidates")
    candidate = next(
        (item for item in candidates if item.candidate_id == candidate_id), None
    )
    if candidate is None:
        raise ValueError(
            f"candidate {candidate_id!r} is not registered for {method_id!r}"
        )
    parameters = dict(candidate.parameters)
    if method_id == "maddpg_mobile":
        training_config = {
            "candidate_id": candidate.candidate_id,
            "candidate_config_hash": candidate.config_hash,
            **parameters,
        }
        algorithm = MADDPGAlgorithm(
            uav_obs_dim=g3.uav_obs_dim,
            vehicle_obs_dim=g3.vehicle_obs_dim,
            state_dim=g3.critic_state_dim,
            uav_action_dim=g3.uav_action_dim,
            vehicle_action_dim=g3.vehicle_action_dim,
            hidden_dim=int(parameters["hidden_width"]),
            device=device,
            training_config=training_config,
        )
        MADDPGTrainer(
            algorithm,
            actor_lr=float(parameters["actor_lr"]),
            critic_lr=float(parameters["critic_lr"]),
            discount=float(parameters["discount"]),
            tau=float(parameters["tau"]),
            batch_size=int(parameters["batch_size"]),
        )
        return algorithm
    if method_id == "iql_mobile":
        training_config = {
            "candidate_id": candidate.candidate_id,
            "candidate_config_hash": candidate.config_hash,
            **parameters,
        }
        algorithm = IQLAlgorithm(
            uav_obs_dim=g3.uav_obs_dim,
            vehicle_obs_dim=g3.vehicle_obs_dim,
            uav_action_dim=g3.uav_action_dim,
            vehicle_action_dim=g3.vehicle_action_dim,
            hidden_dim=int(parameters["hidden_width"]),
            device=device,
            training_config=training_config,
        )
        IQLTrainer(
            algorithm,
            learning_rate=float(parameters["learning_rate"]),
            discount=float(parameters["discount"]),
            target_update_interval=int(parameters["target_update_interval"]),
            batch_size=int(parameters["batch_size"]),
        )
        return algorithm
    training_config = {
        "candidate_id": candidate.candidate_id,
        "candidate_config_hash": candidate.config_hash,
        "learning_rate": float(parameters["learning_rate"]),
        "clip_radius": float(parameters["clip_radius"]),
        "entropy_coefficient": float(parameters["entropy_coefficient"]),
        "discount": float(parameters["discount"]),
        "gae_lambda": float(parameters["gae_lambda"]),
        "rollout_horizon": int(parameters["rollout_horizon"]),
        "ppo_epochs": int(parameters["ppo_epochs"]),
        "minibatch_size": int(parameters["minibatch_size"]),
        "total_updates": int(g3.total_updates),
    }
    stability = dict(contract.stability_components[method_id])
    common = {
        "uav_obs_dim": g3.uav_obs_dim,
        "vehicle_obs_dim": g3.vehicle_obs_dim,
        "uav_action_dim": g3.uav_action_dim,
        "vehicle_action_dim": g3.vehicle_action_dim,
        "hidden_dim": int(parameters["hidden_width"]),
        "device": device,
        "stability_components": stability,
        "training_config": training_config,
    }
    if method_id == "ippo_mobile":
        algorithm = IPPOAlgorithm(**common)
        IPPOTrainer(
            algorithm,
            learning_rate=training_config["learning_rate"],
            value_coef=g3.value_loss_coef,
            entropy_coef=training_config["entropy_coefficient"],
            max_grad_norm=g3.max_grad_norm,
            minibatch_size=training_config["minibatch_size"],
            clip_radius=training_config["clip_radius"],
        )
        return algorithm
    centralized = {**common, "state_dim": g3.critic_state_dim}
    algorithm = (
        SRMAPPOAlgorithm(method_id=method_id, **centralized)
        if method_id == "sr_mappo_mobile"
        else MAPPOAlgorithm(**centralized)
    )
    SRMAPPOTrainer(
        algorithm,
        learning_rate=training_config["learning_rate"],
        value_coef=g3.value_loss_coef,
        entropy_coef=training_config["entropy_coefficient"],
        max_grad_norm=g3.max_grad_norm,
        minibatch_size=training_config["minibatch_size"],
        clip_radius=training_config["clip_radius"],
    )
    return algorithm


__all__ = ["ActionResult", "HeterogeneousAlgorithm", "OffPolicyEnvelope", "OnPolicyEnvelope", "RoleBatch", "build_algorithm"]
