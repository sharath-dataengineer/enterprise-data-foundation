# ADR-001: Declarative, Config-Driven Pipelines over Bespoke Spark Jobs

- **Status:** Accepted
- **Context:** Expert Recommendation & Conversion Data Foundation
- **Decision owner:** Data Engineering (me)

> Anonymized: all names are illustrative placeholders.

## Context

The foundation needed ~74 logical pipelines (process, dimension, helper, fact, reporting), each of which had to run across **5–6 environments** (dev, e2e, perf, prod, plus serverless variants) and **up to 11 regional variants** (US, Canada, UK, AU, rest-of-world, and combinations). Writing and maintaining hundreds of near-identical bespoke Spark jobs would have been unmaintainable: a change to the merge logic or a new region would mean touching dozens of files and re-testing each.

## Decision

Define every pipeline as **HOCON configuration** interpreted at runtime by a single generic Spark pipeline engine. A pipeline is a `name` plus an ordered list of `steps`, where each step binds a step class to properties (source predicates, transform SQL, merge config). Each logical table is materialized as a three-file set:

- `<name>.conf` — the transform + steps (the logic),
- `<name>_<env>.conf` — environment/region binding (`variables{}`, `spark-properties{}`),
- `<name>_<env>.ssp` — Spark session properties.

The transform is written **once**; environment and region are parameters.

## Consequences

**Positive**
- One transform definition fans out to all environments and regions; adding a region is a binding file, not a job.
- The engine centralizes cross-cutting concerns: watermarking, merge/upsert, UDF registration, metrics, DQ hooks.
- Reviews focus on declarative intent (sources, keys, grain) rather than boilerplate Spark plumbing.
- Onboarding a new pipeline is filling a known template — a golden path.

**Negative / costs**
- A config DSL is a product: it needs documentation, validation, and versioning, or it becomes tribal knowledge.
- Very complex transforms still live as large inline SQL blocks inside config — hard to unit-test in isolation (mitigated by the golden-check DQ suite).
- Engine upgrades are a shared-fate change across all pipelines; requires careful backward compatibility.

## Alternatives Considered

| Alternative | Why not |
|---|---|
| Bespoke Spark/Scala job per table | Doesn't scale to 74 × 6 × 11; massive duplication. |
| dbt (SQL-only transforms) | Strong for warehouse SQL, but the merge/upsert-to-S3 + watermark + Spark-resource-profile needs sat better with the Spark engine at the time. A modern rebuild would seriously evaluate dbt + an open table format. |
| Notebook-driven pipelines | Poor reviewability, weak CI, no enforced structure. |

## Related

[ADR-002](./002-watermark-incremental-merge-upsert.md) · [ADR-003](./003-multi-region-config-forking.md) · [Golden paths chapter](../../data-engineering-playbook/platform-engineering/golden-paths/)
