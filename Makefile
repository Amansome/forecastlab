PY ?= python

.PHONY: install test reproduce offline ingest quality backtest explain export monitor spark clean

install:            ## install package + test deps
	$(PY) -m pip install -e ".[dev]"

test:               ## unit tests incl. leakage tests (no network needed)
	$(PY) -m pytest

reproduce:          ## full pipeline: download (cached) -> quality -> backtest -> SHAP -> export -> monitor
	$(PY) -m forecastlab all

offline:            ## rerun modelling from committed data/processed (no network)
	$(PY) -m forecastlab offline

ingest quality backtest explain export monitor spark:
	$(PY) -m forecastlab $@

clean:
	rm -rf reports/*.csv reports/*.md reports/*.json reports/figures/* exports/*
