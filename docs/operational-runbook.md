# Operational Runbook

> Anonymized reference. All names are illustrative placeholders.

How the Expert Recommendation & Conversion Data Foundation is operated day to day. The mart feeds executive revenue dashboards and per-expert incentive numbers, so the operating posture is **fail closed**: when something is wrong, hold yesterday's good data rather than publish a wrong number.

## Daily Build

| Step | What happens | Healthy signal |
|---|---|---|
| 1. Source readiness | Orchestrator waits on upstream `prc_*` and source-table partitions | Upstream partitions present for the run date |
| 2. Dimensions/helpers | `dim_*`, `helper_*`, `cfg_*` build (watermark → merge) | Watermark advances; dup/null checks pass |
| 3. Facts | `fact_*` build, including 7-day attribution | Reconciliation vs sales mart within tolerance |
| 4. Reporting | `rpt_*` aggregate from facts | Funnel totals tie to facts |
| 5. Publish | Tables promoted; dashboards refresh | All blocking DQ checks = 1 |

## Alerts & First Response

| Alert | Likely cause | First action |
|---|---|---|
| **Stale watermark** on a table | Upstream late/missing | Confirm upstream partition; if late, let the next run catch up — pipeline no-ops safely |
| **dup_check = 0** | Source duplicate or wrong merge key | Hold publish; inspect staged delta for the duplicated key; do **not** force-publish |
| **null_check = 0** | Required column missing from source | Hold publish; check for upstream schema change; fix transform/contract |
| **Reconciliation breach** | Attribution drift or booking restatement | Compare conversion totals vs sales mart for the run date; check 7-day-window edge effects |
| **Skew / long-running fact** | Hot company/contact keys | Confirm AQE skew-join active; consider salting hot keys (see spark playbook) |
| **Partition explosion / slow commit** | Too many small `rundatetime` partitions | Trigger compaction; verify dynamic-overwrite scope |

## Backfill / Reprocess

- Reprocessing is **bounded by source retention** (the sales mart keeps current + prior fiscal year). Reprocessing older fiscal years is *not possible* past the source cutoff — this is a documented constraint, not a bug.
- To reprocess a date range: re-run facts for the affected `contact_date` partitions; dynamic partition overwrite replaces only those partitions; re-run dependent `rpt_*`.
- Always re-run the DQ suite after a backfill before re-publishing.

## Change Management

- A new region/product is a new binding config + DQ checks; validate in `e2e` and `perf` before `prd` (see [ADR-003](../adr/003-multi-region-config-forking.md)).
- Engine/version changes are shared-fate; run the full DQ suite across a representative pipeline set before rollout.

## On-Call Principles

1. **Never force-publish past a blocking DQ failure** to "unblock a dashboard." A wrong revenue number costs more than a late one.
2. Prefer letting an idempotent pipeline re-run over manual data surgery.
3. Capture every incident's root cause and permanent fix; recurring classes become new golden checks.

---

## Production Incidents — What Actually Broke

> Anonymized. These are real incident classes encountered operating this system, not hypotheticals.

### Incident 1: Silent attribution double-count after fiscal-year boundary

**What happened:** At the start of a new fiscal year, the sales booking mart was restated for the prior year's final week. Orders that had previously not appeared (held in a staging system pending close) landed in the booking mart retroactively. The conversion fact's watermark-based incremental load did not pick them up — it only scanned new `updated_ts` rows, and the restated bookings had an `updated_ts` older than the current watermark.

**How we found it:** A weekly reconciliation check comparing `SUM(revenue)` in the conversion fact against the authoritative sales mart fell outside tolerance. The breach was ~3% — small enough to miss without the check, large enough to affect incentive calculations.

**Fix:** Added an explicit fiscal-year-boundary reprocessing step: at year-end, re-run the conversion fact for the full final two weeks of the fiscal year, ignoring the watermark. Made this a documented scheduled action in the runbook. The fix took 4 hours to diagnose and 20 minutes to execute. The lesson: watermark-based incrementals are safe except at restatement boundaries — document them explicitly.

**What this became:** The reconciliation check was tightened from weekly to daily. Any breach now blocks publish for that day rather than being caught weekly.

---

### Incident 2: Merge key collision after CRM source schema change

**What happened:** The CRM source system added a new market segment, which caused the `employee_id` → `advisor_business_id` join to produce duplicates — two rows per advisor for a 3-day window while the source backfill ran. The `dim_advisor` dup_check (`advisor_key` uniqueness) fired correctly and blocked publish. No incorrect data reached reporting.

**How we found it:** The DQ gate. That's the point. The dup_check returned 0, publish was blocked, on-call was paged.

**Diagnosis:** 45 minutes — inspecting the staged delta for the duplicated `advisor_key` values, tracing back to the source, confirming the CRM team's backfill was still running.

**Fix:** Held publish for 2 days while the CRM backfill completed. Re-ran the dimension after the source stabilized. No manual data surgery. Idempotent merge meant the re-run was a clean correction.

**What this became:** Added a pre-flight check on source row counts before the watermark load. A sudden 2× spike in source volume now produces a warning before the pipeline runs, not a dup_check failure after.

---

### Incident 3: Partition explosion on the conversion fact after volume spike

**What happened:** A sales campaign drove a 6× spike in recommendations over a 3-day period. The conversion fact, partitioned by `contact_date` and `rundatetime`, produced a much larger-than-normal number of small files because the dynamic overwrite wrote many small `rundatetime` partitions per `contact_date`. Subsequent daily builds started timing out at the partition registration step — the Hive metastore commit was hitting 8+ minutes for a step that normally took 30 seconds.

**How we found it:** The daily build SLA breach. The conversion fact publish was 2 hours late, which cascaded to all `rpt_*` tables.

**Diagnosis:** Spark UI showed normal execution time. The delay was entirely in the post-write partition registration. Inspecting the S3 path directly showed 4,000+ small files across the affected partitions.

**Fix:** Ran a compaction job targeting the affected `contact_date` partitions. Build time returned to normal. Added a post-build file-count check: if any partition has >500 files or average file size <32 MB, trigger compaction automatically before the next run.

**What this became:** The first item in the "What I Would Build Next" list — move to Iceberg, which eliminates this class of problem entirely. `rundatetime=` Parquet partitioning is a design constraint imposed by the engine at the time, not a choice I'd make today.

---

These incidents are in the runbook because they're how the runbook got written. Every table in the "Alerts & First Response" section above exists because something in that row actually paged someone.
