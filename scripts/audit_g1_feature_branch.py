from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PATTERNS = ("HAPPO", "happpo", "AG-SR-MAPPO")
MATURITY_PATTERNS = (
    r"\bM[234]\b",
    r"formal experiments show",
    r"significantly outperforms",
    r"\bproves?\b",
    r"real deployment verified",
    r"universally optimal",
)


def run_git(args: Sequence[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.stdout


def _git_grep(pattern: str, ref: str) -> list[str]:
    completed = subprocess.run(
        ["git", "grep", "-n", "-I", "-E", pattern, ref, "--", ":(exclude).git"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode not in (0, 1):
        raise RuntimeError(completed.stderr.strip() or f"git grep failed: {pattern}")
    return [line for line in (completed.stdout or "").splitlines() if line.strip()]


def classify_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.startswith("src/"):
        return "source"
    if normalized.startswith("configs/"):
        return "configuration"
    if normalized.startswith("tests/"):
        return "test"
    if normalized.startswith("docs/verification/"):
        return "report"
    if normalized.startswith("artifacts/"):
        return "artifact"
    if normalized.startswith("outputs/"):
        return "output"
    return "documentation"


def _parse_changed_paths(output: str) -> list[dict[str, str]]:
    paths: list[dict[str, str]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]
        paths.append({"status": status, "path": path, "class": classify_path(path)})
    return paths


def audit_candidate_branch(base: str, candidate: str) -> dict:
    base_commit = run_git(["rev-parse", base]).strip()
    candidate_commit = run_git(["rev-parse", candidate]).strip()
    changed = _parse_changed_paths(run_git(["diff", "--name-status", f"{base}...{candidate}"]))
    tree_paths = [
        path for path in run_git(["ls-tree", "-r", "--name-only", candidate]).splitlines() if path
    ]
    maturity_matches = {
        pattern: _git_grep(pattern, candidate)
        for pattern in MATURITY_PATTERNS
    }
    forbidden_matches = {
        pattern: _git_grep(re.escape(pattern), candidate)
        for pattern in FORBIDDEN_PATTERNS
    }
    class_counts = Counter(item["class"] for item in changed)
    candidate_dirs = sorted(
        {
            path.split("/", 1)[0]
            for path in tree_paths
            if "/" in path
        }
    )
    return {
        "status": "pass",
        "read_only": True,
        "base_ref": base,
        "candidate_ref": candidate,
        "base_commit": base_commit,
        "candidate_commit": candidate_commit,
        "changed_paths": changed,
        "changed_path_count": len(changed),
        "changed_class_counts": dict(sorted(class_counts.items())),
        "candidate_top_level_directories": candidate_dirs,
        "candidate_tree_path_count": len(tree_paths),
        "maturity_matches": maturity_matches,
        "forbidden_name_matches": forbidden_matches,
        "commands": [
            "git rev-parse <ref>",
            "git diff --name-status <base>...<candidate>",
            "git ls-tree -r --name-only <candidate>",
            "git grep -n -I -E <pattern> <candidate>",
        ],
        "current_branch_maturity": "M1",
        "current_gate": "G1",
        "sealed_test_accessed": False,
        "training_executed": False,
        "asset_classification_policy": {
            "admissible_design_input": "M1 specification or design assets only",
            "requires_independent_reverification": "candidate source, tests, configs, and reports",
            "not_admissible_as_evidence": "candidate maturity claims and untraceable outputs",
            "protected_or_out_of_scope": "external first-problem assets and source OSM inputs",
        },
    }


def _markdown_report(report: dict) -> str:
    counts = report["changed_class_counts"]
    maturity_lines = [
        f"- `{pattern}`: {len(matches)} match(es)"
        for pattern, matches in report["maturity_matches"].items()
    ]
    forbidden_lines = [
        f"- `{pattern}`: {len(matches)} match(es)"
        for pattern, matches in report["forbidden_name_matches"].items()
    ]
    classification_lines = [
        f"- `{item['status']}` `{item['path']}` -> `{item['class']}`"
        for item in report["changed_paths"][:200]
    ]
    return "\n".join(
        [
            "# G1 Candidate Branch Audit",
            "",
            "> Read-only Git-object audit. This report classifies candidate assets;",
            "> it does not accept candidate maturity claims as current evidence.",
            "",
            "## Identity",
            "",
            f"- Base ref: `{report['base_ref']}`",
            f"- Base commit: `{report['base_commit']}`",
            f"- Candidate ref: `{report['candidate_ref']}`",
            f"- Candidate commit: `{report['candidate_commit']}`",
            f"- Read-only: `{report['read_only']}`",
            f"- Current maturity: `{report['current_branch_maturity']}`",
            f"- Current gate: `{report['current_gate']}`",
            "",
            "## Inventory",
            "",
            f"- Changed paths: `{report['changed_path_count']}`",
            f"- Candidate tree paths: `{report['candidate_tree_path_count']}`",
            f"- Changed class counts: `{json.dumps(counts, sort_keys=True)}`",
            "",
            "## Maturity Scan",
            "",
            *maturity_lines,
            "",
            "## Forbidden-Name Scan",
            "",
            *forbidden_lines,
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
            "- Candidate source, configurations, tests, reports, and outputs require independent branch-local verification.",
            "",
            "Candidate-branch assets are design or candidate implementation inputs only; no M2/M3/M4 claim is accepted in the current G1 branch without fresh, branch-local verification.",
            "",
            "## Commands",
            "",
            *[f"- `{command}`" for command in report["commands"]],
            "",
        ]
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a candidate branch using read-only Git objects")
    parser.add_argument("--base", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--json", dest="json_path", type=Path, required=True)
    args = parser.parse_args(argv)
    report = audit_candidate_branch(args.base, args.candidate)
    args.json_path.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown.write_text(_markdown_report(report), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "base_commit", "candidate_commit", "changed_path_count")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
