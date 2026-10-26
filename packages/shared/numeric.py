"""Reject unrepresentable derived output before scoring, statistics or JSON publication."""

import math
from typing import Any


def require_finite(value: Any, context: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"Nonfinite derived value in {context}")
    if isinstance(value, dict):
        for item in value.values():
            require_finite(item, context)
    elif isinstance(value, (list, tuple)):
        for item in value:
            require_finite(item, context)
