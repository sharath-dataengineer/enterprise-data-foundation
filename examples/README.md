# Examples — ERC Data Foundation Patterns

Working reference implementations of the three core patterns used across the 74-pipeline data foundation. Table and column names are anonymized illustrative placeholders.

## Files

| File | What it shows |
|------|--------------|
| [`watermark_merge.py`](./watermark_merge.py) | Watermark-based incremental load + idempotent CDC-style merge upsert — the pattern behind every dim and fact pipeline |
| [`attribution_7day.sql`](./attribution_7day.sql) | 7-day first-touch attribution query: attribute a booking to the first advisor who made a qualifying recommendation within 7 days, keyed on company + product family |
| [`pipeline_config/dim_agent.conf`](./pipeline_config/dim_agent.conf) | HOCON pipeline definition — the three-file pattern: transform definition (region/env agnostic), environment binding, Spark session properties |
| [`pipeline_config/dim_agent_prod.conf`](./pipeline_config/dim_agent_prod.conf) | Production environment binding — shows how one transform fans out to multiple environments/regions via config, not copied code |
| [`dq_checks/dim_agent.sql`](./dq_checks/dim_agent.sql) | Golden-check DQ manifest: duplicate key check, null check, row count reconciliation — each returns 1 (pass) or 0 (fail), blocking promotion on failure |

## The Three-File Pipeline Pattern

Every pipeline follows a three-file structure:

| File | Role |
|------|------|
| `<table>.conf` | Transform definition — steps, inline SQL, merge config. Region/env agnostic. |
| `<table>_<env>.conf` | Environment binding — includes the shared transform, sets `variables{}` and `spark-properties{}`. |

Adding a new region is a new binding file. The transform definition is never forked.

## The Four-Step Execution

Each pipeline declares a step list executed by the generic Spark engine:

| Step | Responsibility |
|------|----------------|
| `RegisterUDFs` | Surrogate-key generation, PII tokenization |
| `LoadSourcesWithWatermark` | Compute watermark from target max(updated_ts); push incremental predicate to source |
| `BuildFromSource` | Execute the inline SQL transform into a staged view |
| `MergeUpsert` | Upsert staged delta into target on business key; dynamic partition overwrite |

## Key Design Decisions

- [ADR-001: Declarative config-driven pipelines](../adr/001-declarative-config-driven-pipelines.md)
- [ADR-002: Watermark incremental + merge upsert](../adr/002-watermark-incremental-merge-upsert.md)
- [ADR-003: Multi-region config forking](../adr/003-multi-region-config-forking.md)
- [ADR-004: Data quality as a gate](../adr/004-data-quality-gates.md)
