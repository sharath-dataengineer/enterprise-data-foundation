# ADR-002: Watermarked Incremental Load + Idempotent Merge/Upsert

- **Status:** Accepted
- **Context:** Expert Recommendation & Conversion Data Foundation

> Anonymized: all names are illustrative placeholders.

## Context

Sources refresh hourly and range up to ~12M rows/day (sales bookings) and ~2M rows/day (clickstream). A full rescan-and-rebuild of every dimension and fact each day would be slow and expensive, and would couple every pipeline to the slowest upstream. We also feed revenue dashboards, so re-running a day must be **safe** — no double counting, no partial states.

## Decision

1. **Per-pipeline watermarking.** Each pipeline derives its incremental window from the **max `updated_ts` of its own target table**, then pushes that down as a predicate on its sources. Pipelines are independent.
2. **Stage then merge.** The incremental transform writes a staged delta; a merge operator upserts the delta into a history-preserving target keyed on an explicit **business key**.
3. **Partitioned, dynamically-overwritten output.** Targets are partitioned Parquet under `rundatetime=<ts>` with `partitionOverwriteMode=dynamic`, so a re-run replaces only the affected partitions — making the load **idempotent**.

## Consequences

**Positive**
- Cost and runtime scale with *changed* data, not total data.
- Re-running a failed day is safe and bounded.
- Decoupled pipelines: a late upstream delays only its own downstream, and only as far as its watermark.

**Negative / costs**
- Watermark on `updated_ts` assumes sources reliably stamp updates; late-arriving or back-dated rows need a lookback buffer.
- Hand-rolled merge-to-S3 lacks the ACID guarantees and concurrency control of an open table format — the chosen mitigation was strict single-writer-per-partition orchestration. A rebuild would use Iceberg/Delta `MERGE INTO`.
- `rundatetime=` directory partitioning can accumulate small files and metadata; requires periodic compaction.

## Alternatives Considered

| Alternative | Why not |
|---|---|
| Full daily rebuild | Too slow/expensive at this volume; not idempotent-friendly for partial failures. |
| CDC streaming merge | Higher operational complexity than the daily SLA required at the time. |
| Open-format `MERGE INTO` (Iceberg/Delta) | The right long-term answer; not the platform default when built. Flagged as next step. |

## Related

[ADR-004](./004-data-quality-gates.md) · [CDC reference architecture](../../data-platform-reference-architecture/architectures/cdc/) · [Spark file-sizing / compaction](../../spark-performance-playbook/topics/compaction/)
