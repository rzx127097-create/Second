from __future__ import annotations

import hashlib
import re


def _field(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be non-empty text")
    if value != value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(f"{name} contains whitespace or control characters")
    if "|" in value:
        raise ValueError(f"{name} cannot contain '|'")
    return value


def canonical_training_serialization(
    method: str,
    scale: str,
    training_seed: int,
    config_hash: str,
    git_commit: str,
) -> str:
    """Return the exact G1 serialization before hashing."""
    if isinstance(training_seed, bool) or not isinstance(training_seed, int):
        raise ValueError("training_seed must be an integer")
    values = (
        _field(method, "method"),
        _field(scale, "scale"),
        str(training_seed),
        _field(config_hash, "config_hash"),
        _field(git_commit, "git_commit"),
    )
    return "|".join(values)


def canonical_training_identity(
    method: str,
    scale: str,
    training_seed: int,
    config_hash: str,
    git_commit: str,
) -> str:
    """Return the SHA-256 identity of the exact G1 serialization."""
    raw = canonical_training_serialization(method, scale, training_seed, config_hash, git_commit)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def experiment_identity(
    family: str,
    condition_id: str,
    protocol_hash: str,
    canonical_identity: str,
) -> str:
    """Bind a family reference while leaving the base identity untouched."""
    family = _field(family, "family")
    condition_id = _field(condition_id, "condition_id")
    protocol_hash = _field(protocol_hash, "protocol_hash")
    if not isinstance(canonical_identity, str) or not canonical_identity:
        raise ValueError("canonical_training_identity must be non-empty text")
    if not re.fullmatch(r"[0-9a-f]{64}", canonical_identity):
        raise ValueError("canonical_training_identity must be a lowercase SHA-256 digest")
    return "|".join((family, condition_id, protocol_hash, canonical_identity))


def sha256_identity(identity: str) -> str:
    return hashlib.sha256(_field(identity, "identity").encode("utf-8")).hexdigest()


__all__ = [
    "canonical_training_serialization", "canonical_training_identity",
    "experiment_identity", "sha256_identity",
]
