"""Strict, code-readable G5 evidence schemas."""

from __future__ import annotations


_COMMON = [
    "evaluation_identity", "canonical_training_identity", "method", "candidate_id", "condition_id", "scale", "training_seed", "scenario_id", "partition", "source_commit", "config_hash", "protocol_hash", "checkpoint_hash", "evaluator_hash", "scenario_panel_hash", "candidate_manifest_sha256", "budget_manifest_sha256", "physical_scenario_contract_sha256", "episode_index", "interaction_count", "termination_reason", "terminated", "initial_total_pest", "final_total_pest", "reduction_rate", "success_at_0_85", "pesticide_initial_l", "pesticide_remaining_l", "pesticide_transferred_l", "resource_conservation_residual_l", "battery_replenishment_l", "action_uav", "action_vehicle_slot", "rendezvous_distance_m", "vehicle_service_travel_m", "waiting_steps", "completed_request_waiting_steps", "pesticide_disabled_steps", "return_steps", "effective_spray_steps", "decision_runtime_s", "source_locator",
]

_DYNAMIC_ECOLOGY_FIELDS = [
    "metric_source", "ecology_version", "ecology_config_sha256",
    "ecology_scenario_sha256", "ecology_source_commit",
    "ecology_implementation_version", "initial_total_predator",
    "final_total_predator", "cumulative_deposited_effect",
    "terminal_mean_concentration", "terminal_max_concentration",
    "terminal_wind_direction", "terminal_wind_strength", "dynamic_step_count",
]

RAW_EPISODE_SCHEMA = {"$schema": "g5.v1", "type": "object", "additionalProperties": False, "required": _COMMON, "properties": {key: {"type": "number"} for key in _COMMON}}
RAW_EPISODE_SCHEMA["properties"].update({"evaluation_identity": {"type": "string"}, "canonical_training_identity": {"type": "string"}, "method": {"type": "string"}, "candidate_id": {"type": "string"}, "condition_id": {"type": "string"}, "scale": {"type": "string"}, "training_seed": {"type": "integer"}, "scenario_id": {"type": "integer"}, "partition": {"type": "string"}, "source_commit": {"type": "string"}, "config_hash": {"type": "string"}, "protocol_hash": {"type": "string"}, "checkpoint_hash": {"type": "string"}, "evaluator_hash": {"type": "string"}, "scenario_panel_hash": {"type": "string"}, "candidate_manifest_sha256": {"type": "string"}, "budget_manifest_sha256": {"type": "string"}, "physical_scenario_contract_sha256": {"type": "string"}, "episode_index": {"type": "integer"}, "interaction_count": {"type": "integer"}, "termination_reason": {"type": "string"}, "terminated": {"type": "boolean"}, "success_at_0_85": {"type": "boolean"}, "action_uav": {"type": "integer"}, "action_vehicle_slot": {"type": "integer"}, "source_locator": {"type": "string"}})
RAW_EPISODE_SCHEMA["properties"].update({
    "metric_source": {"type": "string"}, "ecology_version": {"type": "string"},
    "ecology_config_sha256": {"type": "string"}, "ecology_scenario_sha256": {"type": "string"},
    "ecology_source_commit": {"type": "string"}, "ecology_implementation_version": {"type": "string"},
    "initial_total_predator": {"type": "number"}, "final_total_predator": {"type": "number"},
    "cumulative_deposited_effect": {"type": "number"}, "terminal_mean_concentration": {"type": "number"},
    "terminal_max_concentration": {"type": "number"}, "terminal_wind_direction": {"type": "number"},
    "terminal_wind_strength": {"type": "number"}, "dynamic_step_count": {"type": "integer"},
})
DYNAMIC_RAW_EPISODE_SCHEMA = {
    "$schema": "g5.dynamic.v1", "type": "object", "additionalProperties": False,
    "required": _COMMON + _DYNAMIC_ECOLOGY_FIELDS,
    "properties": dict(RAW_EPISODE_SCHEMA["properties"]),
}
VALIDATED_LONG_TABLE_SCHEMA = {"type": "object", "additionalProperties": False, "required": _COMMON + ["validation_status", "source_row_reference"], "properties": {**RAW_EPISODE_SCHEMA["properties"], "validation_status": {"type": "string"}, "source_row_reference": {"type": "string"}}}
ARTIFACT_MANIFEST_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["artifact_id", "artifact_type", "source_paths", "source_hashes", "generator", "generator_commit", "generator_sha256", "generator_version", "output_path", "output_sha256", "created_at", "data_status"], "properties": {"artifact_id": {"type": "string"}, "artifact_type": {"type": "string"}, "source_paths": {"type": "array"}, "source_hashes": {"type": "array"}, "generator": {"type": "string"}, "generator_commit": {"type": ["string", "null"]}, "generator_sha256": {"type": ["string", "null"]}, "generator_version": {"type": ["string", "null"]}, "output_path": {"type": "string"}, "output_sha256": {"type": ["string", "null"]}, "created_at": {"type": ["string", "null"]}, "data_status": {"type": "string"}}}

__all__ = ["RAW_EPISODE_SCHEMA", "DYNAMIC_RAW_EPISODE_SCHEMA", "VALIDATED_LONG_TABLE_SCHEMA", "ARTIFACT_MANIFEST_SCHEMA"]
