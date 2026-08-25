"""Pure, deterministic G5 statistical estimators."""

from .convergence import ConvergenceSummary, summarize_convergence
from .diagnosis import DiagnosisReport, DiagnosisStage, diagnose_result_bundle
from .equivalence import classify_equivalence
from .mechanism import MechanismSummary, summarize_mechanism
from .multiplicity import AdjustedRecord, holm_adjust
from .paired import PairedEstimate, hierarchical_paired_bootstrap

__all__ = [
    "AdjustedRecord", "ConvergenceSummary", "DiagnosisReport", "DiagnosisStage",
    "MechanismSummary", "PairedEstimate", "classify_equivalence",
    "diagnose_result_bundle", "hierarchical_paired_bootstrap", "holm_adjust",
    "summarize_convergence", "summarize_mechanism",
]
