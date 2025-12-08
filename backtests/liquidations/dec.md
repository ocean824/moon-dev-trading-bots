



12/5- tetsing liq strats

/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/liquidations/pure_liquidation_momentum.py

This one is good:
- 200 unoptimized
- 500 optimized
- Take profit: 1%
- Stop loss: 2%
- Liquidation threshold: $975,000
- Max hold for 2 hours

I think it'd be interesting to combine with looking at people's positions - essentially where they get liquidated - because if we're trading momentum, then we can make sure to only take those trades where there are other pending liquidations.



next idea 
- Find a contrarian liquidation where it's pretty much buying the dip or selling the rip. But then make sure to have a gap of when you enter, so like 0.5%.
    /Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/liquidations/inverse_liquidation_spread.py

Huge. Both strategies above work, and they're exactly opposite, so I can low-key build out a stat arb here,


three bots ready to roll... need to test



12/8- testing 3-5 new liquidation strategies

- Flip flop is the best one so far with a return of 529% vs a buy and hold of 33%.



12/5- finished these three

python -m bots.hyperliquid.liq_momentum_bot


These two are similar but the 2nd has less liq size = more trades, but maybe not. 

python -m bots.hyperliquid.liq_inverse_spread_bot
2,700 trades

python -m bots.hyperliquid.liq_inverse_spread_bot_v2                                                                                                                   
✨ Moon Dev's OPTIMIZED RESULTS:
======================================================================
Start                     2024-06-04 12:50:00
End                       2025-12-05 12:45:00
Duration                    548 days 23:55:00
Exposure Time [%]                   14.996964
Equity Final [$]            1425764197.892908
Equity Peak [$]             1480229664.279406
Return [%]                      142476.419789
Buy & Hold Return [%]               33.251745
Return (Ann.) [%]                 12184.27155
Volatility (Ann.) [%]             5501.980532
Sharpe Ratio                         2.214525
Sortino Ratio                      923.416206
Calmar Ratio                       985.711732
Max. Drawdown [%]                  -12.360887
Avg. Drawdown [%]                    -0.87304
Max. Drawdown Duration       14 days 21:50:00
Avg. Drawdown Duration        0 days 07:01:00
# Trades                                 2338
Win Rate [%]                        65.183918
Best Trade [%]                      29.155453
Worst Trade [%]                     -7.913764
Avg. Trade [%]                        0.32849
Max. Trade Duration           0 days 02:05:00
Avg. Trade Duration           0 days 00:46:00
Profit Factor                         2.68103
Expectancy [%]                       0.334119
SQN                                  9.501118
_strategy                 InverseLiquidati...
_equity_curve                             ...
_trades                          Size  Ent...
dtype: object

🎯 OPTIMIZED PARAMETERS:
--------------------------------------------------
Liquidation Threshold: $300,000
Spread: 1.00%
Take Profit: 1.0%
Stop Loss: 2.0%
Max Hold Hours: 2
