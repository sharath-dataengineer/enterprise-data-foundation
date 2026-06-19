# Tradeoffs

> Anonymized case study. All names are illustrative placeholders; figures are representative.

The decisions that shaped the Expert Recommendation & Conversion Data Foundation, and what each one cost. Principal-level engineering is mostly about being explicit about the second column.

## 1. Declarative config framework vs. bespoke jobs

**Chose:** a generic Spark engine driven by HOCON config ([ADR-001](./adr/001-declarative-config-driven-pipelines.md)).

| Upside | Downside |
|---|---|
| One transform → 6 environments × 11 regions | The config DSL is itself a product to document and version |
| Centralized watermark/merge/DQ/metrics | Big inline-SQL transforms are hard to unit-test |
| New pipeline = fill a template (golden path) | Engine upgrades are shared-fate across all pipelines |

## 2. Hand-rolled merge-to-S3 vs. open table format

**Chose:** staged delta + custom merge operator writing `rundatetime=`-partitioned Parquet ([ADR-002](./adr/002-watermark-incremental-merge-upsert.md)).

| Upside | Downside |
|---|---|
| Worked with the platform defaults at the time | No ACID/time-travel; relies on single-writer orchestration |
| Idempotent via dynamic partition overwrite | Small-file/metadata growth needs periodic compaction |
| Simple mental model | Iceberg/Delta `MERGE INTO` would be cleaner — flagged as the next step |

## 3. Daily batch vs. streaming

**Chose:** daily batch build off hourly-landed sources.

| Upside | Downside |
|---|---|
| Matched the funnel's daily decision cadence | Recommendation-response labels reach the ML team next-day, not in minutes |
| Lower operational complexity, cheaper | A real-time funnel would need a streaming rebuild |

## 4. DQ as a gate vs. as monitoring

**Chose:** golden checks block promotion ([ADR-004](./adr/004-data-quality-gates.md)).

| Upside | Downside |
|---|---|
| Wrong numbers never reach executives | Over-strict checks can delay a publish |
| Reconciliation catches attribution drift | Gating needs a crisp triage runbook |

## 5. 7-day, first-touch attribution vs. multi-touch

**Chose:** attribute a conversion to the **first** qualifying expert if the order books within 7 days.

| Upside | Downside |
|---|---|
| Simple, explainable, defensible to finance | Undercounts multi-expert journeys |
| Matches how the program credits experts | Window is a business assumption that must be revisited as the program evolves |

## 6. Region as config vs. global table with a region column

**Chose:** region as a binding parameter ([ADR-003](./adr/003-multi-region-config-forking.md)).

| Upside | Downside |
|---|---|
| Handles divergent catalogs/calendars/eligibility cleanly | More files in the config matrix |
| New region in days | Region-specific exceptions must be carefully scoped |
