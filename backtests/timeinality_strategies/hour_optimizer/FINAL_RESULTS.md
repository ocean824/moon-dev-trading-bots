# Hour Optimizer Results Analysis

**Generated:** 2025-10-16 10:28:44

This report analyzes the performance of hourly trading strategies across different timeframes and data sources.

## Strategy Overview

| Strategy Type | Description | Total Backtests |
|--------------|-------------|-----------------|
| Short Optimizer | Tests each day-hour combination separately | 3192 |
| Short Combined | Tests each hour on all days combined | 456 |
| Long Optimizer | Tests each day-hour combination separately | 3192 |
| Long Combined | Tests each hour on all days combined | 456 |

---

# Short Optimizer

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

## 🛡️ Top 10 Best Max Drawdown % (Smallest Loss)

| Rank | Data Source | Day | Hour UTC | Max DD % | Return % | Sharpe | Trades | Win Rate % | Profit Factor |
|------|-------------|-----|----------|----------|----------|--------|--------|------------|---------------|
| 1 | BTCUSD-1h-500wks-data_gapped.csv | Tuesday | 09:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 2 | BTCUSD-1h-500wks-data_gapped.csv | Wednesday | 21:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 3 | BTCUSD-1h-500wks-data_gapped.csv | Monday | 09:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 4 | BTCUSD-1h-500wks-data_gapped.csv | Thursday | 21:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 5 | BTCUSD-1h-500wks-data_gapped.csv | Friday | 21:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 6 | BTCUSD-1h-500wks-data_gapped.csv | Saturday | 21:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 7 | BTCUSD-1h-500wks-data_gapped.csv | Sunday | 21:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 8 | BTCUSD-1h-500wks-data_gapped.csv | Wednesday | 09:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 9 | BTCUSD-1h-500wks-data_gapped.csv | Tuesday | 21:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 10 | BTCUSD-1h-500wks-data_gapped.csv | Tuesday | 01:00 | -0.00 | 0.00 | nan | 0 | nan | nan |

---

# Short Combined

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

## 🛡️ Top 10 Best Max Drawdown % (Smallest Loss)

| Rank | Data Source | Days Tested | Hour UTC | Max DD % | Return % | Sharpe | Trades | Win Rate % | Profit Factor |
|------|-------------|-------------|----------|----------|----------|--------|--------|------------|---------------|
| 1 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 23:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 2 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 22:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 3 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 21:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 4 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 13:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 5 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 04:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 6 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 12:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 7 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 11:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 8 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 10:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 9 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 09:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 10 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 08:00 | -0.00 | 0.00 | nan | 0 | nan | nan |

---

# Long Optimizer

## 🏆 Top 10 Highest Return %

| Rank | Data Source | Day | Hour UTC | Return % | Sharpe | Max DD % | Trades | Win Rate % | Profit Factor |
|------|-------------|-----|----------|----------|--------|----------|--------|------------|---------------|
| 1 | BTCUSD-1h-500wks-data_gapped.csv | Friday | 17:00 | 2712.00 | 0.655 | -58.34 | 500 | 64.2 | 1.422 |
| 2 | BTCUSD-1h-500wks-data_gapped.csv | Friday | 18:00 | 2588.44 | 0.659 | -58.71 | 500 | 64.0 | 1.418 |
| 3 | BTCUSD-1h-500wks-data_gapped.csv | Friday | 16:00 | 2493.64 | 0.652 | -63.50 | 500 | 64.4 | 1.415 |
| 4 | BTCUSD-1h-500wks-data_gapped.csv | Friday | 15:00 | 2256.70 | 0.629 | -67.24 | 499 | 64.7 | 1.400 |
| 5 | BTCUSD-1h-500wks-data_gapped.csv | Monday | 19:00 | 1695.98 | 0.727 | -55.03 | 500 | 61.0 | 1.460 |
| 6 | BTCUSD-1h-500wks-data_gapped.csv | Monday | 18:00 | 1689.87 | 0.655 | -59.08 | 500 | 65.8 | 1.388 |
| 7 | BTCUSD-1h-500wks-data_gapped.csv | Monday | 15:00 | 1246.23 | 0.602 | -54.49 | 500 | 65.6 | 1.349 |
| 8 | BTCUSD-1h-500wks-data_gapped.csv | Monday | 17:00 | 1214.58 | 0.626 | -65.62 | 500 | 64.6 | 1.356 |
| 9 | BTCUSD-1h-500wks-data_gapped.csv | Monday | 16:00 | 1023.73 | 0.569 | -62.87 | 500 | 64.8 | 1.330 |
| 10 | BTCUSD-1h-500wks-data_gapped.csv | Wednesday | 15:00 | 984.77 | 0.552 | -62.63 | 500 | 63.2 | 1.330 |

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

## 🛡️ Top 10 Best Max Drawdown % (Smallest Loss)

| Rank | Data Source | Day | Hour UTC | Max DD % | Return % | Sharpe | Trades | Win Rate % | Profit Factor |
|------|-------------|-----|----------|----------|----------|--------|--------|------------|---------------|
| 1 | BTCUSD-1h-500wks-data_gapped.csv | Wednesday | 08:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 2 | BTCUSD-1h-500wks-data_gapped.csv | Saturday | 03:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 3 | BTCUSD-1h-500wks-data_gapped.csv | Tuesday | 08:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 4 | BTCUSD-1h-500wks-data_gapped.csv | Thursday | 06:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 5 | BTCUSD-1h-500wks-data_gapped.csv | Tuesday | 05:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 6 | BTCUSD-1h-500wks-data_gapped.csv | Wednesday | 05:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 7 | BTCUSD-1h-500wks-data_gapped.csv | Thursday | 05:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 8 | BTCUSD-1h-500wks-data_gapped.csv | Friday | 05:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 9 | BTCUSD-1h-500wks-data_gapped.csv | Saturday | 05:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 10 | BTCUSD-1h-500wks-data_gapped.csv | Sunday | 05:00 | -0.00 | 0.00 | nan | 0 | nan | nan |

---

# Long Combined

## 🏆 Top 10 Highest Return %

| Rank | Data Source | Days Tested | Hour UTC | Return % | Sharpe | Max DD % | Trades | Win Rate % | Profit Factor |
|------|-------------|-------------|----------|----------|--------|----------|--------|------------|---------------|
| 1 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 17:00 | 34407.96 | 0.679 | -85.30 | 2499 | 55.3 | 1.256 |
| 2 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 18:00 | 29143.53 | 0.676 | -82.68 | 2500 | 55.2 | 1.249 |
| 3 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 15:00 | 28446.55 | 0.678 | -75.85 | 2498 | 55.3 | 1.252 |
| 4 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 16:00 | 19423.53 | 0.626 | -82.78 | 2500 | 54.8 | 1.236 |
| 5 | BTCUSD-1h-500wks-data_inverse_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 13:00 | 1875.80 | 0.386 | -96.16 | 3497 | 55.6 | 1.194 |
| 6 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 14:00 | 1624.70 | 0.506 | -54.24 | 1588 | 55.5 | 1.217 |
| 7 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 19:00 | 1488.95 | 0.424 | -88.92 | 2499 | 52.1 | 1.170 |
| 8 | BTCUSD-1h-500wks-data_inverse_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 04:00 | 674.16 | 0.270 | -95.24 | 3497 | 56.4 | 1.156 |
| 9 | BTCUSD-1h-500wks-data_inverse_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 21:00 | 669.80 | 0.275 | -95.24 | 3498 | 56.6 | 1.157 |
| 10 | BTCUSD-1h-500wks-data_inverse_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 12:00 | 616.85 | 0.254 | -96.31 | 3499 | 55.5 | 1.154 |

## 📊 Top 10 Highest Sharpe Ratio

| Rank | Data Source | Days Tested | Hour UTC | Sharpe | Return % | Max DD % | Trades | Win Rate % | Profit Factor |
|------|-------------|-------------|----------|--------|----------|----------|--------|------------|---------------|
| 1 | J3NKxxXZcnNiMjKw9hYb2K4LUxgwB6t1FtPtQVsv3KFr-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 15:00 | 1.301 | 33.47 | -12.61 | 42 | 71.4 | 1.593 |
| 2 | J3NKxxXZcnNiMjKw9hYb2K4LUxgwB6t1FtPtQVsv3KFr-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 16:00 | 1.249 | 37.42 | -13.05 | 42 | 73.8 | 1.651 |
| 3 | JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 02:00 | 1.223 | 22.07 | -19.81 | 42 | 61.9 | 1.433 |
| 4 | JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 21:00 | 1.206 | 31.74 | -13.64 | 42 | 71.4 | 1.584 |
| 5 | J3NKxxXZcnNiMjKw9hYb2K4LUxgwB6t1FtPtQVsv3KFr-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 14:00 | 1.173 | 23.79 | -15.15 | 41 | 70.7 | 1.416 |
| 6 | BTCUSD-1h-100wks-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 13:00 | 1.154 | 272.93 | -24.52 | 699 | 55.1 | 1.288 |
| 7 | J3NKxxXZcnNiMjKw9hYb2K4LUxgwB6t1FtPtQVsv3KFr-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 13:00 | 1.142 | 23.79 | -15.66 | 41 | 70.7 | 1.416 |
| 8 | DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 11:00 | 1.136 | 26.25 | -14.67 | 41 | 68.3 | 1.510 |
| 9 | 2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv-1H-300days-data.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 14:00 | 1.127 | 23.79 | -17.83 | 41 | 70.7 | 1.416 |
| 10 | 2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv-1H-300days-data copy.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 14:00 | 1.127 | 23.79 | -17.83 | 41 | 70.7 | 1.416 |

## 🛡️ Top 10 Best Max Drawdown % (Smallest Loss)

| Rank | Data Source | Days Tested | Hour UTC | Max DD % | Return % | Sharpe | Trades | Win Rate % | Profit Factor |
|------|-------------|-------------|----------|----------|----------|--------|--------|------------|---------------|
| 1 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 10:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 2 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 12:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 3 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 00:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 4 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 01:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 5 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 02:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 6 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 03:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 7 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 04:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 8 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 05:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 9 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 06:00 | -0.00 | 0.00 | nan | 0 | nan | nan |
| 10 | BTCUSD-1h-500wks-data_gapped.csv | Mon,Tue,Wed,Thu,Fri,Sat,Sun | 07:00 | -0.00 | 0.00 | nan | 0 | nan | nan |

---

# Summary Statistics

## Overall Performance by Strategy Type

| Strategy | Avg Return % | Median Return % | Best Return % | Worst Return % | Avg Sharpe | Avg Max DD % |
|----------|--------------|-----------------|---------------|----------------|------------|-------------|
| Short Optimizer | -10.22 | -6.23 | 257.70 | -98.32 | 0.399 | -27.76 |
| Short Combined | -29.05 | -27.15 | 201.77 | -99.51 | 0.173 | -50.44 |
| Long Optimizer | 4.11 | -2.20 | 2712.00 | -95.27 | 0.363 | -27.42 |
| Long Combined | 248.99 | -13.52 | 34407.96 | -97.93 | 0.155 | -50.06 |

---

*Analysis completed by Moon Dev's Hour Optimizer Results Analyzer 🌙*
