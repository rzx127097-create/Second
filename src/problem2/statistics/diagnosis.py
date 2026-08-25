from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Mapping

ORDER = (
    ("data_state_correctness", ("data", "state", "correctness")),
    ("mechanism_activation", ("mechanism", "activation")),
    ("physical_engineering_consistency", ("physical", "engineering")),
    ("learnability", ("learnability", "observation", "reward")),
    ("training_checkpoint_behavior", ("training", "checkpoint", "convergence")),
    ("comparator_fairness", ("comparator", "fairness")),
    ("genuine_boundary_or_absence", ("boundary", "absence", "effect")),
)
ALLOWED_STATUSES = {"pass", "fail", "blocked", "not_assessed", "inconclusive"}


@dataclass(frozen=True)
class DiagnosisStage:
    name: str
    status: str
    findings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def __getitem__(self, key: str) -> object:
        return self.to_dict()[key]


@dataclass(frozen=True)
class DiagnosisReport:
    stages: tuple[DiagnosisStage, ...]
    complete: bool
    inspected_row_count: int
    inspected_audit_count: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def __getitem__(self, key: str) -> object:
        return self.to_dict()[key]


def diagnose_result_bundle(validated_rows: Iterable[Mapping[str, object]], audit_records: Iterable[Mapping[str, object]]) -> DiagnosisReport:
    rows = list(validated_rows)
    audits = list(audit_records)
    if not rows:
        raise ValueError("validated_rows must not be empty")
    if any(not isinstance(row, Mapping) for row in rows) or any(not isinstance(row, Mapping) for row in audits):
        raise ValueError("diagnosis inputs must be mappings")
    for record in audits:
        status = str(record.get("status", "unknown")).lower()
        if status not in ALLOWED_STATUSES:
            raise ValueError(f"unknown diagnosis status: {status}")
    stages = []
    for name, terms in ORDER:
        matched = []
        for record in audits:
            label = str(record.get("stage", record.get("check", record.get("name", "")))).lower()
            if any(term in label for term in terms):
                matched.append(record)
        findings = []
        statuses = []
        for record in matched:
            status = str(record.get("status", "unknown")).lower()
            if status not in ALLOWED_STATUSES:
                raise ValueError(f"unknown diagnosis status: {status}")
            statuses.append(status)
            if status in {"fail", "failed", "error", "blocked"}:
                findings.append(str(record.get("reason", record.get("message", "audit failed"))))
        status = "fail" if findings else ("pass" if matched and all(str(record.get("status")).lower() == "pass" for record in matched) else ("inconclusive" if matched else "not_assessed"))
        stages.append(DiagnosisStage(name, status, tuple(findings)))
    complete = all(stage.status == "pass" for stage in stages)
    return DiagnosisReport(tuple(stages), complete, len(rows), len(audits))
