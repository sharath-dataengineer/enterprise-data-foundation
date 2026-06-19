# Results & Impact

> Anonymized. All figures are **representative** of production workloads at this scale, generalized to protect confidentiality.

## What the Foundation Delivered

- **A single source of truth** for the recommendation→revenue funnel, replacing ad-hoc spreadsheets and one-off queries with governed, daily-refreshed marts.
- **Auditable revenue attribution**: every booked unit traces to a contact, expert, recommendation, region, and channel via an explicit, defensible 7-day first-touch rule.
- **Closed-loop ML signal**: recommendation responses flow back as labeled training data for the recommendation models.
- **Configuration-driven expansion**: new regions and products onboard as config + DQ validation rather than new code, compressing a multi-week effort into days.

## Program Outcomes It Made Measurable *(representative)*

The data foundation existed to *measure* the recommendation program. Early-pilot analysis it enabled showed:

| Outcome | Direction *(representative)* |
|---|---|
| 30-day retention of recommended cohorts | ~+1 pt vs comparable non-recommended |
| Feature adoption | ~+3–4 pts |
| Average Handle Time (AHT) | No measurable regression |
| Recommendation → conversion funnel | Now quantified end-to-end by product, region, channel, expert |

## Engineering Characteristics *(representative)*

| Dimension | Figure |
|---|---|
| Logical pipelines | ~74 |
| Config files (env × region) | ~440 |
| Source tables integrated | ~30 across 7 systems |
| Heaviest source | ~12M rows/day (sales bookings) |
| Conversion fact | ~5M rows/day |
| Refresh | hourly sources → daily mart |

## How This Connects to the Rest of the Portfolio

- The **declarative-config pattern** is the kind of golden-path / self-service thinking in the [platform-engineering chapters](../../data-engineering-playbook/platform-engineering/).
- The **incremental + merge + attribution** mechanics generalize to the [CDC](../../data-platform-reference-architecture/architectures/cdc/) and [Customer 360](../../data-platform-reference-architecture/architectures/customer360/) reference architectures.
- The **DQ-as-a-gate** posture is the applied form of the [data-quality](../../data-engineering-playbook/data-quality/) and [observability](../../data-engineering-playbook/observability/) chapters.
- The **Spark resource tuning** that makes the multi-million-row joins viable is catalogued in the [spark-performance-playbook](../../spark-performance-playbook/).

> This case study is the production evidence behind the patterns documented elsewhere in the portfolio — the same engineer who writes about the pattern has shipped it under real constraints.
