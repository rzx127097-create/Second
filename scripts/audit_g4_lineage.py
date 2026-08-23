from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any


SOURCE_PROVENANCE_PATHS = (
    "configs/problem2/g2_deterministic.yaml",
    "docs/evidence/g4/g4_contract.yaml",
    "docs/evidence/g4/g4_probe_manifest.yaml",
    "scripts/audit_g4_mechanism.py",
    "scripts/run_g4_mechanism_probe.py",
    "src/problem2/experiments/g4_activation.py",
    "src/problem2/experiments/g4_audit.py",
    "src/problem2/experiments/g4_contract.py",
    "src/problem2/experiments/g4_counterfactual.py",
    "src/problem2/experiments/g4_support.py",
)
EXPECTED_ARTIFACT_PATHS = frozenset(
    {
        "activation-summary.json",
        "counterfactual-summary.json",
        "fixed/activation-summary.json",
        "fixed/provenance.json",
        "fixed/raw-probe.jsonl",
        "mobile/activation-summary.json",
        "mobile/provenance.json",
        "mobile/raw-probe.jsonl",
        "probe-matrix-summary.json",
        "provenance.json",
    }
)
AUDIT_REPORT_NAME = "g4-mechanism-audit.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_OBJECT_RE = re.compile(r"^[0-9a-f]{40,64}$")
GIT_COMMIT_REF_RE = re.compile(r"^[0-9a-f]{7,64}$")
GENERATOR_RE = re.compile(
    r"(?i)(?:generator(?:/code)? commit(?: bound in the canonical (?:g4 )?artifacts)?|"
    r"provenance binds source commit)\s*[:` ]+`?([0-9a-f]{7,64})"
)
TREE_RE = re.compile(
    r"(?i)(?:source|generator) tree(?: SHA-256)?\s*[:` ]+`?([0-9a-f]{40,64})"
)
BUNDLE_RE = re.compile(
    r"(?i)source bundle SHA-256\s*[:` ]+`?([0-9a-f]{64})"
)


class G4LineageError(ValueError):
    """Raised when G4 provenance cannot be resolved or verified."""


@dataclass(frozen=True)
class G4LineageReport:
    status: str
    generator_commits: tuple[str, ...]
    source_trees: tuple[str, ...]
    source_bundle_hashes: tuple[str, ...]
    contract_hashes: tuple[str, ...]
    artifact_manifest_sha256: str
    artifact_manifest_bytes: int
    artifact_hashes: dict[str, str]
    documentation_files: tuple[str, ...]
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["generator_commits"] = list(self.generator_commits)
        payload["source_trees"] = list(self.source_trees)
        payload["source_bundle_hashes"] = list(self.source_bundle_hashes)
        payload["contract_hashes"] = list(self.contract_hashes)
        payload["documentation_files"] = list(self.documentation_files)
        return payload


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _git(root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise G4LineageError("Git is unavailable while resolving G4 lineage") from exc
    if completed.returncode != 0 or not completed.stdout.strip():
        raise G4LineageError(f"{args[-1] if args else 'Git object'} is not a Git object")
    return completed.stdout.strip()


def _source_file_hashes(root: Path, commit: str) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative in SOURCE_PROVENANCE_PATHS:
        try:
            completed = subprocess.run(
                ["git", "show", f"{commit}:{relative}"],
                cwd=root,
                check=False,
                capture_output=True,
            )
        except OSError as exc:
            raise G4LineageError("Git is unavailable while reading G4 source bundle") from exc
        if completed.returncode != 0:
            raise G4LineageError(f"G4 source bundle file is not in Git object {commit}: {relative}")
        hashes[relative] = _sha256_bytes(completed.stdout)
    return hashes


def _source_bundle_hash(file_hashes: dict[str, str]) -> str:
    payload = {
        "schema_version": "g4-source-bundle.v1",
        "files": dict(sorted(file_hashes.items())),
    }
    return _sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())


def _walk_lineages(value: Any, location: str) -> list[tuple[str, dict[str, Any]]]:
    found: list[tuple[str, dict[str, Any]]] = []
    if isinstance(value, dict):
        if "source_tree_commit" in value and "source_tree_hash" in value:
            found.append((location, value))
        for key, nested in value.items():
            found.extend(_walk_lineages(nested, f"{location}.{key}"))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(_walk_lineages(nested, f"{location}[{index}]"))
    return found


def _load_lineages(output_root: Path) -> list[tuple[str, dict[str, Any]]]:
    lineages: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(output_root.rglob("*")):
        if not path.is_file() or path.name == "artifact-manifest.json":
            continue
        if path.suffix not in {".json", ".jsonl"}:
            continue
        try:
            if path.suffix == ".jsonl":
                payload: Any = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            else:
                payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise G4LineageError(f"cannot read canonical G4 artifact {path}") from exc
        lineages.extend(_walk_lineages(payload, path.relative_to(output_root).as_posix()))
    if not lineages:
        raise G4LineageError("canonical G4 artifacts contain no provenance lineage")
    return lineages


def _verify_artifacts(output_root: Path) -> tuple[dict[str, str], str, int]:
    manifest_path = output_root / "artifact-manifest.json"
    if not manifest_path.is_file():
        raise G4LineageError("canonical G4 artifact manifest is missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise G4LineageError("canonical G4 artifact manifest is unreadable") from exc
    entries = manifest.get("artifacts") if isinstance(manifest, dict) else None
    if not isinstance(entries, list):
        raise G4LineageError("canonical G4 artifact manifest has no artifacts list")
    observed: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise G4LineageError("canonical G4 artifact manifest entry is invalid")
        relative = Path(entry["path"])
        normalized = relative.as_posix()
        if relative.is_absolute() or ".." in relative.parts or normalized in observed:
            raise G4LineageError(f"canonical G4 artifact manifest path is invalid: {normalized}")
        path = (output_root / relative).resolve()
        try:
            path.relative_to(output_root.resolve())
        except ValueError as exc:
            raise G4LineageError(f"canonical G4 artifact escapes output root: {normalized}") from exc
        if not path.is_file():
            raise G4LineageError(f"canonical G4 artifact is missing: {normalized}")
        digest = _sha256(path)
        if digest != entry.get("sha256"):
            raise G4LineageError(f"canonical G4 artifact hash mismatch: {normalized}")
        if path.stat().st_size != entry.get("bytes"):
            raise G4LineageError(f"canonical G4 artifact byte mismatch: {normalized}")
        observed[normalized] = digest
    if set(observed) != EXPECTED_ARTIFACT_PATHS:
        raise G4LineageError("canonical G4 artifact manifest does not match the exact allowlist")
    current = {
        path.relative_to(output_root).as_posix()
        for path in output_root.rglob("*")
        if path.is_file() and path.name not in {"artifact-manifest.json", AUDIT_REPORT_NAME}
    }
    if current != EXPECTED_ARTIFACT_PATHS:
        raise G4LineageError("canonical G4 output contains an unregistered or missing artifact")
    manifest_bytes = manifest_path.stat().st_size
    return observed, _sha256(manifest_path), manifest_bytes


def _current_g4_document_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if path.name == "PROJECT_STATE.md":
        start = text.find("## G4 Resource-Scarcity Mechanism Acceptance Record")
        end = text.find("## Superseded Pre-Final-Review G4 Record", start)
        if start >= 0:
            text = text[start : end if end >= 0 else None]
    return text


def _document_references(root: Path) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    paths = (
        root / "HANDOFFG4.md",
        root / "docs/audits/g4-mechanism-compliance.md",
        root / "docs/PROJECT_STATE.md",
    )
    commits: list[str] = []
    trees: list[str] = []
    bundles: list[str] = []
    used: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        used.append(path.relative_to(root).as_posix())
        text = _current_g4_document_text(path)
        commits.extend(GENERATOR_RE.findall(text))
        trees.extend(TREE_RE.findall(text))
        bundles.extend(BUNDLE_RE.findall(text))
    if not used:
        raise G4LineageError("current G4 documentation is missing")
    return tuple(commits), tuple(trees), tuple(bundles), tuple(used)


def audit_g4_lineage(repository_root: Path, output_root: Path) -> G4LineageReport:
    root = Path(repository_root).resolve()
    artifacts_root = Path(output_root).resolve()
    docs_commits, docs_trees, docs_bundles, documentation_files = _document_references(root)
    candidates = tuple(dict.fromkeys(docs_commits))
    if not candidates:
        raise G4LineageError("current G4 documentation records no generator commit")
    resolved_doc_commits: list[str] = []
    for candidate in candidates:
        if not GIT_COMMIT_REF_RE.fullmatch(candidate):
            raise G4LineageError(f"{candidate} is not a Git object")
        resolved_doc_commits.append(_git(root, "rev-parse", "--verify", f"{candidate}^{{commit}}"))

    if not artifacts_root.is_dir():
        raise G4LineageError("canonical G4 output root is missing")
    artifact_hashes, manifest_hash, manifest_bytes = _verify_artifacts(artifacts_root)
    lineages = _load_lineages(artifacts_root)
    lineage_tuples = set()
    contract_hashes: set[str] = set()
    bundle_hashes: set[str] = set()
    source_trees: set[str] = set()
    generator_commits: set[str] = set()
    source_cache: dict[str, tuple[str, dict[str, str], str]] = {}
    contract_path = root / "docs/evidence/g4/g4_contract.yaml"
    for location, lineage in lineages:
        commit = lineage.get("source_tree_commit")
        tree = lineage.get("source_tree_hash")
        bundle = lineage.get("source_bundle_sha256")
        files = lineage.get("source_file_sha256")
        contract = lineage.get("g4_contract_sha256")
        if not isinstance(commit, str) or not GIT_OBJECT_RE.fullmatch(commit):
            raise G4LineageError(f"G4 provenance commit is invalid at {location}")
        if not isinstance(tree, str) or not GIT_OBJECT_RE.fullmatch(tree):
            raise G4LineageError(f"G4 provenance tree is invalid at {location}")
        cached = source_cache.get(commit)
        if cached is None:
            resolved_commit = _git(root, "rev-parse", "--verify", f"{commit}^{{commit}}")
            if resolved_commit != commit:
                raise G4LineageError(f"G4 provenance commit is not a Git object: {commit}")
            actual_tree = _git(root, "rev-parse", f"{commit}^{{tree}}")
            expected_files = _source_file_hashes(root, commit)
            source_cache[commit] = (actual_tree, expected_files, _source_bundle_hash(expected_files))
        actual_tree, expected_files, expected_bundle = source_cache[commit]
        if actual_tree != tree:
            raise G4LineageError(f"G4 provenance tree mismatch at {location}")
        if files != expected_files:
            raise G4LineageError(f"G4 provenance source-file hashes mismatch at {location}")
        if bundle != expected_bundle:
            raise G4LineageError(f"G4 provenance source-bundle hash mismatch at {location}")
        if contract != _sha256(contract_path):
            raise G4LineageError(f"G4 provenance contract hash mismatch at {location}")
        lineage_tuples.add((commit, tree, bundle, tuple(sorted(expected_files.items())), contract))
        generator_commits.add(commit)
        source_trees.add(tree)
        bundle_hashes.add(bundle)
        contract_hashes.add(contract)
    if len(lineage_tuples) != 1:
        raise G4LineageError("canonical G4 artifacts do not share one exact generator tuple")

    expected_commit = next(iter(generator_commits))
    expected_tree = next(iter(source_trees))
    expected_bundle = next(iter(bundle_hashes))
    errors: list[str] = []
    if set(resolved_doc_commits) != {expected_commit}:
        errors.append("current G4 documentation generator commit disagrees with canonical provenance")
    if set(docs_trees) != {expected_tree}:
        errors.append("current G4 documentation source tree disagrees with canonical provenance")
    if set(docs_bundles) != {expected_bundle}:
        errors.append("current G4 documentation source bundle disagrees with canonical provenance")
    status = "pass" if not errors else "fail"
    return G4LineageReport(
        status=status,
        generator_commits=tuple(sorted(generator_commits)),
        source_trees=tuple(sorted(source_trees)),
        source_bundle_hashes=tuple(sorted(bundle_hashes)),
        contract_hashes=tuple(sorted(contract_hashes)),
        artifact_manifest_sha256=manifest_hash,
        artifact_manifest_bytes=manifest_bytes,
        artifact_hashes=dict(sorted(artifact_hashes.items())),
        documentation_files=documentation_files,
        errors=tuple(errors),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the accepted G4 provenance lineage")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--output-root", default="outputs/problem2_sr_mappo_v1/g4")
    parser.add_argument("--report", default=None)
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()
    report = audit_g4_lineage(root, Path(args.output_root).resolve())
    if args.report:
        report_path = Path(args.report).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report.to_dict(), sort_keys=True))
    return 0 if report.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
