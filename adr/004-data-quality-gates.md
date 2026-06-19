# ADR-004: Data Quality as a Promotion Gate, Not a Dashboard

- **Status:** Accepted
- **Context:** Expert Recommendation & Conversion Data Foundation

> Anonymized: all names are illustrative placeholders.

## Context

These tables feed executive revenue dashboards and per-expert incentive calculations. A silent duplicate in the conversion fact could double-count revenue; a null business key could drop a region from a funnel. In a system that informs compensation and forecasts, a data-quality miss is a **trust and credibility event**, not a cosmetic bug. Logging a warning that nobody reads is insufficient.

## Decision

Every pipeline ships a `.adapt` test manifest pointing at **golden-check SQL** that runs *after* the load. Each check returns `1` (pass) or `0` (fail). A failing check **blocks promotion** of the table to the reporting layer and fails the pipeline, paging the on-call. Three check classes are standard:

- **Duplicate** — business key unique at declared grain (`HAVING count(*) > 1` ⇒ fail).
- **Null** — required columns populated.
- **Reconciliation** — funnel/conversion counts tie back to the source-of-truth sales-booking mart within tolerance.

## Consequences

**Positive**
- Bad data fails *closed*: dashboards keep yesterday's good data rather than publishing a wrong number.
- Checks are co-located with the pipeline and versioned with it — they evolve together.
- Reconciliation against the sales mart catches attribution drift that row-level checks miss.

**Negative / costs**
- Gating adds runtime and can delay a publish when a check is over-strict; thresholds need tuning.
- A blocked publish needs a clear runbook so on-call can triage quickly (see [operational runbook](../docs/operational-runbook.md)).
- Golden checks are themselves code that can rot; they need occasional review against changing business rules.

## Alternatives Considered

| Alternative | Why not |
|---|---|
| Monitoring-only (alert, don't block) | Wrong numbers still reach executives before anyone reacts. |
| Manual analyst QA | Doesn't scale to daily × 74 pipelines × regions; not repeatable. |
| Generic DQ framework only | Used for profiling, but the business-specific reconciliation logic needed bespoke SQL. |

## Related

[Data quality → reconciliation chapter](../../data-engineering-playbook/data-quality/reconciliation/) · [Observability → monitoring](../../data-engineering-playbook/observability/monitoring/) · [Pipeline & DQ patterns](../examples/)
