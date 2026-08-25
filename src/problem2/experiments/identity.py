from __future__ import annotations

import hashlib


def _field(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    value = value.strip()
    if "|" in value:
        raise ValueError(f"{name} cannot contain '|'")
    return value


def canonical_training_identity(
    method: str,
    scale: str,
    training_seed: int,
    config_hash: str,
    git_commit: str,
) -> str:
    """Return the unchanged G1 canonical identity serialization."""
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
    if not isinstance(canonical_identity, str) or not canonical_identity.strip():
        raise ValueError("canonical_training_identity must be non-empty text")
    canonical_identity = canonical_identity.strip()
    return "|".join((family, condition_id, protocol_hash, canonical_identity))


def sha256_identity(identity: str) -> str:
    return hashlib.sha256(_field(identity, "identity").encode("utf-8")).hexdigest()


__all__ = ["canonical_training_identity", "experiment_identity", "sha256_identity"]
