# Hour Optimizer Results Analysis (NO BTC)

**Generated:** 2025-10-16 10:24:03

**Important:** This analysis EXCLUDES all Bitcoin (BTC) data from ALL strategies (both LONG and SHORT).
- All BTCUSD files filtered out to see performance on altcoins, stocks, forex, and other assets

This report analyzes the performance of hourly trading strategies across different timeframes and data sources.

## Strategy Overview

| Strategy Type | Description | Total Backtests | Note |
|--------------|-------------|-----------------|------|
| Short Optimizer | Tests each day-hour combination separately | 2688 | NO BTC |
| Short Combined | Tests each hour on all days combined | 384 | NO BTC |
| Long Optimizer | Tests each day-hour combination separately | 2688 | NO BTC |
| Long Combined | Tests each hour on all days combined | 384 | NO BTC |

---

# Short Optimizer

**Note:** Bitcoin (BTC) data excluded from this analysis.

## 🏆 Top 10 Highest Return %

| Rank | Data Source | Day | Hour UTC | Return % | Sharpe | Max DD % | Trades | Win Rate % | Profit Factor |
|------|-------------|-----|----------|----------|--------|----------|--------|------------|---------------|
| 1 | SOLUSD-1h-250wks-data.csv | Tuesday | 11:00 | 257.70 | 1.019 | -23.38 | 218 | 71.6 | 1.474 |
| 2 | SOLUSD-1h-250wks-data.csv | Thursday | 11:00 | 229.36 | 0.944 | -26.01 | 218 | 71.1 | 1.439 |
| 3 | SUIUSD-1h-52wks-data.csv | Monday | 07:00 | 146.44 | 2.397 | -10.91 | 52 | 86.5 | 3.763 |
| 4 | SOLUSD-1h-250wks-data.csv | Thursday | 10:00 | 124.53 | 0.666 | -28.28 | 218 | 68.8 | 1.291 |
| 5 | SOLUSD-1h-250wks-data.csv | Tuesday | 13:00 | 123.95 | 0.652 | -26.87 | 218 | 68.8 | 1.290 |
| 6 | ETHUSD-1h-250wks-data.csv | Sunday | 09:00 | 122.11 | 0.591 | -39.40 | 250 | 67.6 | 1.257 |
| 7 | SOLUSD-1h-250wks-data.csv | Thursday | 12:00 | 109.27 | 0.617 | -31.21 | 218 | 68.3 | 1.266 |
| 8 | SOLUSD-1h-250wks-data.csv | Tuesday | 12:00 | 108.53 | 0.610 | -23.84 | 218 | 68.3 | 1.264 |
| 9 | SOLUSD-1h-250wks-data.csv | Sunday | 22:00 | 108.07 | 0.615 | -31.79 | 218 | 68.3 | 1.264 |
| 10 | SOLUSD-1h-250wks-data.csv | Tuesday | 09:00 | 101.40 | 0.566 | -37.95 | 218 | 67.9 | 1.253 |

## 📊 Top 10 Highest Sharpe Ratio

| Rank | Data Source | Day | Hour UTC | Sharpe | Return % | Max DD % | Trades | Win Rate % | Profit Factor |
|------|-------------|-----|----------|--------|----------|----------|--------|------------|---------------|
| 1 | DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263-1H-300days-data.csv | Tuesday | 18:00 | 4.524 | 18.08 | -1.65 | 6 | 100.0 | nan |
| 2 | 2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv-1H-300days-data.csv | Thursday | 16:00 | 4.214 | 18.08 | -4.00 | 6 | 100.0 | nan |
| 3 | 2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv-1H-300days-data copy.csv | Thursday | 16:00 | 4.214 | 18.08 | -4.00 | 6 | 100.0 | nan |
| 4 | JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN-1H-300days-data.csv | Sunday | 00:00 | 4.171 | 18.08 | -2.48 | 6 | 100.0 | nan |
| 5 | 2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv-1H-300days-data.csv | Thursday | 11:00 | 4.171 | 18.08 | -3.14 | 6 | 100.0 | nan |
| 6 | 2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv-1H-300days-data copy.csv | Thursday | 11:00 | 4.171 | 18.08 | -3.14 | 6 | 100.0 | nan |
| 7 | ED5nyyWEzpPPiWimP8vYm7sD7TD3LAt3Q3gRTWHzPJBY-1H-300days-data.csv | Thursday | 18:00 | 4.168 | 18.08 | -1.35 | 6 | 100.0 | nan |
| 8 | JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN-1H-300days-data.csv | Sunday | 07:00 | 4.163 | 18.08 | -2.88 | 6 | 100.0 | nan |
| 9 | 2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv-1H-300days-data.csv | Sunday | 18:00 | 4.103 | 18.08 | -0.92 | 6 | 100.0 | nan |
| 10 | 2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv-1H-300days-data copy.csv | Sunday | 18:00 | 4.103 | 18.08 | -0.92 | 6 | 100.0 | nan |

## 🛡️ Top 10 Lowest Max Drawdown %

| Rank | Data Source | Day | Hour UTC | Max DD % | Return % | Sharpe | Trades | Win Rate % | Profit Factor |
|------|-------------|-----|----------|----------|----------|--------|--------|------------|---------------|
| 1 | ETHUSD-1h-250wks-data.csv | Wednesday | 05:00 | -85.31 | -84.64 | 0.000 | 250 | 53.6 | 0.685 |
| 2 | ETHUSD-1h-250wks-data.csv | Wednesday | 07:00 | -82.52 | -80.28 | 0.000 | 250 | 55.2 | 0.727 |
| 3 | SOLUSD-1h-250wks-data.csv | Saturday | 01:00 | -80.71 | -78.72 | 0.000 | 219 | 54.8 | 0.709 |
| 4 | ETHUSD-1h-250wks-data.csv | Monday | 02:00 | -80.31 | -77.93 | 0.000 | 250 | 56.0 | 0.744 |
| 5 | SOLUSD-1h-250wks-data.csv | Friday | 23:00 | -77.66 | -73.98 | 0.000 | 219 | 55.7 | 0.743 |
| 6 | ETHUSD-1h-250wks-data.csv | Wednesday | 03:00 | -77.47 | -75.21 | 0.000 | 250 | 56.8 | 0.760 |
| 7 | ETHUSD-1h-250wks-data.csv | Wednesday | 01:00 | -77.15 | -74.24 | 0.000 | 250 | 56.8 | 0.768 |
| 8 | ETHUSD-1h-250wks-data.csv | Wednesday | 06:00 | -76.61 | -74.26 | 0.000 | 250 | 56.4 | 0.767 |
| 9 | ETHUSD-1h-250wks-data.csv | Friday | 11:00 | -76.61 | -72.86 | 0.000 | 250 | 56.4 | 0.776 |
| 10 | SOLUSD-1h-250wks-data.csv | Friday | 16:00 | -75.65 | -71.13 | 0.000 | 219 | 56.6 | 0.763 |

---

# Short Combined

**Note:** Bitcoin (BTC) data excluded from this analysis.

## 🏆 Top 10 Highest Return %

| Rank | Data Source | Days Tested | Hour UTC | Return % | Sharpe | Max DD % | Trades | Win Rate % | Profit Factor |
|------|-------------|-------------|----------|----------|--------|----------|--------|------------|---------------|
| 1 | SUIUSD-1h-52wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 06:00 | 201.77 | 0.978 | -33.18 | 364 | 64.3 | 1.278 |
| 2 | SUIUSD-1h-52wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 09:00 | 180.48 | 0.970 | -19.13 | 364 | 63.2 | 1.259 |
| 3 | SOLUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 11:00 | 154.67 | 0.302 | -53.19 | 1528 | 59.6 | 1.081 |
| 4 | SUIUSD-1h-52wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 07:00 | 139.77 | 0.868 | -27.57 | 364 | 62.9 | 1.221 |
| 5 | SOLUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 10:00 | 139.68 | 0.285 | -60.90 | 1528 | 59.6 | 1.078 |
| 6 | LTCUSD-1h-52wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 09:00 | 102.16 | 0.872 | -25.52 | 364 | 57.7 | 1.199 |
| 7 | HBARUSD-1h-52wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 12:00 | 88.86 | 0.724 | -41.30 | 364 | 59.6 | 1.170 |
| 8 | SUIUSD-1h-52wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 10:00 | 87.68 | 0.712 | -30.21 | 364 | 62.1 | 1.166 |
| 9 | SUIUSD-1h-52wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 05:00 | 80.72 | 0.669 | -39.55 | 364 | 60.7 | 1.155 |
| 10 | 2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv-1H-300days-data copy.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 06:00 | 68.36 | 1.595 | -9.36 | 41 | 80.5 | 2.416 |

## 📊 Top 10 Highest Sharpe Ratio

| Rank | Data Source | Days Tested | Hour UTC | Sharpe | Return % | Max DD % | Trades | Win Rate % | Profit Factor |
|------|-------------|-------------|----------|--------|----------|----------|--------|------------|---------------|
| 1 | 2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv-1H-300days-data copy.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 06:00 | 1.595 | 68.36 | -9.36 | 41 | 80.5 | 2.416 |
| 2 | 2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 06:00 | 1.595 | 68.36 | -9.36 | 41 | 80.5 | 2.416 |
| 3 | ED5nyyWEzpPPiWimP8vYm7sD7TD3LAt3Q3gRTWHzPJBY-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 20:00 | 1.560 | 37.26 | -10.74 | 42 | 71.4 | 1.678 |
| 4 | 2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 07:00 | 1.447 | 55.91 | -14.07 | 41 | 78.0 | 2.083 |
| 5 | 2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv-1H-300days-data copy.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 07:00 | 1.447 | 55.91 | -14.07 | 41 | 78.0 | 2.083 |
| 6 | 2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 11:00 | 1.438 | 44.38 | -11.65 | 41 | 75.6 | 1.816 |
| 7 | 2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv-1H-300days-data copy.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 11:00 | 1.438 | 44.38 | -11.65 | 41 | 75.6 | 1.816 |
| 8 | 2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv-1H-300days-data copy.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 05:00 | 1.405 | 45.64 | -11.47 | 41 | 75.6 | 1.816 |
| 9 | 2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 05:00 | 1.405 | 45.64 | -11.47 | 41 | 75.6 | 1.816 |
| 10 | 2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv-1H-300days-data copy.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 03:00 | 1.405 | 45.49 | -15.08 | 42 | 76.2 | 1.832 |

## 🛡️ Top 10 Lowest Max Drawdown %

| Rank | Data Source | Days Tested | Hour UTC | Max DD % | Return % | Sharpe | Trades | Win Rate % | Profit Factor |
|------|-------------|-------------|----------|----------|----------|--------|--------|------------|---------------|
| 1 | ETHUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 07:00 | -96.57 | -96.47 | 0.000 | 1750 | 51.7 | 0.877 |
| 2 | ETHUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 03:00 | -96.57 | -96.46 | 0.000 | 1750 | 51.1 | 0.877 |
| 3 | ETHUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 06:00 | -96.21 | -96.03 | 0.000 | 1750 | 51.9 | 0.882 |
| 4 | ETHUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 17:00 | -96.12 | -95.66 | 0.000 | 1750 | 52.3 | 0.885 |
| 5 | ETHUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 20:00 | -95.73 | -95.42 | 0.000 | 1749 | 51.9 | 0.888 |
| 6 | SOLUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 15:00 | -95.59 | -92.52 | 0.000 | 1527 | 56.7 | 0.922 |
| 7 | ETHUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 04:00 | -95.57 | -95.20 | 0.000 | 1750 | 51.8 | 0.889 |
| 8 | ETHUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 02:00 | -95.48 | -95.32 | 0.000 | 1750 | 51.9 | 0.889 |
| 9 | ETHUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 05:00 | -95.35 | -95.03 | 0.000 | 1750 | 51.4 | 0.890 |
| 10 | ETHUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 16:00 | -95.22 | -94.68 | 0.000 | 1750 | 52.7 | 0.894 |

---

# Long Optimizer

**Note:** Bitcoin (BTC) data excluded from this analysis.

## 🏆 Top 10 Highest Return %

| Rank | Data Source | Day | Hour UTC | Return % | Sharpe | Max DD % | Trades | Win Rate % | Profit Factor |
|------|-------------|-----|----------|----------|--------|----------|--------|------------|---------------|
| 1 | ZECUSD-1h-52wks-data.csv | Saturday | 16:00 | 148.07 | 2.497 | -10.83 | 52 | 86.5 | 3.751 |
| 2 | ZECUSD-1h-52wks-data.csv | Saturday | 15:00 | 112.14 | 2.117 | -14.38 | 52 | 82.7 | 2.849 |
| 3 | ZECUSD-1h-52wks-data.csv | Saturday | 13:00 | 109.46 | 2.127 | -17.11 | 52 | 82.7 | 2.725 |
| 4 | ZECUSD-1h-52wks-data.csv | Saturday | 18:00 | 108.48 | 2.241 | -10.93 | 52 | 82.7 | 2.759 |
| 5 | SOLUSD-1h-250wks-data.csv | Friday | 22:00 | 98.95 | 0.564 | -34.84 | 219 | 68.0 | 1.247 |
| 6 | ZECUSD-1h-52wks-data.csv | Saturday | 14:00 | 97.22 | 2.078 | -15.87 | 52 | 80.8 | 2.495 |
| 7 | ZECUSD-1h-52wks-data.csv | Saturday | 17:00 | 97.15 | 2.062 | -10.38 | 52 | 80.8 | 2.463 |
| 8 | ZECUSD-1h-52wks-data.csv | Saturday | 11:00 | 96.64 | 2.023 | -15.49 | 52 | 80.8 | 2.473 |
| 9 | SOLUSD-1h-250wks-data.csv | Friday | 16:00 | 90.38 | 0.531 | -36.30 | 219 | 67.6 | 1.232 |
| 10 | ETHUSD-1h-250wks-data.csv | Sunday | 02:00 | 85.76 | 0.453 | -36.13 | 250 | 66.8 | 1.203 |

## 📊 Top 10 Highest Sharpe Ratio

| Rank | Data Source | Day | Hour UTC | Sharpe | Return % | Max DD % | Trades | Win Rate % | Profit Factor |
|------|-------------|-----|----------|--------|----------|----------|--------|------------|---------------|
| 1 | ED5nyyWEzpPPiWimP8vYm7sD7TD3LAt3Q3gRTWHzPJBY-1H-300days-data.csv | Friday | 03:00 | 3.962 | 15.15 | -3.49 | 6 | 100.0 | nan |
| 2 | J3NKxxXZcnNiMjKw9hYb2K4LUxgwB6t1FtPtQVsv3KFr-1H-300days-data.csv | Saturday | 06:00 | 3.960 | 18.06 | -4.28 | 6 | 100.0 | nan |
| 3 | J3NKxxXZcnNiMjKw9hYb2K4LUxgwB6t1FtPtQVsv3KFr-1H-300days-data.csv | Saturday | 03:00 | 3.960 | 18.06 | -3.50 | 6 | 100.0 | nan |
| 4 | J3NKxxXZcnNiMjKw9hYb2K4LUxgwB6t1FtPtQVsv3KFr-1H-300days-data.csv | Wednesday | 04:00 | 3.960 | 18.06 | -2.88 | 6 | 100.0 | nan |
| 5 | J3NKxxXZcnNiMjKw9hYb2K4LUxgwB6t1FtPtQVsv3KFr-1H-300days-data.csv | Wednesday | 02:00 | 3.960 | 18.06 | -0.00 | 6 | 100.0 | nan |
| 6 | J3NKxxXZcnNiMjKw9hYb2K4LUxgwB6t1FtPtQVsv3KFr-1H-300days-data.csv | Monday | 13:00 | 3.960 | 18.06 | -2.01 | 6 | 100.0 | nan |
| 7 | J3NKxxXZcnNiMjKw9hYb2K4LUxgwB6t1FtPtQVsv3KFr-1H-300days-data.csv | Wednesday | 01:00 | 3.960 | 18.06 | -1.31 | 6 | 100.0 | nan |
| 8 | J3NKxxXZcnNiMjKw9hYb2K4LUxgwB6t1FtPtQVsv3KFr-1H-300days-data.csv | Saturday | 08:00 | 3.960 | 18.06 | -3.44 | 6 | 100.0 | nan |
| 9 | J3NKxxXZcnNiMjKw9hYb2K4LUxgwB6t1FtPtQVsv3KFr-1H-300days-data.csv | Wednesday | 03:00 | 3.960 | 18.06 | -3.29 | 6 | 100.0 | nan |
| 10 | J3NKxxXZcnNiMjKw9hYb2K4LUxgwB6t1FtPtQVsv3KFr-1H-300days-data.csv | Saturday | 05:00 | 3.960 | 18.06 | -3.27 | 6 | 100.0 | nan |

## 🛡️ Top 10 Lowest Max Drawdown %

| Rank | Data Source | Day | Hour UTC | Max DD % | Return % | Sharpe | Trades | Win Rate % | Profit Factor |
|------|-------------|-----|----------|----------|----------|--------|--------|------------|---------------|
| 1 | SOLUSD-1h-250wks-data.csv | Wednesday | 10:00 | -80.06 | -69.45 | 0.000 | 218 | 56.9 | 0.772 |
| 2 | SOLUSD-1h-250wks-data.csv | Tuesday | 08:00 | -78.87 | -69.34 | 0.000 | 218 | 56.9 | 0.773 |
| 3 | SOLUSD-1h-250wks-data.csv | Tuesday | 16:00 | -78.25 | -73.52 | 0.000 | 218 | 56.0 | 0.746 |
| 4 | SOLUSD-1h-250wks-data.csv | Saturday | 22:00 | -77.86 | -68.59 | 0.000 | 218 | 56.9 | 0.777 |
| 5 | SOLUSD-1h-250wks-data.csv | Sunday | 20:00 | -76.86 | -63.95 | 0.000 | 218 | 57.8 | 0.804 |
| 6 | SOLUSD-1h-250wks-data.csv | Thursday | 20:00 | -76.75 | -58.09 | 0.000 | 219 | 58.9 | 0.834 |
| 7 | SOLUSD-1h-250wks-data.csv | Tuesday | 12:00 | -75.86 | -71.23 | 0.000 | 218 | 56.4 | 0.761 |
| 8 | SOLUSD-1h-250wks-data.csv | Sunday | 12:00 | -75.74 | -63.84 | 0.000 | 218 | 57.8 | 0.805 |
| 9 | SOLUSD-1h-250wks-data.csv | Thursday | 08:00 | -75.33 | -69.19 | 0.000 | 218 | 56.9 | 0.774 |
| 10 | ETHUSD-1h-250wks-data.csv | Thursday | 00:00 | -74.67 | -58.38 | 0.000 | 250 | 58.4 | 0.850 |

---

# Long Combined

**Note:** Bitcoin (BTC) data excluded from this analysis.

## 🏆 Top 10 Highest Return %

| Rank | Data Source | Days Tested | Hour UTC | Return % | Sharpe | Max DD % | Trades | Win Rate % | Profit Factor |
|------|-------------|-------------|----------|----------|--------|----------|--------|------------|---------------|
| 1 | ZECUSD-1h-52wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 23:00 | 86.51 | 0.695 | -39.56 | 364 | 62.1 | 1.163 |
| 2 | ZECUSD-1h-52wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 07:00 | 69.52 | 0.615 | -43.11 | 364 | 61.8 | 1.140 |
| 3 | ADAUSD-1h-52wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 23:00 | 63.46 | 0.623 | -51.20 | 364 | 59.9 | 1.143 |
| 4 | DOGEUSD-1h-52wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 19:00 | 59.10 | 0.523 | -50.64 | 364 | 61.3 | 1.132 |
| 5 | ADAUSD-1h-52wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 00:00 | 57.08 | 0.569 | -33.66 | 364 | 60.2 | 1.132 |
| 6 | ZECUSD-1h-52wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 22:00 | 38.51 | 0.405 | -44.22 | 364 | 61.0 | 1.100 |
| 7 | DOGEUSD-1h-52wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 21:00 | 37.82 | 0.387 | -37.81 | 364 | 60.4 | 1.101 |
| 8 | J3NKxxXZcnNiMjKw9hYb2K4LUxgwB6t1FtPtQVsv3KFr-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 16:00 | 37.42 | 1.249 | -13.05 | 42 | 73.8 | 1.651 |
| 9 | LINKUSD-1h-52wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 00:00 | 36.08 | 0.408 | -39.83 | 364 | 59.6 | 1.098 |
| 10 | LINKUSD-1h-52wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 08:00 | 34.94 | 0.404 | -47.58 | 364 | 58.5 | 1.097 |

## 📊 Top 10 Highest Sharpe Ratio

| Rank | Data Source | Days Tested | Hour UTC | Sharpe | Return % | Max DD % | Trades | Win Rate % | Profit Factor |
|------|-------------|-------------|----------|--------|----------|----------|--------|------------|---------------|
| 1 | J3NKxxXZcnNiMjKw9hYb2K4LUxgwB6t1FtPtQVsv3KFr-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 15:00 | 1.301 | 33.47 | -12.61 | 42 | 71.4 | 1.593 |
| 2 | J3NKxxXZcnNiMjKw9hYb2K4LUxgwB6t1FtPtQVsv3KFr-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 16:00 | 1.249 | 37.42 | -13.05 | 42 | 73.8 | 1.651 |
| 3 | JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 02:00 | 1.223 | 22.07 | -19.81 | 42 | 61.9 | 1.433 |
| 4 | JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 21:00 | 1.206 | 31.74 | -13.64 | 42 | 71.4 | 1.584 |
| 5 | J3NKxxXZcnNiMjKw9hYb2K4LUxgwB6t1FtPtQVsv3KFr-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 14:00 | 1.173 | 23.79 | -15.15 | 41 | 70.7 | 1.416 |
| 6 | J3NKxxXZcnNiMjKw9hYb2K4LUxgwB6t1FtPtQVsv3KFr-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 13:00 | 1.142 | 23.79 | -15.66 | 41 | 70.7 | 1.416 |
| 7 | DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 11:00 | 1.136 | 26.25 | -14.67 | 41 | 68.3 | 1.510 |
| 8 | 2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 14:00 | 1.127 | 23.79 | -17.83 | 41 | 70.7 | 1.416 |
| 9 | 2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv-1H-300days-data copy.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 14:00 | 1.127 | 23.79 | -17.83 | 41 | 70.7 | 1.416 |
| 10 | ED5nyyWEzpPPiWimP8vYm7sD7TD3LAt3Q3gRTWHzPJBY-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 01:00 | 1.122 | 21.00 | -21.97 | 42 | 66.7 | 1.377 |

## 🛡️ Top 10 Lowest Max Drawdown %

| Rank | Data Source | Days Tested | Hour UTC | Max DD % | Return % | Sharpe | Trades | Win Rate % | Profit Factor |
|------|-------------|-------------|----------|----------|----------|--------|--------|------------|---------------|
| 1 | SOLUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 10:00 | -98.32 | -97.93 | 0.000 | 1528 | 53.3 | 0.867 |
| 2 | SOLUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 12:00 | -97.91 | -96.73 | 0.000 | 1528 | 54.6 | 0.885 |
| 3 | SOLUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 15:00 | -96.36 | -93.10 | 0.000 | 1527 | 55.5 | 0.917 |
| 4 | SOLUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 04:00 | -96.29 | -96.13 | 0.000 | 1528 | 54.2 | 0.893 |
| 5 | SOLUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 16:00 | -96.22 | -92.62 | 0.000 | 1527 | 55.6 | 0.921 |
| 6 | SOLUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 20:00 | -96.16 | -93.93 | 0.000 | 1527 | 54.7 | 0.913 |
| 7 | SOLUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 09:00 | -95.99 | -95.03 | 0.000 | 1528 | 54.7 | 0.901 |
| 8 | SOLUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 21:00 | -95.92 | -92.93 | 0.000 | 1527 | 55.0 | 0.919 |
| 9 | SOLUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 11:00 | -95.90 | -94.08 | 0.000 | 1528 | 54.6 | 0.909 |
| 10 | SOLUSD-1h-250wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 02:00 | -95.18 | -94.70 | 0.000 | 1528 | 54.9 | 0.906 |

---

# Summary Statistics

## Overall Performance by Strategy Type

| Strategy | Avg Return % | Median Return % | Best Return % | Worst Return % | Avg Sharpe | Avg Max DD % | Data Note |
|----------|--------------|-----------------|---------------|----------------|------------|-------------|----------|
| Short Optimizer | -4.50 | -2.05 | 257.70 | -84.64 | 0.451 | -23.91 | NO BTC |
| Short Combined | -22.28 | -22.00 | 201.77 | -96.47 | 0.198 | -47.18 | NO BTC |
| Long Optimizer | -5.26 | -6.22 | 148.07 | -73.52 | 0.369 | -25.20 | NO BTC |
| Long Combined | -24.85 | -19.16 | 86.51 | -97.93 | 0.111 | -49.99 | NO BTC |

---

*Analysis completed by Moon Dev's Hour Optimizer Results Analyzer (NO BTC) 🌙*
