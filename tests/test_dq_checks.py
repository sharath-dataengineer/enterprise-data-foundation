"""Tests for the golden-check DQ gate functions."""

from dq_checks import duplicate_check, null_check, reconciliation_check


def _rows():
    return [
        {"advisor_id": "a1", "data_region": "US", "full_name": "X", "status": "active"},
        {"advisor_id": "a2", "data_region": "US", "full_name": "Y", "status": "active"},
        {"advisor_id": "a1", "data_region": "CA", "full_name": "Z", "status": "active"},
    ]


# ── duplicate_check ──────────────────────────────────────────────────────────

def test_duplicate_check_passes_on_unique_composite_key():
    assert duplicate_check(_rows(), ["advisor_id", "data_region"]) == 1


def test_duplicate_check_fails_on_repeated_key():
    rows = _rows() + [{"advisor_id": "a1", "data_region": "US",
                       "full_name": "dup", "status": "active"}]
    assert duplicate_check(rows, ["advisor_id", "data_region"]) == 0


# ── null_check ───────────────────────────────────────────────────────────────

def test_null_check_passes_when_required_present():
    assert null_check(_rows(), ["advisor_id", "full_name", "status"]) == 1


def test_null_check_fails_on_missing_required():
    rows = _rows() + [{"advisor_id": "a3", "data_region": "US",
                       "full_name": None, "status": "active"}]
    assert null_check(rows, ["advisor_id", "full_name", "status"]) == 0


# ── reconciliation_check ─────────────────────────────────────────────────────

def test_reconciliation_passes_within_tolerance():
    assert reconciliation_check(target_count=98, source_count=100, tolerance=0.05) == 1


def test_reconciliation_fails_outside_tolerance():
    assert reconciliation_check(target_count=80, source_count=100, tolerance=0.05) == 0


def test_reconciliation_handles_zero_source():
    assert reconciliation_check(target_count=0, source_count=0) == 1
    assert reconciliation_check(target_count=5, source_count=0) == 0
