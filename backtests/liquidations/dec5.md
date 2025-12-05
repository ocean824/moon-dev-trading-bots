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