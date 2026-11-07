#!/usr/bin/env python3
"""Rebuilds prices.csv from purchases.csv.

purchases.csv is the source of truth (one row per purchase).
prices.csv holds the daily close of every ticker that was bought, plus the
USD/ILS rate (ticker USDILS), from a week before the first purchase to today.
Prices come from Yahoo Finance's public chart endpoint. No API key.

Usage: python3 update.py
"""
import csv
import datetime as dt
import json
import pathlib
import subprocess
import sys
import time
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
PURCHASES = HERE / "purchases.csv"
PRICES = HERE / "prices.csv"
DATA_JS = HERE / "docs" / "data.js"
FX_SYMBOL = "ILS=X"  # Yahoo's symbol for USD -> ILS
FX_TICKER = "USDILS"


def fetch(symbol, start, end):
    """Daily closes of one symbol as {YYYY-MM-DD: close}."""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%s?period1=%d&period2=%d&interval=1d" % (
        urllib.parse.quote(symbol),
        int(time.mktime(start.timetuple())),
        int(time.mktime(end.timetuple())),
    )
    # curl, not urllib: this Mac's python.org build has no CA bundle, the system curl does.
    raw = subprocess.run(
        ["curl", "-sS", "--fail", "-m", "30", "-A", "Mozilla/5.0", url],
        check=True, capture_output=True, text=True,
    ).stdout
    body = json.loads(raw)
    result = (body.get("chart") or {}).get("result")
    if not result:
        raise RuntimeError("no data for %s: %s" % (symbol, (body.get("chart") or {}).get("error")))
    result = result[0]
    offset = result["meta"].get("gmtoffset", 0)
    stamps = result.get("timestamp") or []
    closes = result["indicators"]["quote"][0].get("close") or []
    out = {}
    for stamp, close in zip(stamps, closes):
        if close is None:
            continue
        day = dt.datetime.utcfromtimestamp(stamp + offset).strftime("%Y-%m-%d")
        out[day] = round(close, 4)
    return out


def build_site():
    """Writes docs/data.js (the site's only data file) from the two CSVs."""
    with PURCHASES.open(newline="", encoding="utf-8") as f:
        purchases = [r for r in csv.DictReader(f) if r.get("ticker")]
    for r in purchases:
        r["id"] = int(r["id"])
        r["shares"] = float(r["shares"])
        r["price_usd"] = float(r["price_usd"])
    with PRICES.open(newline="", encoding="utf-8") as f:
        prices = [[r["date"], r["ticker"], float(r["close"])] for r in csv.DictReader(f)]
    DATA_JS.parent.mkdir(exist_ok=True)
    DATA_JS.write_text(
        "window.PORTFOLIO = " + json.dumps({"purchases": purchases, "prices": prices}, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    print("docs/data.js: %d purchases, %d price rows" % (len(purchases), len(prices)))


def main():
    if "--build-only" in sys.argv:
        build_site()
        return
    with PURCHASES.open(newline="", encoding="utf-8") as f:
        purchases = [r for r in csv.DictReader(f) if r.get("ticker")]
    today = dt.date.today()
    first = min((dt.date.fromisoformat(r["date"]) for r in purchases), default=today)
    start = first - dt.timedelta(days=7)
    end = today + dt.timedelta(days=1)

    symbols = [(FX_SYMBOL, FX_TICKER)]
    for r in purchases:
        pair = (r["ticker"], r["ticker"])
        if pair not in symbols:
            symbols.append(pair)

    rows, failed = [], []
    for symbol, ticker in symbols:
        try:
            closes = fetch(symbol, start, end)
        except Exception as err:  # keep going: one bad ticker must not lose the rest
            failed.append("%s (%s)" % (ticker, err))
            continue
        if not closes:
            failed.append("%s (no rows)" % ticker)
        rows += [(day, ticker, close) for day, close in closes.items()]

    if not rows:
        sys.exit("No prices fetched: " + "; ".join(failed))
    rows.sort()
    with PRICES.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["date", "ticker", "close"])
        w.writerows(rows)
    build_site()
    print("prices.csv: %d rows, %d tickers, %s to %s" % (len(rows), len({r[1] for r in rows}), rows[0][0], rows[-1][0]))
    if failed:
        print("FAILED: " + "; ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
