from __future__ import annotations

import math


def classify_equivalence(interval: tuple[float, float], margin: float) -> str:
    if not isinstance(interval, (tuple, list)) or len(interval) != 2:
        raise ValueError("interval must contain two values")
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in interval) or isinstance(margin, bool) or not isinstance(margin, (int, float)):
        raise ValueError("interval and margin must be numeric")
    try:
        lo, hi = (float(value) for value in interval)
        margin = float(margin)
    except (TypeError, ValueError) as exc:
        raise ValueError("interval and margin must be numeric") from exc
    if not math.isfinite(lo) or not math.isfinite(hi) or lo > hi:
        raise ValueError("interval must be finite and ordered")
    if not math.isfinite(margin) or margin < 0:
        raise ValueError("margin must be finite and nonnegative")
    if lo >= -margin and hi <= margin:
        return "equivalent"
    if lo > margin:
        return "directional_positive"
    if hi < -margin:
        return "directional_negative"
    return "inconclusive"
