"""
Tests for 7-day first-touch attribution.

The key test is `test_first_touch_is_within_window_not_global` — it pins the
exact bug the naive implementation has: picking the globally-earliest
recommendation and then filtering by the window drops valid attributions.
"""

from datetime import datetime

from attribution import Booking, Recommendation, attribute_bookings


def _rec(advisor, ts, status="acted_on", company="C1", product="payroll", rid=None):
    return Recommendation(
        advisor_id=advisor,
        company_id=company,
        product_family=product,
        recommendation_id=rid or f"r_{advisor}_{ts:%Y%m%d}",
        contact_id=f"contact_{advisor}",
        recommendation_ts=ts,
        recommendation_status=status,
    )


def _booking(close, company="C1", product="payroll", amount=1000.0):
    return Booking(
        booking_id="b1",
        company_id=company,
        product_family=product,
        order_amount=amount,
        units_booked=1,
        order_close_ts=close,
    )


def test_basic_attribution_to_first_advisor_in_window():
    bookings = [_booking(datetime(2024, 3, 10))]
    recs = [
        _rec("adv_A", datetime(2024, 3, 5)),   # first in window
        _rec("adv_B", datetime(2024, 3, 8)),
    ]
    [res] = attribute_bookings(bookings, recs)
    assert res.is_attributed == 1
    assert res.attributed_advisor_id == "adv_A"
    assert res.days_recommendation_to_close == 5


def test_first_touch_is_within_window_not_global():
    """
    adv_A recommended 30 days out (outside the 7-day window); adv_B recommended
    3 days out (inside). Correct answer: attribute to adv_B. A global-first-touch
    implementation would pick adv_A, then filter it out, and wrongly drop the
    booking to unattributed.
    """
    bookings = [_booking(datetime(2024, 3, 10))]
    recs = [
        _rec("adv_A", datetime(2024, 2, 9)),   # 30 days before — out of window
        _rec("adv_B", datetime(2024, 3, 7)),   # 3 days before — in window
    ]
    [res] = attribute_bookings(bookings, recs)
    assert res.is_attributed == 1
    assert res.attributed_advisor_id == "adv_B"


def test_no_qualifying_recommendation_is_unattributed():
    bookings = [_booking(datetime(2024, 3, 10))]
    recs = [_rec("adv_A", datetime(2024, 1, 1))]   # far outside window
    [res] = attribute_bookings(bookings, recs)
    assert res.is_attributed == 0
    assert res.attributed_advisor_id is None


def test_non_qualifying_status_is_ignored():
    bookings = [_booking(datetime(2024, 3, 10))]
    recs = [_rec("adv_A", datetime(2024, 3, 8), status="viewed")]
    [res] = attribute_bookings(bookings, recs)
    assert res.is_attributed == 0


def test_product_family_must_match():
    bookings = [_booking(datetime(2024, 3, 10), product="payroll")]
    recs = [_rec("adv_A", datetime(2024, 3, 8), product="payments")]
    [res] = attribute_bookings(bookings, recs)
    assert res.is_attributed == 0
