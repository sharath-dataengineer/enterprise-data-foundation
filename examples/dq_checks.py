"""
Golden-check DQ functions — executable reference for dq_checks/dim_advisor.sql.

Each check returns 1 (pass) or 0 (fail), matching the SQL contract. A failing
check blocks promotion to the reporting layer. Pure Python so the gate logic is
unit-testable without a warehouse.
"""

from collections import Counter
from typing import Iterable, Sequence


def duplicate_check(rows: Iterable[dict], business_key: Sequence[str]) -> int:
    """Pass (1) iff no business key appears more than once."""
    counts = Counter(tuple(r[k] for k in business_key) for r in rows)
    return 1 if all(c == 1 for c in counts.values()) else 0


def null_check(rows: Iterable[dict], required_cols: Sequence[str]) -> int:
    """Pass (1) iff every required column is non-null in every row."""
    for r in rows:
        for col in required_cols:
            if r.get(col) is None:
                return 0
    return 1


def reconciliation_check(target_count: int, source_count: int, tolerance: float = 0.05) -> int:
    """Pass (1) iff target row count is within `tolerance` of source count."""
    if source_count == 0:
        return 1 if target_count == 0 else 0
    return 1 if abs(target_count - source_count) / source_count <= tolerance else 0
