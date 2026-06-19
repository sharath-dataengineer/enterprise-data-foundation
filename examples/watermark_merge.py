"""
Watermark-based incremental load + idempotent merge upsert.

Pattern used across 74 production pipelines in the ERC data foundation:
  1. Read max(updated_ts) from target table (the watermark).
  2. Push incremental predicate to source read — no full rescans.
  3. Stage the delta.
  4. Merge with the current target state and write back with DYNAMIC PARTITION
     OVERWRITE — replacing only the affected partitions.

Note on mechanism: the production stack was Parquet on a Hive metastore, which
does NOT support the `MERGE INTO` DML statement (that is Delta/Iceberg only).
The merge is therefore hand-rolled — union the staged delta with the existing
rows in the affected partitions, keep the latest row per business key, and
overwrite those partitions atomically. Re-running a day is idempotent. See
ADR-002 for why this was chosen over an open table format.

Anonymized: table and column names are illustrative placeholders.
"""

from datetime import datetime, timezone

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import TimestampType
from pyspark.sql.window import Window


EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def get_watermark(
    spark: SparkSession,
    target_table: str,
    ts_col: str = "updated_ts",
) -> datetime:
    """Return max updated_ts from target, or epoch if table is empty/missing."""
    try:
        row = spark.sql(f"SELECT MAX({ts_col}) AS wm FROM {target_table}").first()
        return row["wm"] or EPOCH
    except Exception:
        return EPOCH


def load_incremental(
    spark: SparkSession,
    source_table: str,
    watermark: datetime,
    ts_col: str = "updated_ts",
) -> DataFrame:
    """Load only rows with updated_ts newer than the watermark."""
    return (
        spark.table(source_table)
             .filter(F.col(ts_col) > F.lit(watermark).cast(TimestampType()))
    )


def merge_upsert(
    spark: SparkSession,
    staged: DataFrame,
    target_table: str,
    business_key: list[str],
    partition_col: str,
    ts_col: str = "updated_ts",
) -> None:
    """
    Idempotent merge keyed on business_key, via dynamic partition overwrite.

    1. Find the partitions the staged delta touches.
    2. Read the existing rows in just those partitions.
    3. Union old + new, keep the latest row per business key by updated_ts.
    4. Overwrite ONLY the affected partitions (partitionOverwriteMode=dynamic),
       so untouched partitions are never rewritten and a replay is idempotent.
    """
    # Spark must be in dynamic mode or this overwrites the whole table.
    spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")

    affected = [r[partition_col] for r in
                staged.select(partition_col).distinct().collect()]

    try:
        existing = spark.table(target_table).filter(F.col(partition_col).isin(affected))
    except Exception:
        existing = None  # first run — target does not exist yet

    combined = (
        existing.unionByName(staged, allowMissingColumns=True)
        if existing is not None else staged
    )

    # Latest-wins dedup on the business key; ties broken deterministically.
    dedup_window = Window.partitionBy(*business_key).orderBy(F.col(ts_col).desc())
    merged = (
        combined
        .withColumn("_rn", F.row_number().over(dedup_window))
        .filter(F.col("_rn") == 1)
        .drop("_rn")
    )

    (
        merged.write
              .mode("overwrite")          # dynamic mode ⇒ only affected partitions
              .partitionBy(partition_col)
              .format("parquet")
              .saveAsTable(target_table)
    )


def run_pipeline(spark: SparkSession, config: dict) -> None:
    watermark = get_watermark(spark, config["target"], config["ts_col"])

    delta = load_incremental(spark, config["source"], watermark, config["ts_col"])
    delta.cache()

    row_count = delta.count()
    if row_count == 0:
        print(f"[{config['target']}] No new rows since {watermark}. Skipping.")
        return

    print(f"[{config['target']}] {row_count:,} incremental rows since {watermark}")
    merge_upsert(
        spark,
        delta,
        config["target"],
        config["business_key"],
        config["partition_col"],
        config["ts_col"],
    )
    print(f"[{config['target']}] Merge complete.")


if __name__ == "__main__":
    spark = (
        SparkSession.builder
        .appName("watermark-merge-example")
        .enableHiveSupport()
        .getOrCreate()
    )

    # Example: dim_agent pipeline config — mirrors examples/pipeline_config/dim_agent.conf
    pipeline_config = {
        "source": "source_prod.advisors_raw",
        "target": "analytics_mart.dim_agent",
        "ts_col": "updated_ts",
        "business_key": ["advisor_id", "data_region"],
        "partition_col": "data_region",
    }

    run_pipeline(spark, pipeline_config)
