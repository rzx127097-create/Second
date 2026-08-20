"""Read-only audit of candidate problem-2 assets stored in Git objects."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Sequence

import yaml


ROOT = Path(__file__).resolve().parents[1]
AUDITOR_VERSION = "g1-candidate-final-review-remediation.v1"
FORMAL_TRAINING_SEEDS = [42, 123, 2024, 3407, 7919]
ADMISSIBILITY_CLASSES = (
    "admissible_design_input",
    "requires_independent_reverification",
    "not_admissible_as_evidence",
    "protected_or_out_of_scope",
)
FORBIDDEN_PATTERNS = ("HAPPO", "happpo", "AG-SR-MAPPO")
MATURITY_PATTERNS = (
    r"\bM[234]\b",
    r"formal experiments show",
    r"significantly outperforms",
    r"\bproves?\b",
    r"real deployment verified",
    r"universally optimal",
)
CONTRACT_PATHS = {
    "parameter": "configs/parameter_registry.yaml",
    "seed": "configs/scenarios.yaml",
    "experiment": "configs/experiments/formal_matrix.yaml",
    "artifact": "src/problem2/artifacts/evidence_manifest.py",
    "sealed": "src/problem2/experiments/freeze.py",
}


def _decode(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")


def _run_git_bytes(
    args: Sequence[str],
    *,
    check: bool = True,
    command_records: list[dict[str, Any]] | None = None,
) -> bytes:
    argv = ["git", *args]
    completed = subprocess.run(
        argv,
        cwd=ROOT,
        check=False,
        text=False,
        capture_output=True,
    )
    if command_records is not None:
        command_records.append(
            {
                "argv": argv,
                "returncode": completed.returncode,
                "status": "ok" if completed.returncode == 0 else "no_match" if completed.returncode == 1 else "error",
                "stderr": _decode(completed.stderr).strip(),
            }
        )
    if check and completed.returncode != 0:
        raise RuntimeError(
            _decode(completed.stderr).strip()
            or f"git command failed ({completed.returncode}): {argv}"
        )
    return completed.stdout


def run_git(args: Sequence[str]) -> str:
    """Run a read-only Git command and return decoded standard output."""
    return _decode(_run_git_bytes(args))


def classify_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    lowered = normalized.lower()
    suffix = Path(normalized).suffix.lower()
    if lowered.startswith("artifacts/documents/") or lowered.startswith("docs/thesis/") or suffix in {".docx", ".doc"}:
        return "thesis/document"
    if lowered.startswith("src/") or (lowered.startswith("scripts/") and suffix == ".py"):
        return "source"
    if lowered.startswith("tests/"):
        return "test"
    if lowered.startswith("outputs/"):
        return "output"
    if lowered.startswith("artifacts/"):
        return "artifact"
    if lowered.startswith("docs/verification/") or re.search(r"(?:^|/)(?:audit|report)[^/]*\.(?:json|md)$", lowered):
        return "report"
    if lowered.startswith("configs/") or lowered in {"pyproject.toml", ".gitignore"}:
        return "configuration"
    return "documentation"


def _admissibility(path_class: str) -> str:
    if path_class == "documentation":
        return "admissible_design_input"
    if path_class in {"source", "configuration", "test", "artifact"}:
        return "requires_independent_reverification"
    if path_class in {"report", "output"}:
        return "not_admissible_as_evidence"
    return "protected_or_out_of_scope"


def _parse_changed_paths(output: str | bytes) -> list[dict[str, str]]:
    text = _decode(output) if isinstance(output, bytes) else output
    tokens = text.split("\0")
    if tokens and tokens[-1] == "":
        tokens.pop()
    paths: list[dict[str, str]] = []
    index = 0
    while index < len(tokens):
        status = tokens[index]
        index += 1
        if not status:
            continue
        if status[0] in {"R", "C"}:
            if index + 1 >= len(tokens):
                raise ValueError(f"truncated rename/copy record for status {status}")
            old_path, path = tokens[index], tokens[index + 1]
            index += 2
            path_class = classify_path(path)
            paths.append(
                {
                    "status": status,
                    "old_path": old_path,
                    "path": path,
                    "class": path_class,
                    "admissibility": _admissibility(path_class),
                }
            )
        else:
            if index >= len(tokens):
                raise ValueError(f"truncated path record for status {status}")
            path = tokens[index]
            index += 1
            path_class = classify_path(path)
            paths.append(
                {
                    "status": status,
                    "path": path,
                    "class": path_class,
                    "admissibility": _admissibility(path_class),
                }
            )
    return paths


def _parse_tree_paths(output: bytes) -> list[str]:
    return [_decode(value) for value in output.split(b"\0") if value]


def _git_grep(
    pattern: str,
    ref: str,
    command_records: list[dict[str, Any]],
) -> list[str]:
    output = _run_git_bytes(
        ["-c", "core.quotepath=false", "grep", "-n", "-I", "-E", pattern, ref, "--", "."],
        check=False,
        command_records=command_records,
    )
    return [line for line in _decode(output).splitlines() if line.strip()]


def _blob_id_and_content(
    candidate: str,
    path: str,
    command_records: list[dict[str, Any]],
) -> tuple[str, str]:
    tree = _run_git_bytes(
        ["-c", "core.quotepath=false", "ls-tree", "-z", candidate, "--", path],
        command_records=command_records,
    )
    record = tree.rstrip(b"\0")
    try:
        metadata, returned_path = record.split(b"\t", 1)
        _mode, object_type, blob_id = _decode(metadata).split(" ", 2)
    except ValueError as exc:
        raise RuntimeError(f"could not parse Git blob record for {path}") from exc
    if object_type != "blob" or _decode(returned_path) != path:
        raise RuntimeError(f"candidate contract is not the expected blob: {path}")
    content = _run_git_bytes(
        ["show", f"{candidate}:{path}"],
        command_records=command_records,
    )
    return blob_id, _decode(content)


def _missing_mapping_fields(
    value: object,
    required: set[str],
    prefix: str,
) -> list[str]:
    if not isinstance(value, dict):
        return [prefix]
    return [f"{prefix}.{field}" for field in sorted(required - set(value))]


def _inspect_parameter_contract(content: str) -> tuple[list[str], list[str]]:
    data = yaml.safe_load(content)
    missing = _missing_mapping_fields(data, {"status", "parameters"}, "root")
    conflicts: list[str] = []
    parameters = data.get("parameters") if isinstance(data, dict) else None
    required = {
        "symbol", "meaning", "value", "unit", "min", "max", "source_type",
        "source_id", "source_value", "source_unit", "conversion", "status", "scope",
    }
    if not isinstance(parameters, dict):
        missing.append("root.parameters.mapping")
    else:
        for parameter_id, record in parameters.items():
            missing.extend(
                _missing_mapping_fields(record, required, f"parameters.{parameter_id}")
            )
            if isinstance(record, dict) and record.get("status") != "verified":
                conflicts.append(f"{parameter_id} is not independently verified")
    return sorted(set(missing)), conflicts


def _inspect_seed_contract(content: str) -> tuple[list[str], list[str]]:
    data = yaml.safe_load(content)
    missing = _missing_mapping_fields(
        data, {"status", "source_kind", "source_metadata_hash", "scenarios"}, "root"
    )
    conflicts: list[str] = []
    scenarios = data.get("scenarios") if isinstance(data, dict) else None
    if not isinstance(scenarios, dict):
        missing.append("root.scenarios.mapping")
    else:
        for scenario_id, record in scenarios.items():
            missing.extend(
                _missing_mapping_fields(
                    record, {"split", "scale", "seed_offset"}, f"scenarios.{scenario_id}"
                )
            )
        sealed_offsets = sorted(
            int(record["seed_offset"])
            for record in scenarios.values()
            if isinstance(record, dict)
            and record.get("split") == "sealed_test"
            and isinstance(record.get("seed_offset"), int)
        )
        if sealed_offsets and not all(30000 <= value <= 30099 for value in sealed_offsets):
            conflicts.append(
                "candidate sealed-test seed offsets do not match the locked 30000-30099 range"
            )
    return sorted(set(missing)), conflicts


def _inspect_experiment_contract(content: str) -> tuple[list[str], list[str], list[int] | None]:
    data = yaml.safe_load(content)
    required = {
        "status", "splits", "methods", "training_seeds", "train_scenarios",
        "validation_scenarios", "sealed_test_scenarios", "scales",
    }
    missing = _missing_mapping_fields(data, required, "root")
    conflicts: list[str] = []
    training_seeds: list[int] | None = None
    if isinstance(data, dict):
        value = data.get("training_seeds")
        if isinstance(value, list) and all(isinstance(item, int) for item in value):
            training_seeds = value
            if value != FORMAL_TRAINING_SEEDS:
                conflicts.append(
                    f"candidate training seeds {value} conflict with frozen G1 seeds {FORMAL_TRAINING_SEEDS}"
                )
        if data.get("scales") != ["g20x20_d2", "g20x30_d3", "g20x40_d3", "g30x30_d3", "g30x40_d4", "g30x50_d4"]:
            conflicts.append("candidate scale IDs do not match the frozen six-scale G1 protocol")
    return missing, conflicts, training_seeds


def _inspect_python_contract(content: str, expected_tokens: Sequence[str]) -> list[str]:
    return [token for token in expected_tokens if token not in content]


def _inspect_contracts(
    candidate: str,
    command_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    inspected: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for kind, path in CONTRACT_PATHS.items():
        blob_id, content = _blob_id_and_content(candidate, path, command_records)
        conflicts: list[str] = []
        training_seeds: list[int] | None = None
        try:
            if kind == "parameter":
                missing, conflicts = _inspect_parameter_contract(content)
            elif kind == "seed":
                missing, conflicts = _inspect_seed_contract(content)
            elif kind == "experiment":
                missing, conflicts, training_seeds = _inspect_experiment_contract(content)
            elif kind == "artifact":
                missing = _inspect_python_contract(
                    content,
                    ("sha256", "script_version", "created_at", "output", "provisional"),
                )
                conflicts = [
                    "candidate artifact generator code is not an accepted G1 artifact schema"
                ]
            else:
                missing = _inspect_python_contract(
                    content,
                    ("create_validation_freeze", "create_sealed_unlock", "consumed", "sealed_test", "freeze_hash"),
                )
                conflicts = [
                    "candidate executable sealed-unlock implementation remains unavailable at M1/G1"
                ]
        except (TypeError, ValueError, yaml.YAMLError) as exc:
            missing = [f"parse_error:{type(exc).__name__}:{exc}"]
        inspected.append(
            {
                "kind": kind,
                "path": path,
                "blob_id": blob_id,
                "missing_fields": missing,
                "conflicts": conflicts,
                "complete": not missing,
                "admissibility": "requires_independent_reverification",
            }
        )
        for missing_field in missing:
            unresolved.append(
                {
                    "code": f"candidate_{kind}_contract_incomplete",
                    "path": path,
                    "detail": missing_field,
                    "resolution": "requires_independent_reverification",
                }
            )
        for conflict in conflicts:
            unresolved.append(
                {
                    "code": f"candidate_{kind}_contract_conflict",
                    "path": path,
                    "detail": conflict,
                    "resolution": "requires_independent_reverification",
                }
            )
        if kind == "experiment" and training_seeds != FORMAL_TRAINING_SEEDS:
            unresolved.append(
                {
                    "code": "candidate_training_seed_conflict",
                    "path": path,
                    "candidate_value": training_seeds,
                    "g1_value": FORMAL_TRAINING_SEEDS,
                    "resolution": "requires_independent_reverification",
                }
            )
    return inspected, unresolved


def _parse_grep_line(line: str) -> tuple[str, int | None, str]:
    match = re.match(r"^[^:]+:(.*?):(\d+):(.*)$", line)
    if match is None:
        return "", None, line
    return match.group(1), int(match.group(2)), match.group(3)


def _forbidden_classification(text: str) -> str:
    guardrail = re.compile(
        r"(?:do\s+not|must\s+not|forbidden|forbid|reject|not\s+introduce|"
        r"not\s+implement|not\s+use|no\s+happo|avoid)",
        re.IGNORECASE,
    )
    return "guardrail_mention" if guardrail.search(text) else "substantive_reference"


def _provenance(repository_commit: str, inspected: list[dict[str, Any]]) -> dict[str, Any]:
    auditor_path = Path(__file__).resolve()
    return {
        "auditor": {
            "path": auditor_path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(auditor_path.read_bytes()).hexdigest(),
            "version": AUDITOR_VERSION,
        },
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository_commit": repository_commit,
        "inspected_candidate_blobs": {
            item["path"]: item["blob_id"] for item in inspected
        },
    }


def audit_candidate_branch(base: str, candidate: str) -> dict[str, Any]:
    commands: list[dict[str, Any]] = []
    base_commit = _decode(
        _run_git_bytes(["rev-parse", base], command_records=commands)
    ).strip()
    candidate_commit = _decode(
        _run_git_bytes(["rev-parse", candidate], command_records=commands)
    ).strip()
    repository_commit = _decode(
        _run_git_bytes(["rev-parse", "HEAD"], command_records=commands)
    ).strip()
    changed = _parse_changed_paths(
        _run_git_bytes(
            [
                "-c", "core.quotepath=false", "diff", "--name-status", "-z",
                f"{base}...{candidate}",
            ],
            command_records=commands,
        )
    )
    tree_paths = _parse_tree_paths(
        _run_git_bytes(
            ["-c", "core.quotepath=false", "ls-tree", "-r", "-z", "--name-only", candidate],
            command_records=commands,
        )
    )
    maturity_matches = {
        pattern: _git_grep(pattern, candidate, commands)
        for pattern in MATURITY_PATTERNS
    }
    forbidden_matches = {
        pattern: _git_grep(re.escape(pattern), candidate, commands)
        for pattern in FORBIDDEN_PATTERNS
    }
    forbidden_findings: list[dict[str, Any]] = []
    for pattern, lines in forbidden_matches.items():
        for line in lines:
            path, line_number, text = _parse_grep_line(line)
            forbidden_findings.append(
                {
                    "name": pattern,
                    "path": path,
                    "line": line_number,
                    "text": text,
                    "classification": _forbidden_classification(text),
                }
            )
    inspected, unresolved = _inspect_contracts(candidate, commands)
    substantive_count = sum(
        item["classification"] == "substantive_reference"
        for item in forbidden_findings
    )
    if substantive_count:
        unresolved.append(
            {
                "code": "candidate_forbidden_name_substantive_references",
                "count": substantive_count,
                "resolution": "not_admissible_as_evidence",
            }
        )
    maturity_count = sum(len(matches) for matches in maturity_matches.values())
    if maturity_count:
        unresolved.append(
            {
                "code": "candidate_premature_maturity_claims",
                "count": maturity_count,
                "resolution": "not_admissible_as_evidence",
            }
        )
    class_counts = Counter(item["class"] for item in changed)
    admissibility_counts = Counter(item["admissibility"] for item in changed)
    candidate_dirs = sorted(
        {path.split("/", 1)[0] for path in tree_paths if "/" in path}
    )
    return {
        "status": "pass",
        "status_meaning": "audit_executed_successfully",
        "read_only": True,
        "base_ref": base,
        "candidate_ref": candidate,
        "base_commit": base_commit,
        "candidate_commit": candidate_commit,
        "changed_paths": changed,
        "changed_path_count": len(changed),
        "changed_paths_rendered": len(changed),
        "changed_paths_omitted": 0,
        "changed_class_counts": dict(sorted(class_counts.items())),
        "changed_admissibility_counts": dict(sorted(admissibility_counts.items())),
        "candidate_top_level_directories": candidate_dirs,
        "candidate_tree_path_count": len(tree_paths),
        "maturity_matches": maturity_matches,
        "forbidden_name_matches": forbidden_matches,
        "forbidden_name_findings": forbidden_findings,
        "inspected_contracts": inspected,
        "unresolved_findings": unresolved,
        "commands": commands,
        "current_branch_maturity": "M1",
        "current_gate": "G1",
        "sealed_test_accessed": False,
        "training_executed": False,
        "asset_classification_policy": {
            "admissible_design_input": "candidate documentation usable only as M1 design context",
            "requires_independent_reverification": "candidate source, tests, configs, and artifacts",
            "not_admissible_as_evidence": "candidate reports, outputs, maturity claims, and untraceable results",
            "protected_or_out_of_scope": "candidate thesis/document assets and protected external inputs",
        },
        "provenance": _provenance(repository_commit, inspected),
    }


def _markdown_report(report: dict[str, Any]) -> str:
    maturity_lines = [
        f"- `{pattern}`: {len(matches)} match(es)"
        for pattern, matches in report["maturity_matches"].items()
    ]
    forbidden_lines = [
        f"- `{pattern}`: {len(matches)} match(es)"
        for pattern, matches in report["forbidden_name_matches"].items()
    ]
    contract_lines = [
        (
            f"- `{item['kind']}` `{item['path']}` blob `{item['blob_id']}`: "
            f"complete=`{item['complete']}`, missing=`{json.dumps(item['missing_fields'], ensure_ascii=False)}`, "
            f"conflicts=`{json.dumps(item['conflicts'], ensure_ascii=False)}`"
        )
        for item in report["inspected_contracts"]
    ]
    unresolved_lines = [
        f"- `{item['code']}`: `{json.dumps(item, ensure_ascii=False, sort_keys=True)}`"
        for item in report["unresolved_findings"]
    ]
    classification_lines: list[str] = []
    for item in report["changed_paths"]:
        old = f" (from `{item['old_path']}`)" if "old_path" in item else ""
        classification_lines.append(
            f"- `{item['status']}` `{item['path']}`{old} -> `{item['class']}` / `{item['admissibility']}`"
        )
    command_lines = [
        f"- `{json.dumps(command['argv'], ensure_ascii=False)}` -> return `{command['returncode']}` (`{command['status']}`)"
        for command in report["commands"]
    ]
    seed_finding = next(
        (
            item for item in report["unresolved_findings"]
            if item["code"] == "candidate_training_seed_conflict"
        ),
        None,
    )
    seed_line = (
        f"Candidate training seeds `{seed_finding['candidate_value']}` conflict with frozen G1 seeds `{seed_finding['g1_value']}`."
        if seed_finding
        else "No candidate training-seed conflict was parsed."
    )
    provenance = report["provenance"]
    return "\n".join(
        [
            "# G1 Candidate Branch Audit",
            "",
            "> Read-only Git-object audit. `status=pass` means the audit executed successfully;",
            "> it does not accept candidate maturity claims or implementation evidence.",
            "",
            "## Identity And Provenance",
            "",
            f"- Base ref: `{report['base_ref']}`",
            f"- Base commit: `{report['base_commit']}`",
            f"- Candidate ref: `{report['candidate_ref']}`",
            f"- Candidate commit: `{report['candidate_commit']}`",
            f"- Generator commit: `{provenance['repository_commit']}`",
            f"- Auditor SHA-256: `{provenance['auditor']['sha256']}`",
            f"- Auditor version: `{provenance['auditor']['version']}`",
            f"- Generated UTC: `{provenance['generated_at_utc']}`",
            f"- Read-only: `{report['read_only']}`",
            f"- Current maturity: `{report['current_branch_maturity']}`",
            f"- Current gate: `{report['current_gate']}`",
            "",
            "## Inventory",
            "",
            f"- Changed paths: `{report['changed_path_count']}`",
            f"- Rendered changed paths: `{report['changed_paths_rendered']}`",
            f"- Omitted changed paths: `{report['changed_paths_omitted']}`",
            f"- Candidate tree paths: `{report['candidate_tree_path_count']}`",
            f"- Changed class counts: `{json.dumps(report['changed_class_counts'], sort_keys=True)}`",
            f"- Admissibility counts: `{json.dumps(report['changed_admissibility_counts'], sort_keys=True)}`",
            "",
            "## Contract Inspection",
            "",
            *contract_lines,
            "",
            seed_line,
            "",
            "## Maturity Scan",
            "",
            *maturity_lines,
            "",
            "## Forbidden-Name Scan",
            "",
            *forbidden_lines,
            "",
            "Guardrail mentions are recorded separately from substantive references; neither introduces a current implementation or public rename.",
            "",
            "## Unresolved Findings",
            "",
            *unresolved_lines,
            "",
            "## Changed-Path Classification",
            "",
            *classification_lines,
            "",
            "## Boundary",
            "",
            "- Training executed: `False`.",
            "- Sealed-test scenarios accessed: `False`.",
            "- OSM inputs remain simulation inputs, not field-deployment evidence.",
            "- Candidate M2/M3/M4 code and claims remain unaccepted.",
            "",
            "Candidate-branch assets are design or candidate implementation inputs only; no M2/M3/M4 claim is accepted in the current G1 branch without fresh, branch-local verification.",
            "",
            "## Commands",
            "",
            *command_lines,
            "",
        ]
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--json", dest="json_path", type=Path, required=True)
    args = parser.parse_args(argv)
    report = audit_candidate_branch(args.base, args.candidate)
    args.json_path.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.markdown.write_text(_markdown_report(report), encoding="utf-8")
    print(
        json.dumps(
            {
                key: report[key]
                for key in ("status", "base_commit", "candidate_commit", "changed_path_count")
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
