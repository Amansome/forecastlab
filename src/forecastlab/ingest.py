"""Download raw data with a local cache.

Raw JSON/CSV is written to data/raw/ exactly as received and never edited.
A file already in the cache is reused unless refresh=True, so reruns are
reproducible and do not hit the SEC rate limit (10 requests/second).
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from . import config


def _get(url: str, headers: dict | None = None, retries: int = 4) -> requests.Response:
    last = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers or {}, timeout=60)
            if resp.status_code == 200:
                return resp
            last = RuntimeError(f"HTTP {resp.status_code} for {url}")
        except requests.RequestException as exc:  # network hiccup: retry
            last = exc
        time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"Failed to download {url}: {last}")


def _write_manifest(path: Path, url: str) -> None:
    manifest = path.with_suffix(path.suffix + ".meta.json")
    manifest.write_text(json.dumps({
        "url": url,
        "downloaded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bytes": path.stat().st_size,
    }, indent=2))


def fetch_companyfacts(cik: int, refresh: bool = False) -> dict:
    """Return the companyfacts JSON for a CIK, using data/raw/edgar as cache."""
    config.EDGAR_CACHE.mkdir(parents=True, exist_ok=True)
    path = config.EDGAR_CACHE / f"CIK{cik:010d}.json"
    if refresh or not path.exists():
        url = config.COMPANYFACTS_URL.format(cik=cik)
        resp = _get(url, headers={"User-Agent": config.SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"})
        if "facts" not in resp.json():  # never cache an error or maintenance page
            raise RuntimeError(f"Unexpected companyfacts payload for CIK {cik}")
        path.write_bytes(resp.content)
        _write_manifest(path, url)
        time.sleep(0.2)  # stay well under SEC's 10 req/s limit
    return json.loads(path.read_text())


def fetch_fred(series: str, refresh: bool = False) -> pd.DataFrame:
    """Return a FRED series as DataFrame[date, value] (cached CSV, no API key)."""
    config.FRED_CACHE.mkdir(parents=True, exist_ok=True)
    path = config.FRED_CACHE / f"{series}.csv"
    if refresh or not path.exists():
        url = config.FRED_URL.format(series=series)
        resp = _get(url)
        first_line = resp.text.splitlines()[0] if resp.text else ""
        if "," not in first_line or "<" in first_line:  # FRED serves HTML maintenance pages with HTTP 200
            raise RuntimeError(f"FRED returned non-CSV content for {series}: {first_line[:60]!r}")
        path.write_bytes(resp.content)
        _write_manifest(path, url)
    df = pd.read_csv(path)
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")  # FRED uses "." for missing
    return df.dropna()


def ingest_all(refresh: bool = False, with_macro: bool = True) -> None:
    for c in config.COMPANIES:
        facts = fetch_companyfacts(c.cik, refresh=refresh)
        name = facts.get("entityName", "?")
        print(f"[ingest] {c.ticker}: CIK {c.cik} -> {name}")
    if with_macro:
        for s in config.FRED_SERIES:
            try:
                df = fetch_fred(s, refresh=refresh)
            except RuntimeError as exc:  # macro is optional: warn and continue without it
                print(f"[ingest] WARNING: FRED {s} unavailable, macro features will be skipped ({exc})")
                continue
            print(f"[ingest] FRED {s}: {len(df)} monthly obs, last {df['date'].max().date()}")
