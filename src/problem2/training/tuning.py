"""Fail-closed validation access accounting for frozen G5 candidates."""

from __future__ import annotations

import hashlib
import json
import math
import os
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator, Mapping

import numpy as np

from problem2.experiments.artifacts import atomic_write_bytes
from problem2.experiments.ecology_policy import (
    DYNAMIC_OUTPUT_ROOT,
    STATIC_DIAGNOSTIC_OUTPUT_ROOT,
    resolve_output_root,
)
from problem2.experiments.g5_contract import load_g5_contract
from problem2.experiments.identity import canonical_evaluation_identity, canonical_training_identity
from problem2.config import load_g2_config
from problem2.domain import EpisodeState, UavState, VehicleState
from problem2.resources.ledger import new_ledger
from problem2.road.cache import RoadCacheExpectation, load_road_cache
from problem2.ecology.config import DynamicEcologyConfig
from problem2.ecology.scenario import generate_dynamic_scenario
from problem2.ecology.system import DynamicEcologySystem

from .cooperative_env import Problem2CooperativeEnv
from .dynamic_env import DynamicPestEnvironment
from problem2.heuristics import FixedSupportController, NearestRequestController, RollingAStarController, UrgencyController
from .conditions import resolve_condition_execution


INITIAL_ONBOARD_PESTICIDE_L = 0.2875
DEVELOPMENT_SCENARIO_IDS = range(10000, 10020)
VALIDATION_SCENARIO_IDS = range(20000, 20050)
SEALED_SCENARIO_IDS = range(30000, 30100)
CANONICAL_METHODS = (
    "sr_mappo_mobile", "mappo_mobile", "ippo_mobile", "maddpg_mobile", "iql_mobile"
)
CANONICAL_SEEDS = (51001, 51002, 51003)
CANONICAL_SCALE = "g30x50_d4"
CANONICAL_INTERACTIONS = 200000


class _Task12PhysicalEnv(Problem2CooperativeEnv):
    """Keep active dispatch mapping aligned with its one-hot behavior mask."""

    def _candidate_requests(self) -> tuple[list[Any], list[str | None]]:
        if self._dispatch is None:
            return super()._candidate_requests()
        dispatch = self._dispatch
        request = next(
            item for item in self._state.requests if item.request_id == dispatch.request_id
        )
        mapping: list[str | None] = [None, None, None, None]
        mapping[dispatch.sampled_slot - 1] = dispatch.request_id
        self._dispatch = replace(dispatch, candidate_mapping=tuple(mapping))
        self._candidate_nodes = {
            dispatch.request_id: (
                dispatch.selected_service_node,
                dispatch.route_length_m,
            )
        }
        return [request], mapping


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is unreadable") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain an object")
    return payload


def validate_validation_episode(row: Mapping[str, Any]) -> None:
    """Reject proxy outcomes and any validation/sealed boundary ambiguity."""

    if not isinstance(row, Mapping):
        raise ValueError("validation episode must be a mapping")
    if row.get("partition") != "validation" or row.get("validation_accessed") is not True:
        raise ValueError("validation episode must record validation access")
    scenario_id = row.get("scenario_id")
    if isinstance(scenario_id, bool) or not isinstance(scenario_id, int) or scenario_id not in range(20000, 20050):
        raise ValueError("validation scenario identity is outside 20000-20049")
    if row.get("sealed_accessed") is not False:
        raise ValueError("sealed access is forbidden during G5")
    if row.get("battery_replenishment_enabled") is not False:
        raise ValueError("battery replenishment must remain inactive")
    metric_source = row.get("metric_source")
    if metric_source not in {"action_driven_environment", "dynamic_ecology_environment"}:
        raise ValueError("validation metrics must come from an action-driven or dynamic ecology environment")
    spray_count = row.get("spray_action_count")
    sprayed_l = row.get("sprayed_pesticide_l")
    if isinstance(spray_count, bool) or not isinstance(spray_count, int) or spray_count < 0:
        raise ValueError("spray action count must be a non-negative integer")
    if isinstance(sprayed_l, bool) or not isinstance(sprayed_l, (int, float)) or not math.isfinite(float(sprayed_l)) or float(sprayed_l) < 0:
        raise ValueError("sprayed pesticide must be non-negative")
    initial = row.get("initial_total_pest")
    final = row.get("final_total_pest")
    reduction = row.get("reduction_rate")
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) for value in (initial, final, reduction)):
        raise ValueError("pest metrics must be finite numbers")
    if float(initial) <= 0 or float(final) < 0:
        raise ValueError("pest totals are physically invalid")
    expected = 1.0 - float(final) / float(initial)
    if metric_source == "action_driven_environment" and float(final) > float(initial):
        raise ValueError("pest totals are physically invalid")
    if metric_source == "action_driven_environment" and expected > 0 and (spray_count == 0 or float(sprayed_l) <= 0):
        raise ValueError("positive pest reduction requires at least one spray action")
    if not math.isclose(float(reduction), expected, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("reduction rate is not derived from pest totals")
    if row.get("success_at_0_85") is not (expected >= 0.85):
        raise ValueError("success indicator does not match the 0.85 threshold")


class ValidationAccessLedger:
    """Bind the first validation row to immutable candidate and budget bytes."""

    def __init__(self, candidate_manifest: Path | str, budget_manifest: Path | str, ledger_path: Path | str) -> None:
        self.candidate_manifest = Path(candidate_manifest).resolve()
        self.budget_manifest = Path(budget_manifest).resolve()
        self.ledger_path = Path(ledger_path).resolve()
        candidates = _load_json(self.candidate_manifest, "candidate manifest")
        budget = _load_json(self.budget_manifest, "budget manifest")
        declared = candidates.get("equal_environment_interactions")
        if isinstance(declared, bool) or not isinstance(declared, int) or declared <= 0:
            raise ValueError("candidate manifest lacks equal environment interactions")
        methods = candidates.get("candidates")
        if not isinstance(methods, dict) or not methods:
            raise ValueError("candidate manifest is incomplete")
        self._candidates: dict[tuple[str, str], str] = {}
        for method, rows in methods.items():
            if not isinstance(rows, list) or len(rows) != 4:
                raise ValueError("candidate manifest must contain four candidates per method")
            for row in rows:
                if not isinstance(row, dict) or row.get("environment_interactions") != declared:
                    raise ValueError("all candidates must have equal environment interactions")
                candidate_id = row.get("candidate_id")
                config_hash = row.get("config_hash")
                if not isinstance(candidate_id, str) or not isinstance(config_hash, str) or len(config_hash) != 64:
                    raise ValueError("candidate identity is incomplete")
                self._candidates[(str(method), candidate_id)] = config_hash
        if budget.get("decision", {}).get("selected_budget") != declared:
            raise ValueError("candidate and pilot budget manifests disagree")
        self.interactions = declared
        self.candidate_sha256 = _file_sha256(self.candidate_manifest)
        self.budget_sha256 = _file_sha256(self.budget_manifest)

    def append(self, row: Mapping[str, Any]) -> dict[str, Any]:
        if _file_sha256(self.candidate_manifest) != self.candidate_sha256:
            raise ValueError("candidate manifest changed after validation access")
        if _file_sha256(self.budget_manifest) != self.budget_sha256:
            raise ValueError("budget manifest changed after validation access")
        validate_validation_episode(row)
        identity = (row.get("method"), row.get("candidate_id"))
        if identity not in self._candidates or row.get("config_hash") != self._candidates[identity]:
            raise ValueError("validation row is not a frozen candidate")
        if row.get("interaction_count") != self.interactions:
            raise ValueError("validation row violates the equal environment interactions budget")
        previous = _load_json(self.ledger_path, "validation access ledger") if self.ledger_path.exists() else {
            "schema_version": "g5-validation-access-v1",
            "status": "validation_accessed_candidates_locked",
            "candidate_manifest_sha256": self.candidate_sha256,
            "budget_manifest_sha256": self.budget_sha256,
            "row_count": 0,
            "row_chain_sha256": "0" * 64,
            "sealed_accessed": False,
            "actual_unlock_count": 0,
        }
        if previous.get("candidate_manifest_sha256") != self.candidate_sha256 or previous.get("budget_manifest_sha256") != self.budget_sha256:
            raise ValueError("validation access ledger provenance drifted")
        row_raw = json.dumps(dict(row), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        chain = hashlib.sha256((str(previous["row_chain_sha256"])).encode("ascii") + row_raw).hexdigest()
        updated = {**previous, "row_count": int(previous["row_count"]) + 1, "row_chain_sha256": chain}
        atomic_write_bytes(self.ledger_path, (json.dumps(updated, sort_keys=True, indent=2) + "\n").encode("utf-8"))
        return updated

    def verify_rows(self, rows: list[Mapping[str, Any]]) -> None:
        """Verify a recovered JSONL prefix against the persisted hash chain."""

        if not self.ledger_path.is_file():
            if rows:
                raise ValueError("validation rows exist without an access ledger")
            return
        ledger = _load_json(self.ledger_path, "validation access ledger")
        expected_keys = {
            "schema_version", "status", "candidate_manifest_sha256",
            "budget_manifest_sha256", "row_count", "row_chain_sha256",
            "sealed_accessed", "actual_unlock_count",
        }
        if set(ledger) != expected_keys:
            raise ValueError("validation access ledger schema drifted")
        if ledger.get("schema_version") not in {"g5-validation-access-v1", "g5-validation-access-v2"}:
            raise ValueError("validation access ledger schema drifted")
        if ledger.get("status") != "validation_accessed_candidates_locked":
            raise ValueError("validation access ledger status is not locked")
        if ledger.get("sealed_accessed") is not False or ledger.get("actual_unlock_count") != 0:
            raise ValueError("validation access ledger contains sealed or unlock state")
        if ledger.get("candidate_manifest_sha256") != self.candidate_sha256 or ledger.get("budget_manifest_sha256") != self.budget_sha256:
            raise ValueError("validation access ledger provenance drifted")
        if isinstance(ledger.get("row_count"), bool) or not isinstance(ledger.get("row_count"), int) or ledger["row_count"] < 0:
            raise ValueError("validation access ledger row count is invalid")
        if not isinstance(ledger.get("row_chain_sha256"), str) or len(ledger["row_chain_sha256"]) != 64:
            raise ValueError("validation access ledger chain is invalid")
        chain = "0" * 64
        for row in rows:
            validate_validation_episode(row)
            raw = json.dumps(dict(row), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
            chain = hashlib.sha256(chain.encode("ascii") + raw).hexdigest()
        if ledger.get("row_count") != len(rows) or ledger.get("row_chain_sha256") != chain:
            raise ValueError("validation recovery row chain mismatch")


class ValidationAccessError(RuntimeError):
    """Raised when validation access cannot acquire its exclusive writer."""


class CanonicalValidationStore(ValidationAccessLedger):
    """Recoverable, single-writer storage for the canonical validation matrix.

    The legacy ``append`` method remains available for pre-existing compact
    tests. Canonical callers must use ``commit_row``, which accepts only the
    strict raw schema and commits a row file before rebuilding the ledger.
    """

    def __init__(
        self,
        repository_root: Path | str,
        budget_manifest: Path | str | None = None,
        ledger_path: Path | str | None = None,
        *,
        output_root: Path | str | None = None,
        candidate_manifest: Path | str | None = None,
        source_commit: str | None = None,
        protocol_hash: str | None = None,
        scenario_panel_hash: str | None = None,
        physical_scenario_contract_hash: str | None = None,
        allow_noncanonical_test: bool = False,
        require_dynamic_ecology: bool = False,
    ) -> None:
        root = Path(repository_root).resolve()
        if candidate_manifest is None and budget_manifest is not None and ledger_path is not None:
            candidate_manifest = Path(repository_root)
            candidate_budget = Path(budget_manifest)
            target_ledger = Path(ledger_path)
            target_root = target_ledger.parent
        else:
            candidate_manifest = Path(candidate_manifest or root / DYNAMIC_OUTPUT_ROOT / "g5/manifests/validation-candidates.json")
            candidate_budget = Path(budget_manifest or root / DYNAMIC_OUTPUT_ROOT / "g5/manifests/pilot-budget.json")
            target_root = Path(output_root or root / DYNAMIC_OUTPUT_ROOT / "g5/validation")
        if allow_noncanonical_test:
            target_root = target_root.resolve()
        else:
            target_root = resolve_output_root(
                root,
                "G5",
                target_root,
                primary=True,
                partition="validation",
            )
        target_ledger = Path(ledger_path or target_root / "validation-access.json")
        canonical_root = (root / DYNAMIC_OUTPUT_ROOT / "g5/validation").resolve()
        if not allow_noncanonical_test and target_root != canonical_root:
            raise ValueError("canonical validation output must be the dynamic G5 validation root")
        super().__init__(candidate_manifest, candidate_budget, target_ledger)
        if self.candidate_sha256 != "67e6784b3d00d0385310d467c351f5b3374f02c7a7d7c22c571d4de29190419a":
            raise ValueError("candidate manifest bytes are not the frozen canonical manifest")
        if self.budget_sha256 != "048138954f336c95e3d339aed594c71e23167ef30cc1f4a373d5c2b10bb049cb":
            raise ValueError("budget manifest bytes are not the frozen canonical manifest")
        if self.interactions != CANONICAL_INTERACTIONS:
            raise ValueError("canonical validation budget must be exactly 200000")
        if set(method for method, _ in self._candidates) != set(CANONICAL_METHODS):
            raise ValueError("candidate manifest must declare exactly the five canonical methods")
        if len(self._candidates) != 20:
            raise ValueError("candidate manifest must declare exactly 20 candidates")
        self.repository_root = root
        self.output_root = target_root
        self.rows_root = target_root / "rows"
        self.consolidated_path = target_root / "validation-episodes.jsonl"
        self.lock_path = target_root / ".validation-writer.lock"
        self.failures_path = target_root / "technical-failures.jsonl"
        self.source_commit = source_commit
        self.protocol_hash = protocol_hash
        self.scenario_panel_hash = scenario_panel_hash
        self.physical_scenario_contract_hash = physical_scenario_contract_hash
        self.require_dynamic_ecology = True if not allow_noncanonical_test else require_dynamic_ecology
        self._lock_depth = 0
        self._lock_handle: int | None = None
        candidate_ids = tuple(sorted({candidate for _, candidate in self._candidates}))
        if candidate_ids != ("c01", "c02", "c03", "c04"):
            raise ValueError("candidate manifest must declare c01-c04 for every method")
        self.methods = CANONICAL_METHODS
        self.candidate_ids = candidate_ids
        self.expected_identity_keys = tuple(
            (method, candidate, seed, scenario)
            for method in self.methods
            for candidate in self.candidate_ids
            for seed in CANONICAL_SEEDS
            for scenario in VALIDATION_SCENARIO_IDS
        )
        self._expected_index = {key: index for index, key in enumerate(self.expected_identity_keys)}

    def candidate_hash(self, method: str, candidate_id: str) -> str:
        try:
            return self._candidates[(method, candidate_id)]
        except KeyError as exc:
            raise ValueError("identity is not a frozen candidate") from exc

    @contextmanager
    def exclusive_lock(self) -> Iterator[None]:
        """Hold an OS-level lock for the complete writer transaction."""

        if self._lock_depth:
            self._lock_depth += 1
            try:
                yield
            finally:
                self._lock_depth -= 1
            return
        self.output_root.mkdir(parents=True, exist_ok=True)
        try:
            self._lock_handle = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise ValidationAccessError("validation writer lock is held by another process") from exc
        try:
            os.write(self._lock_handle, json.dumps({"pid": os.getpid(), "created_at": datetime.now(timezone.utc).isoformat()}).encode("utf-8"))
            os.close(self._lock_handle)
            self._lock_handle = None
            self._lock_depth = 1
            yield
        finally:
            self._lock_depth = 0
            if self._lock_handle is not None:
                os.close(self._lock_handle)
                self._lock_handle = None
            self.lock_path.unlink(missing_ok=True)

    def _locked(self) -> bool:
        return self._lock_depth > 0

    @contextmanager
    def _ensure_lock(self) -> Iterator[None]:
        if self._locked():
            yield
        else:
            with self.exclusive_lock():
                yield

    def _key(self, row: Mapping[str, Any]) -> tuple[str, str, int, int]:
        key = (str(row.get("method")), str(row.get("candidate_id")), row.get("training_seed"), row.get("scenario_id"))
        if key not in self._expected_index:
            raise ValueError("validation row identity is outside the exact canonical matrix")
        return key  # type: ignore[return-value]

    def _row_path(self, key: tuple[str, str, int, int]) -> Path:
        return self.rows_root / f"{self._expected_index[key]:04d}.json"

    def _validate_canonical_row(self, row: Mapping[str, Any]) -> dict[str, Any]:
        from problem2.evaluation.validator import validate_long_table

        payload = dict(row)
        key = self._key(payload)
        if payload.get("config_hash") != self.candidate_hash(key[0], key[1]):
            raise ValueError("validation row is not bound to the frozen candidate hash")
        if payload.get("scale") != CANONICAL_SCALE or payload.get("interaction_count") != CANONICAL_INTERACTIONS:
            raise ValueError("validation row violates the canonical scale or budget")
        if payload.get("partition") != "validation":
            raise ValueError("validation row must use the validation partition")
        for field, frozen in (
            ("source_commit", self.source_commit),
            ("protocol_hash", self.protocol_hash),
            ("scenario_panel_hash", self.scenario_panel_hash),
            ("candidate_manifest_sha256", self.candidate_sha256),
            ("budget_manifest_sha256", self.budget_sha256),
            ("physical_scenario_contract_sha256", self.physical_scenario_contract_hash),
        ):
            if frozen is not None and payload.get(field) != frozen:
                raise ValueError(f"validation row provenance drifted: {field}")
        expected_provenance = {
            "source_commit": payload.get("source_commit"),
            "config_hash": payload.get("config_hash"),
            "protocol_hash": payload.get("protocol_hash"),
            "checkpoint_hash": payload.get("checkpoint_hash"),
            "evaluator_hash": payload.get("evaluator_hash"),
            "scenario_panel_hash": payload.get("scenario_panel_hash"),
            "candidate_manifest_sha256": payload.get("candidate_manifest_sha256"),
            "budget_manifest_sha256": payload.get("budget_manifest_sha256"),
            "physical_scenario_contract_sha256": payload.get("physical_scenario_contract_sha256"),
        }
        validate_long_table(
            [payload], expected_identities={payload.get("evaluation_identity")},
            expected_provenance=expected_provenance, allow_validation_access=True,
        )
        if self.require_dynamic_ecology:
            from problem2.evaluation.validator import validate_dynamic_episode

            if payload.get("metric_source") != "dynamic_ecology_environment":
                raise ValueError("dynamic ecology rows require dynamic ecology provenance")
            validate_dynamic_episode(payload)
        return payload

    def _read_rows(self) -> list[dict[str, Any]]:
        if not self.rows_root.exists():
            return []
        rows: list[dict[str, Any]] = []
        for path in sorted(self.rows_root.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ValueError(f"validation row file is torn: {path.name}") from exc
            if not isinstance(payload, dict):
                raise ValueError("validation row file must contain an object")
            rows.append(payload)
        return rows

    def _rebuild_ledger_locked(self, rows: list[Mapping[str, Any]]) -> dict[str, Any]:
        for row in rows:
            self._validate_canonical_row(row)
        keys = [self._key(row) for row in rows]
        if keys != list(self.expected_identity_keys[: len(keys)]):
            raise ValueError("validation recovery rows are not an exact execution prefix")
        chain = "0" * 64
        for row in rows:
            raw = json.dumps(dict(row), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
            chain = hashlib.sha256(chain.encode("ascii") + raw).hexdigest()
        updated = {
            "schema_version": "g5-validation-access-v2",
            "status": "validation_accessed_candidates_locked",
            "candidate_manifest_sha256": self.candidate_sha256,
            "budget_manifest_sha256": self.budget_sha256,
            "row_count": len(rows),
            "row_chain_sha256": chain,
            "sealed_accessed": False,
            "actual_unlock_count": 0,
        }
        atomic_write_bytes(self.ledger_path, (json.dumps(updated, sort_keys=True, indent=2) + "\n").encode("utf-8"))
        return updated

    @staticmethod
    def _row_chain(rows: list[Mapping[str, Any]]) -> str:
        chain = "0" * 64
        for row in rows:
            raw = json.dumps(dict(row), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
            chain = hashlib.sha256(chain.encode("ascii") + raw).hexdigest()
        return chain

    def _assert_ledger_not_ahead(self, rows: list[Mapping[str, Any]]) -> None:
        if not self.ledger_path.is_file():
            return
        ledger = _load_json(self.ledger_path, "validation access ledger")
        expected_keys = {
            "schema_version", "status", "candidate_manifest_sha256",
            "budget_manifest_sha256", "row_count", "row_chain_sha256",
            "sealed_accessed", "actual_unlock_count",
        }
        if set(ledger) != expected_keys:
            raise ValueError("validation access ledger schema drifted")
        if ledger["schema_version"] != "g5-validation-access-v2":
            raise ValueError("validation access ledger schema drifted")
        if ledger["status"] != "validation_accessed_candidates_locked":
            raise ValueError("validation access ledger status is not locked")
        if ledger["sealed_accessed"] is not False or ledger["actual_unlock_count"] != 0:
            raise ValueError("validation access ledger contains sealed or unlock state")
        if (
            isinstance(ledger["row_count"], bool)
            or not isinstance(ledger["row_count"], int)
            or ledger["row_count"] < 0
            or not isinstance(ledger["row_chain_sha256"], str)
            or len(ledger["row_chain_sha256"]) != 64
        ):
            raise ValueError("validation access ledger counters or chain are invalid")
        if ledger["row_count"] > len(rows):
            raise ValueError("validation ledger is ahead of committed row files")
        expected_prefix_chain = self._row_chain(rows[: ledger["row_count"]])
        if ledger["row_chain_sha256"] != expected_prefix_chain:
            raise ValueError("validation ledger row chain mismatch")

    def commit_row(self, row: Mapping[str, Any]) -> dict[str, Any]:
        checked = self._validate_canonical_row(row)
        key = self._key(checked)
        with self._ensure_lock():
            existing = self._read_rows()
            self._assert_ledger_not_ahead(existing)
            path = self._row_path(key)
            if path.exists():
                prior = json.loads(path.read_text(encoding="utf-8"))
                if prior != checked:
                    raise ValueError("duplicate validation identity has different row content")
                return self._rebuild_ledger_locked(existing)
            if self._expected_index[key] != len(existing):
                raise ValueError("validation row is out of order or has a missing predecessor")
            self.rows_root.mkdir(parents=True, exist_ok=True)
            atomic_write_bytes(path, (json.dumps(checked, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8"))
            committed = self._read_rows()
            return self._rebuild_ledger_locked(committed)

    def consolidate(self) -> list[dict[str, Any]]:
        with self._ensure_lock():
            rows = self._read_rows()
            self._assert_ledger_not_ahead(rows)
            self._rebuild_ledger_locked(rows)
            raw = b"".join(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n" for row in rows)
            atomic_write_bytes(self.consolidated_path, raw)
            return rows

    def recover(self) -> list[dict[str, Any]]:
        with self._ensure_lock():
            rows = self._read_rows()
            self._assert_ledger_not_ahead(rows)
            self._rebuild_ledger_locked(rows)
            return rows

    def record_technical_failure(self, key: tuple[str, str, int, int], error: BaseException) -> dict[str, Any]:
        if key not in self._expected_index:
            raise ValueError("technical failure identity is outside the canonical matrix")
        with self._ensure_lock():
            prior = self.failure_records()
            same = [item for item in prior if tuple(item.get("identity", ())) == key]
            record = {
                "attempt": len(same) + 1,
                "identity": list(key),
                "exception_type": type(error).__name__,
                "exception_message": str(error),
                "source_commit": self.source_commit,
                "candidate_manifest_sha256": self.candidate_sha256,
                "budget_manifest_sha256": self.budget_sha256,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            existing = self.failures_path.read_bytes() if self.failures_path.exists() else b""
            atomic_write_bytes(self.failures_path, existing + json.dumps(record, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")
            return record

    def failure_records(self) -> list[dict[str, Any]]:
        if not self.failures_path.is_file():
            return []
        return [json.loads(line) for line in self.failures_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    @staticmethod
    def assert_candidate_generation_allowed(repository_root: Path | str) -> None:
        root = Path(repository_root).resolve()
        validation = root / DYNAMIC_OUTPUT_ROOT / "g5/validation"
        validation_roots = [validation]
        # A temporary legacy repository used by regression tests may contain
        # only the pre-dynamic ledger; preserve its one-way guard without
        # allowing real historical evidence to block a new dynamic freeze.
        historical_validation = root / "outputs/problem2_sr_mappo_v1/g5/validation"
        if not validation.exists() and historical_validation.exists():
            validation_roots.append(historical_validation)
        for validation_root in validation_roots:
            rows = validation_root / "rows"
            if rows.is_dir() and any(rows.glob("*.json")):
                raise ValueError("candidate generation is forbidden after first validation row")
            ledger = validation_root / "validation-access.json"
            if ledger.is_file():
                payload = _load_json(ledger, "validation access ledger")
                if int(payload.get("row_count", 0)) > 0:
                    raise ValueError("candidate generation is forbidden after validation access")


def map_validation_episode_to_raw(
    row: Mapping[str, Any], *, source_commit: str, protocol_hash: str,
    checkpoint_hash: str, evaluator_hash: str, scenario_panel_hash: str,
    raw_trace_locator: str, candidate_manifest_sha256: str,
    budget_manifest_sha256: str, physical_scenario_contract_sha256: str,
) -> dict[str, Any]:
    """Map an action-driven episode to the strict canonical raw-row schema."""

    source = dict(row)
    method = str(source["method"])
    scale = str(source.get("scale", CANONICAL_SCALE))
    seed = int(source["training_seed"])
    scenario_id = int(source["scenario_id"])
    config_hash = str(source["config_hash"])
    training_identity = str(source.get("canonical_training_identity") or canonical_training_identity(method, scale, seed, config_hash, source_commit))
    initial = float(source["initial_total_pest"])
    final = float(source["final_total_pest"])
    epsilon = 1.0e-12 if source.get("metric_source") == "action_driven_environment" else 0.0
    reduction = 1.0 - final / (initial + epsilon)
    metrics = source.get("mechanism_metrics") if isinstance(source.get("mechanism_metrics"), Mapping) else {}
    residual = float(source.get("resource_conservation_residual_l", metrics.get("resource_residual_l", 0.0)))
    raw = {
        "evaluation_identity": canonical_evaluation_identity(training_identity, str(source.get("condition_id", method)), scale, seed, scenario_id, "validation", checkpoint_hash, evaluator_hash, scenario_panel_hash),
        "canonical_training_identity": training_identity,
        "method": method, "candidate_id": str(source["candidate_id"]), "condition_id": str(source.get("condition_id", method)), "scale": scale,
        "training_seed": seed, "scenario_id": scenario_id, "partition": "validation",
        "source_commit": source_commit, "config_hash": config_hash, "protocol_hash": protocol_hash,
        "checkpoint_hash": checkpoint_hash, "evaluator_hash": evaluator_hash, "scenario_panel_hash": scenario_panel_hash,
        "candidate_manifest_sha256": candidate_manifest_sha256, "budget_manifest_sha256": budget_manifest_sha256,
        "physical_scenario_contract_sha256": physical_scenario_contract_sha256,
        "episode_index": int(source.get("episode_index", 0)), "interaction_count": int(source.get("interaction_count", CANONICAL_INTERACTIONS)),
        "termination_reason": str(source.get("termination_reason", "horizon")), "terminated": True,
        "initial_total_pest": initial, "final_total_pest": final, "reduction_rate": reduction,
        "success_at_0_85": reduction >= 0.85,
        "pesticide_initial_l": float(source.get("pesticide_initial_l", 0.0)),
        "pesticide_remaining_l": float(source.get("pesticide_remaining_l", 0.0)),
        "pesticide_transferred_l": float(source.get("pesticide_transferred_l", source.get("sprayed_pesticide_l", 0.0))),
        "resource_conservation_residual_l": residual,
        "battery_replenishment_l": 0.0,
        "action_uav": int(source.get("action_uav", 0)), "action_vehicle_slot": int(source.get("action_vehicle_slot", 0)),
        "rendezvous_distance_m": float(source.get("rendezvous_distance_m", metrics.get("rendezvous_distance_m", 0.0))),
        "vehicle_service_travel_m": float(source.get("vehicle_service_travel_m", metrics.get("vehicle_service_travel_m", 0.0))),
        "waiting_steps": float(source.get("waiting_steps", metrics.get("waiting_steps", 0.0))),
        "completed_request_waiting_steps": float(source.get("completed_request_waiting_steps", metrics.get("completed_request_waiting_steps", 0.0))),
        "pesticide_disabled_steps": float(source.get("pesticide_disabled_steps", metrics.get("pesticide_disabled_steps", 0.0))),
        "return_steps": float(source.get("return_steps", metrics.get("return_steps", 0.0))),
        "effective_spray_steps": float(source.get("effective_spray_steps", metrics.get("effective_spray_steps", source.get("spray_action_count", 0.0)))),
        "decision_runtime_s": float(source.get("decision_runtime_s", metrics.get("decision_runtime_s", 0.0))),
        "source_locator": raw_trace_locator,
    }
    metric_source = source.get("metric_source")
    if metric_source is not None:
        raw["metric_source"] = str(metric_source)
    if metric_source == "dynamic_ecology_environment":
        dynamic_fields = (
            "ecology_version", "ecology_config_sha256", "ecology_scenario_sha256",
            "ecology_source_commit", "ecology_implementation_version",
            "initial_total_predator", "final_total_predator",
            "cumulative_deposited_effect", "terminal_mean_concentration",
            "terminal_max_concentration", "terminal_wind_direction", "terminal_wind_strength",
            "dynamic_step_count",
        )
        missing = [field for field in dynamic_fields if field not in source]
        if missing:
            raise ValueError(f"dynamic ecology provenance is incomplete: {', '.join(missing)}")
        raw.update({field: source[field] for field in dynamic_fields})
        from problem2.evaluation.validator import validate_dynamic_episode

        validate_dynamic_episode(raw)
    return raw


class ActionDrivenValidationEnv:
    """Attach deterministic local pest mortality to accepted physical spray events."""

    ecology_mode = "static_diagnostic"
    primary_eligible = False

    def __init__(
        self,
        physical_environment: Any,
        *,
        initial_pest: np.ndarray,
        mortality_per_l: float,
        partition: str = "validation",
        source_provenance: Mapping[str, Any] | None = None,
        purpose: str | None = None,
        output_root: Path | str | None = None,
        repository_root: Path | str | None = None,
        allow_noncanonical_output_root: bool = False,
    ) -> None:
        physical_scenario_id = getattr(physical_environment, "scenario_id", None)
        _validate_partition_scenario(partition, physical_scenario_id)
        if partition != "development":
            raise ValueError("static diagnostic requires partition=development")
        if purpose != "static_ecology_diagnostic":
            raise ValueError("purpose must be static_ecology_diagnostic")
        if output_root is None:
            raise ValueError("static diagnostic output_root is required")
        if repository_root is None:
            raise ValueError("static diagnostic repository_root is required")
        if not allow_noncanonical_output_root:
            _validate_static_diagnostic_scope(repository_root, output_root)
        density = np.asarray(initial_pest, dtype=np.float64)
        if density.ndim != 2 or density.size == 0 or not np.isfinite(density).all() or np.any(density < 0):
            raise ValueError("initial pest field must be a finite non-negative matrix")
        if isinstance(mortality_per_l, bool) or not isinstance(mortality_per_l, (int, float)) or not math.isfinite(float(mortality_per_l)) or mortality_per_l <= 0:
            raise ValueError("mortality_per_l must be positive and finite")
        self.physical = physical_environment
        self.initial_pest = density.copy()
        self.mortality_per_l = float(mortality_per_l)
        self.pest = density.copy()
        self.spray_action_count = 0
        self.sprayed_pesticide_l = 0.0
        self.partition = partition
        self.source_provenance = dict(source_provenance or {})
        self.replenished_resource = "pesticide"
        self.battery_replenishment_enabled = False
        self._scenario_id = int(physical_scenario_id)

    @property
    def state(self) -> Any:
        return self.physical.state

    def _field_summary(self) -> tuple[float, ...]:
        return (
            float(np.mean(self.pest)),
            float(np.max(self.pest)),
            float(np.min(self.pest)),
            float(np.count_nonzero(self.pest < self.initial_pest) / self.pest.size),
        )

    def reset(self, *, scenario_id: int | None = None) -> dict[str, Any]:
        self._assert_live_scenario()
        requested_scenario_id = self._scenario_id if scenario_id is None else scenario_id
        _validate_partition_scenario(self.partition, requested_scenario_id)
        if requested_scenario_id != self._scenario_id:
            raise ValueError("wrapped physical scenario identity is immutable")
        self.pest = self.initial_pest.copy()
        self.spray_action_count = 0
        self.sprayed_pesticide_l = 0.0
        self.physical.initial_total_pest = float(np.sum(self.initial_pest))
        self.physical.final_total_pest = float(np.sum(self.pest))
        self.physical.field_summary = self._field_summary()
        return self.physical.reset(scenario_id=requested_scenario_id)

    def _assert_live_scenario(self) -> None:
        current_scenario_id = getattr(self.physical, "scenario_id", None)
        _validate_partition_scenario(self.partition, current_scenario_id)
        if int(current_scenario_id) != self._scenario_id:
            raise ValueError("wrapped physical scenario identity changed")

    def _cell_for_uav(self, uav_id: str) -> tuple[int, int]:
        uav = next(item for item in self.physical.state.uavs if item.uav_id == uav_id)
        x0, y0, x1, y1 = self.physical.graph.aoi_bounds_m
        x_fraction = 0.0 if x1 <= x0 else (uav.x_m - x0) / (x1 - x0)
        y_fraction = 0.0 if y1 <= y0 else (uav.y_m - y0) / (y1 - y0)
        col = min(self.pest.shape[1] - 1, max(0, int(round(x_fraction * (self.pest.shape[1] - 1)))))
        row = min(self.pest.shape[0] - 1, max(0, int(round(y_fraction * (self.pest.shape[0] - 1)))))
        return row, col

    def step(self, action_result: Any, **kwargs: Any) -> dict[str, Any]:
        self._assert_live_scenario()
        pest_before = float(np.sum(self.pest))
        physical_view = self.physical.step(action_result, **kwargs)
        for event in physical_view.get("events", ()):
            if getattr(event, "kind", None) != "spray":
                continue
            amount_l = float(dict(event.payload).get("delta_l", 0.0))
            if amount_l <= 0:
                continue
            row, col = self._cell_for_uav(str(event.entity_id))
            self.pest[row, col] = max(0.0, self.pest[row, col] - amount_l * self.mortality_per_l)
            self.spray_action_count += 1
            self.sprayed_pesticide_l += amount_l
        self.physical.final_total_pest = float(np.sum(self.pest))
        self.physical.field_summary = self._field_summary()
        # Problem2CooperativeEnv built its first next view before local pest
        # mortality was applied. Rebuild from the same completed physical state
        # so actors and the critic receive the action-complete ecological view.
        view = self.physical._make_view(events=tuple(physical_view.get("events", ())))
        if "sampled_actions" in physical_view:
            view["sampled_actions"] = physical_view["sampled_actions"]
        immediate_decrease = max(0.0, pest_before - self.physical.final_total_pest)
        initial_total = float(np.sum(self.initial_pest))
        view["pest_total_before"] = pest_before
        view["pest_total"] = self.physical.final_total_pest
        view["team_reward"] = immediate_decrease / initial_total
        view["metric_source"] = "action_driven_environment"
        return view

    def episode_record(self) -> Any:
        return self.physical.episode_record()


def _road_cache_expectation(metadata: Mapping[str, Any]) -> RoadCacheExpectation:
    return RoadCacheExpectation(
        scale_id=str(metadata["scale_id"]),
        source_sha256=str(metadata["source"]["sha256"]),
        source_crs=str(metadata["source"]["crs"]),
        target_crs=str(metadata["projection"]["target_crs"]),
        aoi_bounds_m=tuple(float(value) for value in metadata["projection"]["aoi_bounds_m"]),
        grid_shape=tuple(int(value) for value in metadata["grid"]["shape"]),
        preprocess_version=str(metadata["preprocess_version"]),
        generator_commit=str(metadata["generator"]["git_commit"]),
        generator_sha256=str(metadata["generator"]["sha256"]),
    )


def _validate_partition_scenario(partition: str, scenario_id: int) -> None:
    if partition not in {"development", "validation"}:
        raise ValueError("physical scenario partition must be exactly development or validation")
    if isinstance(scenario_id, bool) or not isinstance(scenario_id, int):
        raise ValueError(f"{partition} scenario identity must be an integer")
    if scenario_id in SEALED_SCENARIO_IDS:
        raise ValueError("sealed scenarios are forbidden everywhere in G5")
    allowed = DEVELOPMENT_SCENARIO_IDS if partition == "development" else VALIDATION_SCENARIO_IDS
    if scenario_id not in allowed:
        start, stop = allowed.start, allowed.stop - 1
        raise ValueError(f"only {partition} scenarios {start}-{stop} may be constructed in G5")


def _validate_static_diagnostic_scope(repository_root: Path | str, output_root: Path | str) -> None:
    supplied_root = Path(repository_root).resolve()
    canonical_root = Path(__file__).resolve().parents[3]
    if supplied_root != canonical_root:
        raise ValueError("static diagnostic repository_root is not the authoritative repository")
    output = Path(output_root).resolve()
    diagnostic_root = canonical_root / STATIC_DIAGNOSTIC_OUTPUT_ROOT
    if not output.is_relative_to(diagnostic_root):
        raise ValueError(
            "static diagnostic output is outside the diagnostics/static_ecology namespace"
        )


@lru_cache(maxsize=12)
def _load_static_environment_inputs(
    repository_root: str, scale: str
) -> tuple[Any, Any, Any, Path, dict[str, Any], Any, str, str]:
    """Load frozen contract, configuration, and road data once per process."""

    root = Path(repository_root).resolve()
    contract = load_g5_contract(root)
    config = load_g2_config(root / "configs" / "problem2" / "g2_deterministic.yaml")
    scale_config = next((item for item in config.scales if item.scale_id == scale), None)
    if scale_config is None:
        raise ValueError(f"unknown frozen scale {scale!r}")
    cache_root = root / "outputs" / "problem2_sr_mappo_v1" / "g2" / "roads" / scale
    metadata_path = cache_root / "metadata.json"
    graph_path = cache_root / "road_graph.npz"
    metadata = _load_json(metadata_path, "frozen G2 road metadata")
    graph = load_road_cache(
        graph_path,
        metadata_path,
        _road_cache_expectation(metadata),
    )
    return (
        contract,
        config,
        scale_config,
        cache_root,
        metadata,
        graph,
        _file_sha256(metadata_path),
        _file_sha256(graph_path),
    )


def _build_physical_environment(
    repository_root: Path | str,
    *,
    scenario_id: int,
    scale: str,
    partition: str,
    vehicle_controller: Any | None = None,
    condition_id: str | None = None,
) -> tuple[Problem2CooperativeEnv, np.ndarray, dict[str, Any]]:
    _validate_partition_scenario(partition, scenario_id)
    root = Path(repository_root).resolve()
    (
        contract,
        config,
        scale_config,
        cache_root,
        metadata,
        graph,
        metadata_sha256,
        graph_sha256,
    ) = _load_static_environment_inputs(str(root), scale)
    scenario_contract = contract.physical_scenario
    if INITIAL_ONBOARD_PESTICIDE_L > config.usable_capacity_l + config.tolerance:
        raise ValueError("frozen initial onboard pesticide exceeds usable UAV capacity")
    rng = np.random.default_rng(scenario_id)
    primary_nodes = np.flatnonzero(
        np.asarray([
            int(graph.component_id[int(row), int(col)]) == graph.primary_component_id
            for row, col in zip(graph.node_rows, graph.node_cols)
        ], dtype=bool)
    )
    if not primary_nodes.size:
        raise ValueError("frozen road graph has no primary component nodes")
    try:
        uav_count = int(scale.rsplit("_d", 1)[1])
    except (IndexError, ValueError) as exc:
        raise ValueError("scale does not encode its UAV count") from exc
    selected = rng.choice(primary_nodes, size=uav_count + 1, replace=primary_nodes.size < uav_count + 1)
    uavs = tuple(
        UavState(
            f"uav-{index}",
            float(graph.node_x_m[int(node)]),
            float(graph.node_y_m[int(node)]),
            pesticide_l=INITIAL_ONBOARD_PESTICIDE_L,
        )
        for index, node in enumerate(selected[:-1])
    )
    vehicle_node = int(selected[-1])
    vehicle = VehicleState(
        "vehicle-0",
        vehicle_node,
        float(graph.node_x_m[vehicle_node]),
        float(graph.node_y_m[vehicle_node]),
        inventory_l=config.vehicle_inventory_l,
    )
    if vehicle_controller is None and condition_id is not None:
        try:
            execution = resolve_condition_execution(condition_id)
        except ValueError:
            execution = None
        if execution is None:
            pass
        elif not execution.vehicle_trainable:
            controller_name = execution.vehicle_controller
            if controller_name == "fixed_support":
                support_node = int(primary_nodes[0])
                vehicle_controller = FixedSupportController(
                    support_node=support_node,
                    initial_inventory_l=config.vehicle_inventory_l,
                    service_cap_l=config.service_cap_l,
                    transfer_rate_lpm=config.transfer_rate_lpm,
                    setup_time_s=config.setup_time_s,
                    mobile_initial_inventory_l=config.vehicle_inventory_l,
                    mobile_service_cap_l=config.service_cap_l,
                    mobile_transfer_rate_lpm=config.transfer_rate_lpm,
                    mobile_setup_time_s=config.setup_time_s,
                )
            elif controller_name == "rolling_astar":
                vehicle_controller = RollingAStarController(replan_interval_steps=5)
            elif controller_name == "nearest_feasible":
                vehicle_controller = NearestRequestController()
            elif controller_name == "urgency_priority":
                vehicle_controller = UrgencyController()
    state = EpisodeState(0, uavs, vehicle, ledger=new_ledger(uavs, vehicle.inventory_l))
    raw_pest = rng.gamma(
        shape=scenario_contract.gamma_shape,
        scale=scenario_contract.gamma_scale,
        size=scale_config.grid_shape,
    )
    pest = raw_pest * (
        scenario_contract.normalized_initial_pest_total / float(np.sum(raw_pest))
    )
    physical = _Task12PhysicalEnv(
        state,
        graph,
        config,
        max_steps=scale_config.max_steps,
        scenario_id=scenario_id,
        vehicle_controller=vehicle_controller,
    )
    scenario_contract_path = root / "docs/evidence/g5/physical_scenario_contract.yaml"
    scenario_contract_sha256 = contract.file_hashes[
        "docs/evidence/g5/physical_scenario_contract.yaml"
    ]
    content_metadata = {
        "partition": partition,
        "scenario_id": scenario_id,
        "scale_id": scale,
        "physical_scenario_contract_sha256": scenario_contract_sha256,
        "initial_pest_shape": list(pest.shape),
    }
    content_hasher = hashlib.sha256()
    content_hasher.update(
        json.dumps(content_metadata, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    content_hasher.update(np.asarray(pest, dtype="<f8").tobytes(order="C"))
    source_provenance = {
        "environment_factory": f"problem2.training.tuning.build_{partition}_environment",
        "road_cache_scale": scale,
        "road_cache_metadata_sha256": metadata_sha256,
        "road_cache_graph_sha256": graph_sha256,
        "road_source_sha256": str(metadata["source"]["sha256"]),
        "physical_scenario_contract": str(scenario_contract_path),
        "physical_scenario_contract_sha256": scenario_contract_sha256,
        "physical_scenario_assumption_status": scenario_contract.assumption_status,
        "physical_scenario_empirical_claim": scenario_contract.empirical_claim,
        "physical_scenario_deployment_claim": scenario_contract.deployment_claim,
        "gamma_shape": scenario_contract.gamma_shape,
        "gamma_shape_unit": scenario_contract.gamma_shape_unit,
        "gamma_scale": scenario_contract.gamma_scale,
        "gamma_scale_unit": scenario_contract.gamma_scale_unit,
        "normalized_initial_pest_total": scenario_contract.normalized_initial_pest_total,
        "normalized_initial_pest_total_unit": scenario_contract.normalized_initial_pest_total_unit,
        "spray_mortality_per_l": scenario_contract.spray_mortality_per_l,
        "spray_mortality_unit": scenario_contract.spray_mortality_unit,
        "scenario_content_sha256": content_hasher.hexdigest(),
        "scenario_content_hash_encoding": scenario_contract.content_hash_encoding,
    }
    return physical, pest, source_provenance


def _build_static_environment(
    repository_root: Path | str,
    *,
    scenario_id: int,
    scale: str,
    partition: str,
    purpose: str = "static_ecology_diagnostic",
    output_root: Path | str | None = None,
) -> ActionDrivenValidationEnv:
    root = Path(repository_root).resolve()
    physical, pest, source_provenance = _build_physical_environment(
        root, scenario_id=scenario_id, scale=scale, partition=partition,
    )
    return ActionDrivenValidationEnv(
        physical,
        initial_pest=pest,
        mortality_per_l=source_provenance["spray_mortality_per_l"],
        partition=partition,
        source_provenance=source_provenance,
        purpose=purpose,
        output_root=output_root or (root / STATIC_DIAGNOSTIC_OUTPUT_ROOT),
        repository_root=root,
    )


def _build_dynamic_environment(
    repository_root: Path | str,
    *,
    scenario_id: int,
    scale: str,
    partition: str,
    vehicle_controller: Any | None = None,
    condition_id: str | None = None,
) -> DynamicPestEnvironment:
    _validate_partition_scenario(partition, scenario_id)
    root = Path(repository_root).resolve()
    physical, _, physical_provenance = _build_physical_environment(
        root, scenario_id=scenario_id, scale=scale, partition=partition,
        vehicle_controller=vehicle_controller, condition_id=condition_id,
    )
    _, _, scale_config, _, _, _, _, _ = _load_static_environment_inputs(str(root), scale)
    ecology_config = DynamicEcologyConfig.from_yaml(
        root / "configs" / "problem2" / "dynamic_pest_v1.yaml"
    )
    scenario = generate_dynamic_scenario(
        partition,
        scenario_id,
        scale,
        scale_config.grid_shape,
        ecology_config,
    )
    ecology = DynamicEcologySystem.from_scenario(
        scenario, ecology_config, physical.config.spray_per_step_l
    )
    provenance = {
        **physical_provenance,
        "environment_factory": f"problem2.training.tuning.build_{partition}_environment",
        "ecology_mode": "dynamic",
        "ecology_config_path": str(root / "configs" / "problem2" / "dynamic_pest_v1.yaml"),
        "ecology_config_sha256": ecology_config.contract_sha256,
        "ecology_scenario_sha256": scenario.scenario_sha256,
        "ecology_source_commit": scenario.source_commit,
        "ecology_version": ecology_config.version,
        "ecology_implementation_version": scenario.implementation_version,
        "dynamic_grid_shape": list(scenario.grid_shape),
        "scenario_content_sha256": scenario.scenario_sha256,
        "scenario_content_hash_encoding": "canonical_dynamic_ecology_state_v1",
    }
    return DynamicPestEnvironment(
        physical,
        ecology,
        partition=partition,
        source_provenance=provenance,
    )


def build_static_diagnostic_environment(
    repository_root: Path | str,
    *,
    scenario_id: int,
    scale: str = "g20x20_d2",
    partition: str,
    purpose: str,
    output_root: Path | str,
) -> ActionDrivenValidationEnv:
    """Build the legacy static adapter for explicitly scoped diagnostics only."""

    if partition != "development":
        raise ValueError("static diagnostic requires partition=development")
    if purpose != "static_ecology_diagnostic":
        raise ValueError("purpose must be static_ecology_diagnostic")
    root = Path(repository_root).resolve()
    output = Path(output_root).resolve()
    _validate_static_diagnostic_scope(root, output)
    environment = _build_static_environment(
        root, scenario_id=scenario_id, scale=scale, partition=partition,
        purpose=purpose, output_root=output,
    )
    environment.primary_eligible = False
    return environment


def build_development_environment(
    repository_root: Path | str,
    *,
    scenario_id: int,
    scale: str = "g20x20_d2",
    vehicle_controller: Any | None = None,
    condition_id: str | None = None,
) -> DynamicPestEnvironment:
    """Create one dynamic development scenario from the frozen G2 road cache."""

    return _build_dynamic_environment(
        repository_root,
        scenario_id=scenario_id,
        scale=scale,
        partition="development",
        vehicle_controller=vehicle_controller,
        condition_id=condition_id,
    )


def build_validation_environment(
    repository_root: Path | str,
    *,
    scenario_id: int,
    scale: str = "g30x50_d4",
) -> DynamicPestEnvironment:
    """Create one dynamic validation-only scenario from the frozen G2 road cache."""

    return _build_dynamic_environment(
        repository_root,
        scenario_id=scenario_id,
        scale=scale,
        partition="validation",
    )


__all__ = [
    "CANONICAL_METHODS",
    "CANONICAL_SEEDS",
    "CANONICAL_SCALE",
    "CANONICAL_INTERACTIONS",
    "CanonicalValidationStore",
    "ActionDrivenValidationEnv",
    "DynamicPestEnvironment",
    "DEVELOPMENT_SCENARIO_IDS",
    "INITIAL_ONBOARD_PESTICIDE_L",
    "SEALED_SCENARIO_IDS",
    "VALIDATION_SCENARIO_IDS",
    "ValidationAccessLedger",
    "ValidationAccessError",
    "build_development_environment",
    "build_static_diagnostic_environment",
    "build_validation_environment",
    "map_validation_episode_to_raw",
    "validate_validation_episode",
]
