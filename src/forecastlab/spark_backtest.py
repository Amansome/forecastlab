"""Optional: the feature + LightGBM backtest step re-implemented in PySpark.

* Features are computed with Spark window functions (lag/lead over each
  company's quarters), not by calling the pandas feature code.
* Each fold is a group: training rows (target quarter <= origin) and test rows
  (origin == fold) are tagged, then trained/predicted with groupBy().applyInPandas.
* The result is compared with the pandas pipeline (features and forecasts).

This runs Spark in local mode (local[*]). It was not run on Databricks.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

from . import backtest, config, data, features
from .models import GlobalLGBM


def _qord(p: pd.Period) -> int:
    return p.year * 4 + p.quarter - 1


def _spark():
    from pyspark.sql import SparkSession
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)  # workers must see this environment's packages
    return (SparkSession.builder.master("local[*]").appName("forecastlab")
            .config("spark.sql.session.timeZone", "UTC")
            .config("spark.sql.execution.arrow.pyspark.enabled", "true")
            .config("spark.sql.shuffle.partitions", "8")
            .config("spark.ui.enabled", "false").getOrCreate())


def spark_features(spark, panel: data.Panel):
    from pyspark.sql import Window
    from pyspark.sql import functions as F

    rows = [{"ticker": t, "q": _qord(q), "revenue": float(v), "available_date": panel.available[t][q]}
            for t, y in panel.series.items() for q, v in y.items()]
    rev = spark.createDataFrame(pd.DataFrame(rows))
    w = Window.partitionBy("ticker").orderBy("q")
    df = rev.withColumn("l", F.log("revenue"))
    for k in range(12):
        df = df.withColumn(f"l{k}", F.lag("l", k).over(w))
    for k in range(1, 5):
        df = df.withColumn(f"lead{k}", F.lead("l", k).over(w))
    df = df.where(F.col("l11").isNotNull())                       # MIN_HISTORY quarters
    for k in range(8):
        df = df.withColumn(f"yoy{k}", F.col(f"l{k}") - F.col(f"l{k + 4}"))
    yoys = [F.col(f"yoy{k}") for k in range(8)]
    mean8 = sum(yoys) / 8
    df = (df.withColumn("yoy_mean8", mean8)
            .withColumn("yoy_std8", F.sqrt(sum((c - mean8) ** 2 for c in yoys) / 7))
            .withColumn("trailing4", F.log((F.exp("l0") + F.exp("l1") + F.exp("l2") + F.exp("l3")) / 4)))

    hz = spark.createDataFrame(pd.DataFrame({"h": config.HORIZONS}))
    df = df.crossJoin(hz)
    base = F.when(F.col("h") == 1, F.col("l3")).when(F.col("h") == 2, F.col("l2")).when(F.col("h") == 3, F.col("l1")).otherwise(F.col("l0"))
    base8 = F.when(F.col("h") == 1, F.col("l7")).when(F.col("h") == 2, F.col("l6")).when(F.col("h") == 3, F.col("l5")).otherwise(F.col("l4"))
    lead = F.when(F.col("h") == 1, F.col("lead1")).when(F.col("h") == 2, F.col("lead2")).when(F.col("h") == 3, F.col("lead3")).otherwise(F.col("lead4"))
    tq = (F.col("q") + F.col("h")) % 4 + 1
    out = df.select(
        "ticker", F.col("q").alias("origin_q"), "h", (F.col("q") + F.col("h")).alias("target_q"),
        F.exp(base).alias("base"), (lead - base).alias("target"),
        *[(tq == i).cast("int").alias(f"tq_{i}") for i in range(1, 5)],
        F.col("yoy0").alias("yoy_0"), F.col("yoy1").alias("yoy_1"), F.col("yoy2").alias("yoy_2"), F.col("yoy3").alias("yoy_3"),
        ((F.col("yoy0") + F.col("yoy1") + F.col("yoy2") + F.col("yoy3")) / 4).alias("yoy_mean4"),
        "yoy_mean8", "yoy_std8", (F.col("yoy0") - F.col("yoy4")).alias("yoy_accel"),
        (F.col("l0") - F.col("l1")).alias("qoq_0"), (base - base8).alias("base_yoy"),
        (base - F.col("trailing4")).alias("base_vs_trailing4"), (F.col("l0") - F.col("trailing4")).alias("level_vs_ma4"),
    )
    if panel.macro is not None:
        cycle = rev.groupBy("q").agg(F.max("available_date").alias("cycle_date"))
        m = panel.macro.assign(mq=panel.macro["quarter"].apply(_qord))[["mq", "macro_retail_yoy", "macro_cpi_yoy", "available_date"]]
        mw = Window.orderBy("mq")
        macro = (spark.createDataFrame(m).withColumn("prev_retail", F.lag("macro_retail_yoy").over(mw))
                 .withColumnRenamed("available_date", "macro_pub"))
        pub = (cycle.join(macro, macro["macro_pub"] <= cycle["cycle_date"])
                    .withColumn("rk", F.row_number().over(Window.partitionBy("q").orderBy(F.desc("mq"))))
                    .where("rk = 1")
                    .select(F.col("q").alias("origin_q"), "macro_retail_yoy", "macro_cpi_yoy",
                            (F.col("macro_retail_yoy") - F.col("prev_retail")).alias("macro_retail_yoy_chg")))
        out = out.join(pub, "origin_q", "left")
    return out


def _fold_udf(variants: dict):
    def run(pdf: pd.DataFrame) -> pd.DataFrame:
        fold = int(pdf["fold"].iloc[0])
        train = pdf[pdf["role"] == "train"].rename(columns={"origin_q": "origin"})
        test = pdf[pdf["role"] == "test"].rename(columns={"origin_q": "origin"})
        res = []
        for name, cols in variants.items():
            pred = GlobalLGBM(cols).fit(train).predict(test.sort_values(["ticker", "h"]))
            t = test.sort_values(["ticker", "h"])
            res.append(pd.DataFrame({"fold": fold, "ticker": t["ticker"].to_numpy(), "h": t["h"].to_numpy(),
                                     "model": name, "forecast": pred}))
        # pandas>=3 strings are Arrow-backed; PySpark's serializer expects plain objects.
        return pd.concat(res).astype({"ticker": object, "model": object})
    return run


def run(use_macro: bool = True) -> dict:
    from pyspark.sql import functions as F

    panel = data.load_panel(use_macro=use_macro)
    spark = _spark()
    spark.sparkContext.setLogLevel("ERROR")
    sf = spark_features(spark, panel).cache()

    # 1) Feature parity with the pandas implementation.
    pd_table = backtest.build_table(panel)
    variants = backtest.lgbm_variants(pd_table)
    cols = sorted({c for v in variants.values() for c in v} - {"h"}) + ["base", "target"]  # h is a join key
    sp = sf.toPandas()
    pd_table = pd_table.assign(origin_q=pd_table["origin"].apply(_qord))
    merged = pd_table.merge(sp, on=["ticker", "origin_q", "h"], suffixes=("_pd", "_sp"))
    def diff(c):  # relative for the USD level column, absolute for log-growth features
        a, b = merged[f"{c}_pd"].astype(float), merged[f"{c}_sp"].astype(float)
        return float(np.nanmax(np.abs(b / a - 1) if c == "base" else np.abs(a - b)))
    feat_diff = {c: diff(c) for c in cols}

    # 2) Fold-parallel LightGBM backtest in Spark.
    origins = [_qord(o) for o in backtest.fold_origins(panel)]
    folds = spark.createDataFrame(pd.DataFrame({"fold": origins}))
    tagged = (sf.crossJoin(folds)
                .withColumn("role", F.when((F.col("target_q") <= F.col("fold")) & F.col("target").isNotNull(), "train")
                                     .when(F.col("origin_q") == F.col("fold"), "test"))
                .where(F.col("role").isNotNull()))
    leaks = tagged.where((F.col("role") == "train") & (F.col("target_q") > F.col("fold"))).count()
    schema = "fold long, ticker string, h long, model string, forecast double"
    fc = tagged.groupBy("fold").applyInPandas(_fold_udf(variants), schema=schema).toPandas()
    spark.stop()

    # 3) Forecast parity with the pandas backtest.
    pdf = pd.read_csv(config.REPORTS / "backtest_forecasts.csv")
    pdf = pdf[pdf["model"].isin(list(variants))].assign(fold=lambda d: d["origin"].apply(lambda s: _qord(pd.Period(s, "Q"))))
    cmp_ = pdf.merge(fc, on=["fold", "ticker", "h", "model"], suffixes=("_pd", "_sp"))
    rel = (cmp_["forecast_sp"] / cmp_["forecast_pd"] - 1).abs()
    result = {
        "spark_mode": "local[*] (not Databricks)",
        "n_feature_rows_spark": int(len(sp)), "n_feature_rows_pandas": int(len(pd_table)),
        "max_abs_feature_diff": max(feat_diff.values()), "feature_diff_by_column": feat_diff,
        "train_rows_with_future_label": int(leaks),
        "n_forecasts_compared": int(len(cmp_)), "n_forecasts_pandas": int(len(pdf)),
        "max_rel_forecast_diff": float(rel.max()), "mean_rel_forecast_diff": float(rel.mean()),
    }
    (config.REPORTS / "spark_parity.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "feature_diff_by_column"}, indent=2))
    return result
