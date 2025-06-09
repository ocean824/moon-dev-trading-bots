"""
🌙 MOON DEV'S LIQUIDATION DATA QUALITY ANALYZER 🔍
Deep dive into data patterns to find the alpha!
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("🌙 MOON DEV'S DATA DETECTIVE MODE ACTIVATED! 🔍")
print("=" * 60)

def analyze_liquidation_data(data_path):
    """
    🔍 Moon Dev's comprehensive data analysis
    """
    print("📊 Loading liquidation data for Moon Dev's investigation... 🌙")
    
    # Load data
    df = pd.read_csv(data_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    
    print(f"🎉 Loaded {len(df):,} liquidation records! 🚀")
    print(f"📅 Date range: {df['datetime'].min()} to {df['datetime'].max()}")
    print(f"⏰ Total span: {(df['datetime'].max() - df['datetime'].min()).days} days")
    
    # 1. SYMBOL ANALYSIS - What are we dealing with?
    print("\n" + "="*50)
    print("🪙 MOON DEV'S SYMBOL BREAKDOWN ANALYSIS 🪙")
    print("="*50)
    
    symbol_stats = df.groupby('symbol').agg({
        'original_quantity': ['count', 'sum', 'mean'],
        'usd_size': ['sum', 'mean', 'max'],
        'price': ['mean', 'std']
    }).round(4)
    
    symbol_stats.columns = ['liquidation_count', 'total_quantity', 'avg_quantity', 
                           'total_usd', 'avg_usd', 'max_usd', 'avg_price', 'price_volatility']
    
    # Sort by total USD liquidated
    symbol_stats = symbol_stats.sort_values('total_usd', ascending=False)
    
    print(f"📊 Total unique symbols: {len(symbol_stats)}")
    print(f"🔥 Top 10 symbols by USD liquidated:")
    
    for i, (symbol, row) in enumerate(symbol_stats.head(10).iterrows()):
        btc_marker = "🪙 BTC" if symbol == 'BTC' else ""
        print(f"   {i+1:2d}. {symbol:10s} {btc_marker}")
        print(f"       💰 Total USD: ${row['total_usd']:>15,.0f}")
        print(f"       🔢 Count: {row['liquidation_count']:>8,.0f}")
        print(f"       💵 Avg USD: ${row['avg_usd']:>10,.2f}")
    
    # 2. BTC vs ALL ANALYSIS
    print("\n" + "="*50)
    print("🪙 MOON DEV'S BTC VS ALL CRYPTO ANALYSIS 🪙")
    print("="*50)
    
    btc_data = df[df['symbol'] == 'BTC']
    non_btc_data = df[df['symbol'] != 'BTC']
    
    btc_pct = len(btc_data) / len(df) * 100
    btc_usd_pct = btc_data['usd_size'].sum() / df['usd_size'].sum() * 100
    
    print(f"🪙 BTC liquidations: {len(btc_data):,} ({btc_pct:.1f}% of records)")
    print(f"💰 BTC USD volume: ${btc_data['usd_size'].sum():,.0f} ({btc_usd_pct:.1f}% of total)")
    print(f"🌊 Other cryptos: {len(non_btc_data):,} records across {non_btc_data['symbol'].nunique()} symbols")
    
    # 3. LIQUIDATION SIZE DISTRIBUTION
    print("\n" + "="*50)
    print("💰 MOON DEV'S LIQUIDATION SIZE ANALYSIS 💰")
    print("="*50)
    
    # Overall distribution
    print("🌊 Overall USD liquidation distribution:")
    percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
    for p in percentiles:
        value = np.percentile(df['usd_size'], p)
        print(f"   {p:2d}th percentile: ${value:>10,.2f}")
    
    # Whale detection
    whale_threshold = np.percentile(df['usd_size'], 95)
    whales = df[df['usd_size'] >= whale_threshold]
    print(f"\n🐋 Whale liquidations (top 5%): {len(whales):,} events")
    print(f"💰 Whale USD volume: ${whales['usd_size'].sum():,.0f}")
    print(f"🪙 Whale BTC events: {len(whales[whales['symbol'] == 'BTC']):,}")
    
    # 4. TEMPORAL PATTERNS
    print("\n" + "="*50)
    print("⏰ MOON DEV'S TEMPORAL PATTERN ANALYSIS ⏰")
    print("="*50)
    
    df['hour'] = df['datetime'].dt.hour
    df['day_of_week'] = df['datetime'].dt.dayofweek
    
    # Hourly patterns
    hourly_volume = df.groupby('hour')['usd_size'].sum().sort_values(ascending=False)
    print("🕐 Top liquidation hours (UTC):")
    for i, (hour, volume) in enumerate(hourly_volume.head(5).items()):
        print(f"   {i+1}. {hour:2d}:00 - ${volume:>12,.0f}")
    
    # Weekly patterns  
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    daily_volume = df.groupby('day_of_week')['usd_size'].sum()
    print("\n📅 Weekly liquidation pattern:")
    for day_idx, volume in daily_volume.items():
        print(f"   {day_names[day_idx]}: ${volume:>15,.0f}")
    
    # 5. SIDE ANALYSIS (Buy vs Sell liquidations)
    print("\n" + "="*50)
    print("⚖️ MOON DEV'S LIQUIDATION DIRECTION ANALYSIS ⚖️")
    print("="*50)
    
    side_analysis = df.groupby(['symbol', 'side']).agg({
        'usd_size': ['count', 'sum', 'mean']
    }).round(2)
    
    btc_sides = side_analysis.loc['BTC'] if 'BTC' in side_analysis.index else None
    if btc_sides is not None:
        print("🪙 BTC liquidation breakdown:")
        for side in ['BUY', 'SELL']:
            if side in btc_sides.index:
                count = btc_sides.loc[side, ('usd_size', 'count')]
                total = btc_sides.loc[side, ('usd_size', 'sum')]
                avg = btc_sides.loc[side, ('usd_size', 'mean')]
                side_name = "SHORT liquidations (BUY orders)" if side == 'BUY' else "LONG liquidations (SELL orders)"
                print(f"   📊 {side_name}:")
                print(f"      Count: {count:>8,.0f}")
                print(f"      Total: ${total:>12,.0f}")
                print(f"      Average: ${avg:>10,.2f}")
    
    # 6. DATA QUALITY ISSUES
    print("\n" + "="*50)
    print("🚨 MOON DEV'S DATA QUALITY ISSUES DETECTED 🚨")
    print("="*50)
    
    issues = []
    
    # Check for duplicate timestamps
    duplicate_times = df['datetime'].duplicated().sum()
    if duplicate_times > 0:
        issues.append(f"⚠️ {duplicate_times:,} duplicate timestamps")
    
    # Check for zero/negative prices
    zero_prices = (df['price'] <= 0).sum()
    if zero_prices > 0:
        issues.append(f"⚠️ {zero_prices:,} zero/negative prices")
    
    # Check for tiny liquidations
    tiny_liq = (df['usd_size'] < 1).sum()
    tiny_pct = tiny_liq / len(df) * 100
    if tiny_pct > 5:
        issues.append(f"⚠️ {tiny_liq:,} tiny liquidations (<$1) = {tiny_pct:.1f}%")
    
    # Check for extreme price volatility
    for symbol in symbol_stats.head(20).index:
        symbol_data = df[df['symbol'] == symbol]
        if len(symbol_data) > 100:
            price_cv = symbol_data['price'].std() / symbol_data['price'].mean()
            if price_cv > 0.1:  # Coefficient of variation > 10%
                issues.append(f"⚠️ {symbol} has high price volatility (CV: {price_cv:.3f})")
    
    if issues:
        print("🔥 Data quality issues found:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("✅ No major data quality issues detected!")
    
    # 7. RECOMMENDATIONS
    print("\n" + "="*50)
    print("💡 MOON DEV'S OPTIMIZATION RECOMMENDATIONS 💡")
    print("="*50)
    
    recommendations = []
    
    # BTC percentage check
    if btc_pct < 5:
        recommendations.append("🪙 Consider weighting BTC liquidations higher (only {:.1f}% of data)".format(btc_pct))
    
    # Small liquidation check
    if tiny_pct > 10:
        recommendations.append(f"💰 Filter out liquidations <$10 (removes {tiny_pct:.1f}% noise)")
    
    # Symbol diversity check
    if len(symbol_stats) > 100:
        recommendations.append(f"🎯 Focus on top 50 symbols by volume (current: {len(symbol_stats)} symbols)")
    
    # Temporal aggregation
    recommendations.append("⏰ Try different time windows: 30sec, 5min, 15min aggregations")
    recommendations.append("🔮 Test different prediction horizons: 1min, 3min, 10min ahead")
    recommendations.append("📊 Add volatility-based features (price change velocity)")
    
    if recommendations:
        print("🚀 Recommended optimizations for Moon Dev:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
    
    return df, symbol_stats

# 8. VISUALIZATION
def create_data_visualizations(df, symbol_stats):
    """
    📊 Create Moon Dev's data visualization dashboard
    """
    print("\n📊 Creating Moon Dev's data visualization dashboard... 🌙")
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('🌙 MOON DEV\'S LIQUIDATION DATA ANALYSIS DASHBOARD 🔍', fontsize=16)
    
    # 1. Top symbols by volume
    top_symbols = symbol_stats.head(15)
    axes[0, 0].bar(range(len(top_symbols)), top_symbols['total_usd'] / 1e6)
    axes[0, 0].set_title('💰 Top 15 Symbols by USD Volume (Millions)')
    axes[0, 0].set_xticks(range(len(top_symbols)))
    axes[0, 0].set_xticklabels(top_symbols.index, rotation=45)
    axes[0, 0].set_ylabel('USD Volume (Millions)')
    
    # 2. Liquidation size distribution
    axes[0, 1].hist(np.log10(df['usd_size']), bins=50, alpha=0.7, color='green')
    axes[0, 1].set_title('📊 Liquidation Size Distribution (Log10)')
    axes[0, 1].set_xlabel('Log10(USD Size)')
    axes[0, 1].set_ylabel('Frequency')
    
    # 3. Hourly patterns
    hourly_data = df.groupby('hour')['usd_size'].sum() / 1e6
    axes[0, 2].plot(hourly_data.index, hourly_data.values, marker='o', color='blue')
    axes[0, 2].set_title('⏰ Hourly Liquidation Patterns')
    axes[0, 2].set_xlabel('Hour (UTC)')
    axes[0, 2].set_ylabel('USD Volume (Millions)')
    axes[0, 2].grid(True, alpha=0.3)
    
    # 4. BTC vs Others
    btc_vs_others = df.groupby(df['symbol'] == 'BTC')['usd_size'].sum() / 1e6
    labels = ['Other Cryptos', 'Bitcoin']
    axes[1, 0].pie(btc_vs_others.values, labels=labels, autopct='%1.1f%%', colors=['lightcoral', 'gold'])
    axes[1, 0].set_title('🪙 BTC vs Other Crypto Volume')
    
    # 5. Daily patterns
    daily_data = df.groupby('day_of_week')['usd_size'].sum() / 1e6
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    axes[1, 1].bar(range(7), daily_data.values, color='purple', alpha=0.7)
    axes[1, 1].set_title('📅 Weekly Liquidation Patterns')
    axes[1, 1].set_xticks(range(7))
    axes[1, 1].set_xticklabels(day_names)
    axes[1, 1].set_ylabel('USD Volume (Millions)')
    
    # 6. Side analysis for BTC
    if 'BTC' in df['symbol'].values:
        btc_data = df[df['symbol'] == 'BTC']
        side_counts = btc_data['side'].value_counts()
        axes[1, 2].pie(side_counts.values, labels=side_counts.index, autopct='%1.1f%%', colors=['lightgreen', 'salmon'])
        axes[1, 2].set_title('⚖️ BTC Liquidation Directions')
    
    plt.tight_layout()
    plt.show()
    
    print("🎉 Moon Dev's data analysis complete! 🌙")

if __name__ == "__main__":
    data_path = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data.csv"
    df, symbol_stats = analyze_liquidation_data(data_path)
    create_data_visualizations(df, symbol_stats) 