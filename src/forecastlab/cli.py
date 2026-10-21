"""Command line entry point: `forecastlab <step>` or `forecastlab all`."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from . import backtest, config, data, explain, export, ingest, monitor, plots, quality, report


def step_ingest(args):
    ingest.ingest_all(refresh=args.refresh, with_macro=not args.no_macro)


def step_quality(args):
    print(quality.run_quality(with_macro=not args.no_macro).to_string(index=False))


def step_backtest(args):
    panel = data.load_panel(use_macro=not args.no_macro)
    table = backtest.build_table(panel)
    fc, meta = backtest.run_backtest(panel, table)
    fm = backtest.fold_metrics(fc)
    cm = backtest.company_metrics(fm)
    sm = backtest.summary_metrics(fm, cm)
    hz = backtest.horizon_metrics(fc)
    boot = backtest.bootstrap_table(fm)
    config.REPORTS.mkdir(parents=True, exist_ok=True)
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    fc.to_csv(config.REPORTS / "backtest_forecasts.csv", index=False)
    fm.to_csv(config.REPORTS / "metrics_by_fold.csv", index=False)
    cm.to_csv(config.REPORTS / "metrics_by_company.csv", index=False)
    sm.to_csv(config.REPORTS / "results_summary.csv", index=False)
    hz.to_csv(config.REPORTS / "metrics_by_horizon.csv")
    boot.to_csv(config.REPORTS / "bootstrap_ci.csv", index=False)
    (config.REPORTS / "backtest_meta.json").write_text(json.dumps(meta, indent=2))
    report.write_results(sm, cm, hz, boot, meta, panel)
    plots.revenue_overview(panel)
    plots.backtest_h1(panel, fc)
    plots.mase_by_company(cm)
    plots.mape_by_fold(fm)
    print(pd.read_csv(config.REPORTS / "results_summary.csv").round(3).to_string(index=False))


def step_explain(args):
    panel = data.load_panel(use_macro=not args.no_macro)
    table = backtest.build_table(panel)
    meta = json.loads((config.REPORTS / "backtest_meta.json").read_text())
    fc = pd.read_csv(config.REPORTS / "backtest_forecasts.csv")
    cm = pd.read_csv(config.REPORTS / "metrics_by_company.csv")
    explain.run_explain(panel, table, fc, cm, meta)
    print("[explain] wrote reports/explainability.md")


def step_export(args):
    panel = data.load_panel(use_macro=not args.no_macro)
    export.run_export(panel, backtest.build_table(panel))


def step_monitor(args):
    files = [Path(args.forecasts)] if args.forecasts else sorted(config.REPORTS.glob("forecasts_origin_*.csv"))
    for f in files:
        monitor.run_monitor(f, model=args.model)


def step_spark(args):
    from . import spark_backtest
    spark_backtest.run(use_macro=not args.no_macro)


STEPS = {"ingest": step_ingest, "quality": step_quality, "backtest": step_backtest, "explain": step_explain,
         "export": step_export, "monitor": step_monitor, "spark": step_spark}
PIPELINE = ["ingest", "quality", "backtest", "explain", "export", "monitor"]


def main(argv=None):
    p = argparse.ArgumentParser(prog="forecastlab", description=__doc__)
    p.add_argument("step", choices=list(STEPS) + ["all", "offline"],
                   help="'all' = ingest..monitor; 'offline' = backtest..monitor from committed processed data")
    p.add_argument("--refresh", action="store_true", help="re-download raw data even if cached")
    p.add_argument("--no-macro", action="store_true", help="skip FRED macro features")
    p.add_argument("--forecasts", help="forecast CSV for the monitor step")
    p.add_argument("--model", default="lgbm", help="model to monitor")
    args = p.parse_args(argv)
    steps = PIPELINE if args.step == "all" else PIPELINE[2:] if args.step == "offline" else [args.step]
    for s in steps:
        print(f"=== {s} ===")
        STEPS[s](args)


if __name__ == "__main__":
    main()
