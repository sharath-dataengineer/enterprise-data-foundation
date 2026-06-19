"""
7-day first-touch attribution — executable reference for attribution_7day.sql.

Pure-Python implementation of the exact rule the SQL encodes, so the logic is
unit-testable without a Spark cluster. The SQL is the production artifact; this
mirrors it 1:1 and is what the tests pin down.

Rule: attribute a booking to the FIRST advisor who made a qualifying
recommendation in the `window_days` BEFORE the order close, matched on
company + product family. First touch is evaluated RELATIVE TO each booking's
window — not the globally earliest recommendation.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

QUALIFYING_STATUSES = {"acted_on", "lead_created"}


@dataclass(frozen=True)
class Recommendation:
    advisor_id: str
    company_id: str
    product_family: str
    recommendation_id: str
    contact_id: str
    recommendation_ts: datetime
    recommendation_status: str


@dataclass(frozen=True)
class Booking:
    booking_id: str
    company_id: str
    product_family: str
    order_amount: float
    units_booked: int
    order_close_ts: datetime


@dataclass(frozen=True)
class AttributedBooking:
    booking_id: str
    order_amount: float
    is_attributed: int
    attributed_advisor_id: Optional[str] = None
    attributed_recommendation_id: Optional[str] = None
    days_recommendation_to_close: Optional[int] = None


def attribute_bookings(
    bookings: list[Booking],
    recommendations: list[Recommendation],
    window_days: int = 7,
) -> list[AttributedBooking]:
    window = timedelta(days=window_days)
    results: list[AttributedBooking] = []

    for b in bookings:
        # Candidates: qualifying recommendations within THIS booking's window
        candidates = [
            r for r in recommendations
            if r.company_id == b.company_id
            and r.product_family == b.product_family
            and r.recommendation_status in QUALIFYING_STATUSES
            and (b.order_close_ts - window) <= r.recommendation_ts <= b.order_close_ts
        ]

        if not candidates:
            results.append(AttributedBooking(
                booking_id=b.booking_id,
                order_amount=b.order_amount,
                is_attributed=0,
            ))
            continue

        # First touch within the window
        first = min(candidates, key=lambda r: r.recommendation_ts)
        results.append(AttributedBooking(
            booking_id=b.booking_id,
            order_amount=b.order_amount,
            is_attributed=1,
            attributed_advisor_id=first.advisor_id,
            attributed_recommendation_id=first.recommendation_id,
            days_recommendation_to_close=(b.order_close_ts - first.recommendation_ts).days,
        ))

    return results
