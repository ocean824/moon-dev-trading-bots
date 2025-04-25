#!/usr/bin/env python3
"""
rrs_pipeline.py

Fetches OHLCV data from Coinbase Exchange, computes Real Relative Strength (RRS)
versus BTC-USD, and outputs per-symbol RRS CSVs plus a consolidated Top_RRS.csv.
"""

import os
import time
import requests
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# ==== CONFIGURATION ====
BENCHMARK     = 'BTC-USD'
SYMBOLS       = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'PEPE-USD', 'TAO-USD', 'FET-USD']
TIMEFRAMES    = ['6h', '1d']
WEEKS         = 104
DATA_DIR      = Path('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/bots/hyperliquid/rrs/data')
RESULTS_DIR   = Path('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/bots/hyperliquid/rrs/results')
BASE_URL      = "https://api.exchange.coinbase.com"

# ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# load .env for API creds if needed (public endpoints don't require auth)
load_dotenv(Path(__file__).parent / '.env')
API_KEY    = os.getenv('COINBASE_API_KEY')
API_SECRET = os.getenv('COINBASE_API_SECRET')


def sign_request(method: str, path: str, body: str = '', timestamp: str = None) -> dict:
    ts = timestamp or str(int(time.time()))
    return {
        'CB-ACCESS-KEY':       API_KEY or '',
        'CB-ACCESS-TIMESTAMP': ts,
        'Accept':             'application/json',
        'Content-Type':       'application/json'
    }


def timeframe_to_granularity(tf: str) -> int:
    unit = tf[-1]; val = int(tf[:-1])
    if unit == 'm': return val * 60
    if unit == 'h': return val * 3600
    if unit == 'd': return val * 86400
    raise ValueError(f"Unsupported timeframe: {tf}")


def get_historical_data(symbol: str, timeframe: str, weeks: int) -> pd.DataFrame:
    outfile = DATA_DIR / f"{symbol.replace('-','')}-{timeframe}-{weeks}wks.csv"
    if outfile.exists():
        return pd.read_csv(outfile, parse_dates=['datetime'], index_col='datetime')

    end_time   = datetime.utcnow()
    start_time = end_time - timedelta(weeks=weeks)
    gran       = timeframe_to_granularity(timeframe)
    chunk_delta= timedelta(seconds=300*gran)

    all_candles = []
    cursor = start_time
    while cursor < end_time:
        window_end = min(cursor + chunk_delta, end_time)
        params = {
            'start':       cursor.isoformat(),
            'end':         window_end.isoformat(),
            'granularity': gran
        }
        path = f"/products/{symbol}/candles"
        r = requests.get(f"{BASE_URL}{path}", params=params, headers=sign_request('GET', path))
        r.raise_for_status()
        all_candles.extend(r.json())
        cursor = window_end
        time.sleep(0.34)

    df = pd.DataFrame(all_candles, columns=[
        'timestamp', 'low', 'high', 'open', 'close', 'volume'
    ]).rename(columns={'timestamp':'datetime'})
    df['datetime'] = pd.to_datetime(df['datetime'], unit='s')
    df = df.set_index('datetime').sort_index()
    df.to_csv(outfile)
    return df


def compute_metrics(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    df = df.copy()
    df['log_return']     = np.log(df['close'] / df['close'].shift(1))
    df['volatility']     = df['log_return'].rolling(window).std()
    df['average_volume'] = df['volume'].rolling(window).mean()
    df['volume_ratio']   = df['volume'] / df['average_volume']
    return df.dropna(subset=['log_return','volatility','volume_ratio'])


def calculate_rrs(df: pd.DataFrame, bm_df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    df = df.copy()
    bm = bm_df[['log_return']].rename(columns={'log_return':'log_return_benchmark'})
    merged = df.join(bm, how='inner')
    merged['differential_return'] = merged['log_return'] - merged['log_return_benchmark']
    merged['normalized_return']   = merged['differential_return'] / merged['volatility']
    merged['rrs']                 = merged['normalized_return'] * merged['volume_ratio']
    merged['smoothed_rrs']        = merged['rrs'].ewm(span=window, adjust=False).mean()
    return merged.reset_index()


def main():
    # 1) fetch & process benchmark per timeframe
    for tf in TIMEFRAMES:
        bm_df      = get_historical_data(BENCHMARK, tf, WEEKS)
        bm_metrics = compute_metrics(bm_df)

        # 2) each symbol vs benchmark
        for sym in SYMBOLS:
            if sym == BENCHMARK: continue
            df       = get_historical_data(sym, tf, WEEKS)
            metrics  = compute_metrics(df)
            rrs_df   = calculate_rrs(metrics, bm_metrics)
            out_file = RESULTS_DIR / f"{sym.replace('-','')}_{tf}_rrs.csv"
            rrs_df.to_csv(out_file, index=False)

    # 3) aggregate Top_RRS.csv with correct timeframe
    top_list = []
    for file in RESULTS_DIR.glob('*_rrs.csv'):
        parts = file.stem.split('_')
        if len(parts) < 3:
            continue
        symbol, timeframe, _ = parts  # e.g. ['FETUSD','6h','rrs']
        df = pd.read_csv(file)
        if df.empty: continue
        top3 = df.nlargest(3, 'rrs')
        for _, row in top3.iterrows():
            top_list.append({
                'timeframe': timeframe,
                'symbol':    symbol,
                'timestamp': row['datetime'],
                'rrs':       row['rrs'],
                'source':    file.name
            })

    if top_list:
        results_df = (pd.DataFrame(top_list)
                         .sort_values('rrs', ascending=False)
                         .reset_index(drop=True))
        results_df.to_csv(RESULTS_DIR / 'Top_RRS.csv', index=False)
        print("✅ Wrote Top_RRS.csv")
    else:
        print("⚠️ No RRS results to aggregate.")

if __name__ == "__main__":
    main()
