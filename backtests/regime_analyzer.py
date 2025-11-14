"""
Moon Dev's Regime Analyzer
Analyzes market regimes using 3 methods: Volatility, Trend (ADX), and Momentum
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from datetime import datetime

def detect_volatility_regime(returns, window=20, threshold_low=0.5, threshold_high=1.0):
    """
    Detect volatility regime using rolling volatility z-score

    Returns: 'LOW_VOL', 'MEDIUM_VOL', 'HIGH_VOL'
    """
    rolling_vol = returns.rolling(window).std() * np.sqrt(365)  # Annualized
    long_term_vol = returns.rolling(252).std() * np.sqrt(365)

    # Z-score of current vol vs long-term
    vol_mean = long_term_vol.mean()
    vol_std = long_term_vol.std()

    vol_zscore = (rolling_vol - vol_mean) / vol_std

    # Classify
    regime = []
    for z in vol_zscore:
        if pd.isna(z):
            regime.append('UNKNOWN')
        elif z > threshold_high:
            regime.append('HIGH_VOL')
        elif z < -threshold_low:
            regime.append('LOW_VOL')
        else:
            regime.append('MEDIUM_VOL')

    return regime

def detect_trend_regime(df, adx_period=14, adx_threshold=25, trend_lookback=50):
    """
    Detect trend regime using ADX

    Returns: 'UPTREND', 'DOWNTREND', 'CHOPPY'
    """
    # Calculate ADX
    adx_data = ta.adx(df['high'], df['low'], df['close'], length=adx_period)
    adx = adx_data[f'ADX_{adx_period}']

    # Price trend
    price_trend = df['close'] > df['close'].shift(trend_lookback)

    regime = []
    for i in range(len(df)):
        if pd.isna(adx.iloc[i]):
            regime.append('UNKNOWN')
        elif adx.iloc[i] > adx_threshold:
            # Trending - check direction
            if i >= trend_lookback and price_trend.iloc[i]:
                regime.append('UPTREND')
            else:
                regime.append('DOWNTREND')
        else:
            regime.append('CHOPPY')

    return regime

def detect_momentum_regime(returns, window=20, threshold=0.6):
    """
    Detect momentum regime using autocorrelation

    High autocorrelation = Momentum/Trending
    Low autocorrelation = Mean-reverting

    Returns: 'MOMENTUM', 'MEAN_REVERT', 'NEUTRAL'
    """
    autocorr = returns.rolling(window).apply(lambda x: x.autocorr(), raw=False)

    regime = []
    for ac in autocorr:
        if pd.isna(ac):
            regime.append('UNKNOWN')
        elif ac > threshold:
            regime.append('MOMENTUM')
        elif ac < -threshold:
            regime.append('MEAN_REVERT')
        else:
            regime.append('NEUTRAL')

    return regime

def analyze_regime_by_year(df):
    """
    Analyze regime statistics by year
    """
    df['year'] = df['timestamp'].dt.year

    yearly_stats = []

    for year in sorted(df['year'].unique()):
        year_data = df[df['year'] == year].copy()

        if len(year_data) < 30:  # Skip if not enough data
            continue

        # Overall stats
        total_return = (year_data['close'].iloc[-1] / year_data['close'].iloc[0] - 1) * 100
        avg_vol = year_data['returns'].std() * np.sqrt(365) * 100

        # Regime percentages
        vol_regime_pct = year_data['vol_regime'].value_counts(normalize=True) * 100
        trend_regime_pct = year_data['trend_regime'].value_counts(normalize=True) * 100
        momentum_regime_pct = year_data['momentum_regime'].value_counts(normalize=True) * 100

        yearly_stats.append({
            'Year': int(year),
            'Return %': f"{total_return:+.1f}%",
            'Avg Vol %': f"{avg_vol:.1f}%",
            'Low Vol %': vol_regime_pct.get('LOW_VOL', 0),
            'Med Vol %': vol_regime_pct.get('MEDIUM_VOL', 0),
            'High Vol %': vol_regime_pct.get('HIGH_VOL', 0),
            'Uptrend %': trend_regime_pct.get('UPTREND', 0),
            'Downtrend %': trend_regime_pct.get('DOWNTREND', 0),
            'Choppy %': trend_regime_pct.get('CHOPPY', 0),
            'Momentum %': momentum_regime_pct.get('MOMENTUM', 0),
            'Mean Rev %': momentum_regime_pct.get('MEAN_REVERT', 0),
            'Neutral %': momentum_regime_pct.get('NEUTRAL', 0)
        })

    return pd.DataFrame(yearly_stats)

def main():
    print("=" * 80)
    print("MOON DEV'S REGIME ANALYZER 🌙")
    print("=" * 80)
    print()

    # Load data
    data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/ETHUSD-1d-1000wks-data.csv'
    print(f"Loading data from: {data_path}")

    df = pd.read_csv(data_path)

    # Parse datetime (rename to timestamp for consistency)
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    print(f"✓ Loaded {len(df)} days of data")
    print(f"  Date range: {df['timestamp'].min().date()} to {df['timestamp'].max().date()}")
    print()

    # Calculate returns
    df['returns'] = df['close'].pct_change()

    print("Calculating regimes...")
    print()

    # Detect regimes
    df['vol_regime'] = detect_volatility_regime(df['returns'])
    df['trend_regime'] = detect_trend_regime(df)
    df['momentum_regime'] = detect_momentum_regime(df['returns'])

    # Analyze by year
    yearly_stats = analyze_regime_by_year(df)

    print("=" * 80)
    print("REGIME ANALYSIS BY YEAR")
    print("=" * 80)
    print()

    # Print yearly stats
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)

    print(yearly_stats.to_string(index=False))
    print()

    print("=" * 80)
    print("REGIME DEFINITIONS")
    print("=" * 80)
    print()
    print("📊 VOLATILITY REGIME:")
    print("  • LOW_VOL    = Volatility below historical average (calm markets)")
    print("  • MEDIUM_VOL = Normal volatility")
    print("  • HIGH_VOL   = Volatility above historical average (panic/euphoria)")
    print()
    print("📈 TREND REGIME:")
    print("  • UPTREND    = ADX > 25 + Price rising (strong uptrend)")
    print("  • DOWNTREND  = ADX > 25 + Price falling (strong downtrend)")
    print("  • CHOPPY     = ADX < 25 (range-bound, no clear trend)")
    print()
    print("⚡ MOMENTUM REGIME:")
    print("  • MOMENTUM   = High autocorrelation (trends persist)")
    print("  • MEAN_REVERT= Negative autocorrelation (price bounces)")
    print("  • NEUTRAL    = Low autocorrelation (random walk)")
    print()

    # Current regime
    print("=" * 80)
    print("CURRENT REGIME (Last 30 Days)")
    print("=" * 80)
    print()

    recent = df.tail(30)
    current_vol = recent['vol_regime'].mode()[0] if len(recent['vol_regime'].mode()) > 0 else 'UNKNOWN'
    current_trend = recent['trend_regime'].mode()[0] if len(recent['trend_regime'].mode()) > 0 else 'UNKNOWN'
    current_momentum = recent['momentum_regime'].mode()[0] if len(recent['momentum_regime'].mode()) > 0 else 'UNKNOWN'

    current_price = df['close'].iloc[-1]
    current_vol_pct = df['returns'].tail(30).std() * np.sqrt(365) * 100

    print(f"Current Price: ${current_price:,.2f}")
    print(f"Current Volatility: {current_vol_pct:.1f}% annualized")
    print()
    print(f"Volatility Regime:  {current_vol}")
    print(f"Trend Regime:       {current_trend}")
    print(f"Momentum Regime:    {current_momentum}")
    print()

    # Synopsis
    print("=" * 80)
    print("SYNOPSIS")
    print("=" * 80)
    print()

    # Find best performing years
    yearly_stats_clean = yearly_stats.copy()
    yearly_stats_clean['Return_num'] = yearly_stats_clean['Return %'].str.rstrip('%').astype(float)
    top_years = yearly_stats_clean.nlargest(3, 'Return_num')
    bottom_years = yearly_stats_clean.nsmallest(3, 'Return_num')

    print("🚀 TOP 3 PERFORMING YEARS:")
    for _, row in top_years.iterrows():
        print(f"  {int(row['Year'])}: {row['Return %']} - "
              f"Vol: {row['Low Vol %']:.0f}% Low/{row['Med Vol %']:.0f}% Med/{row['High Vol %']:.0f}% High, "
              f"Trend: {row['Uptrend %']:.0f}% Up/{row['Choppy %']:.0f}% Choppy")
    print()

    print("💥 BOTTOM 3 PERFORMING YEARS:")
    for _, row in bottom_years.iterrows():
        print(f"  {int(row['Year'])}: {row['Return %']} - "
              f"Vol: {row['Low Vol %']:.0f}% Low/{row['Med Vol %']:.0f}% Med/{row['High Vol %']:.0f}% High, "
              f"Trend: {row['Downtrend %']:.0f}% Down/{row['Choppy %']:.0f}% Choppy")
    print()

    # Pattern recognition
    avg_uptrend_top = top_years['Uptrend %'].mean()
    avg_uptrend_bottom = bottom_years['Uptrend %'].mean()

    avg_highvol_top = top_years['High Vol %'].mean()
    avg_highvol_bottom = bottom_years['High Vol %'].mean()

    print("📌 WINNING PATTERN:")
    if avg_uptrend_top > 50:
        print(f"  ✓ Strong uptrends (avg {avg_uptrend_top:.0f}% of time in uptrend)")
    if avg_highvol_top < 30:
        print(f"  ✓ Lower volatility (avg {avg_highvol_top:.0f}% time in high-vol)")
    print()

    print("📌 LOSING PATTERN:")
    if avg_uptrend_bottom < 30:
        print(f"  ✗ Weak trends (avg {avg_uptrend_bottom:.0f}% of time in uptrend)")
    if avg_highvol_bottom > 40:
        print(f"  ✗ Higher volatility (avg {avg_highvol_bottom:.0f}% time in high-vol)")
    print()

    print("=" * 80)
    print("Built with 🌙 by Moon Dev")
    print("=" * 80)

if __name__ == "__main__":
    main()
