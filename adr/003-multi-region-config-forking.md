# ADR-003: Region & Environment as Configuration, Not Forked Code

- **Status:** Accepted
- **Context:** Expert Recommendation & Conversion Data Foundation

> Anonymized: all names are illustrative placeholders.

## Context

The recommendation funnel runs for multiple geographies — US, Canada, UK, AU, and rest-of-world, plus combinations — each with slightly different product catalogs, eligibility rules, and fiscal calendars. It also runs across dev/e2e/perf/prod. The naive approach (copy the transform per region) would have multiplied ~74 pipelines into many hundreds of divergent files that drift apart over time.

## Decision

Treat **region and environment as parameters**, expressed as filename suffixes (`_canada`, `_uk`, `_row`, `_prd`, `_e2e`) and `variables{}` values in the binding config. The transform definition (`<name>.conf`) is shared; only the binding differs (target schema, S3 path, region filter, resource profile). Region-specific business rules (e.g. a different product-eligibility filter) are isolated to small, named config blocks rather than copied SQL.

## Consequences

**Positive**
- A new region is a new binding file + DQ validation, typically days not weeks.
- Logic fixes apply everywhere at once — no drift between US and international.
- The diff for "add UK Payments SKU" is small and reviewable.

**Negative / costs**
- Region-specific exceptions must be carefully scoped; an unguarded change to the shared transform affects all regions (mitigated by per-region golden checks).
- Filename-suffix conventions must be disciplined and documented, or the matrix becomes confusing.
- Static, per-region seed/lookup tables (`cfg_*`) still require analyst curation.

## Alternatives Considered

| Alternative | Why not |
|---|---|
| One transform per region | Guaranteed drift; unmaintainable matrix. |
| Single global table with region column only | Doesn't handle divergent product catalogs / fiscal calendars / eligibility cleanly. |
| Runtime feature flags in code | Pushes config into a deploy cycle; slower and less reviewable than declarative bindings. |

## Related

[ADR-001](./001-declarative-config-driven-pipelines.md) · [Self-service platforms chapter](../../data-engineering-playbook/platform-engineering/self-service-platforms/)
