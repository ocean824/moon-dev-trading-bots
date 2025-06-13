# Machine Learning for BTC Liquidation Trading 🚀

## 🎯 Goal
Use tick-level liquidation data to forecast very short-term BTC price moves and execute intraday trades.
- we have data for all symbols, so this can be any symbol really

## 🤖 Best ML Models

### 1. LSTM / GRU (Recurrent Neural Networks)
- **Strength:** Excels at detecting sequential patterns in order flow
- **Use case:** Time series analysis of liquidation sequences

### 2. CNN / DeepLOB-style Convolutional Networks  
- **Strength:** Detects local "spikes/clusters" of liquidations that precede price moves
- **Use case:** Pattern recognition in liquidation event clustering

### 3. Gradient-Boosted Trees (XGBoost/LightGBM)
- **Strength:** Strong performance on engineered tabular features
- **Advantages:** Fast training, interpretable results

### 4. LSTM, CNN, and XGBoost into a "super model"

## 📊 Feature Engineering Ideas

**Time Windows:** Per-second or 5-minute aggregations
- any time frame

**Key Features:**
- Counts and volume of buy vs. sell liquidations
- Notional size of liquidation events
- Largest single liquidation event
- Recent price returns
- Time since last liquidation spike
- Liquidation-to-volume ratios

## 🎯 Backtesting Realism Requirements

**Critical:** Always include realistic trading costs
- Bid-ask spread impact
- Slippage assumptions
- Assume entry 1-2 ticks worse than liquidation price
- Account for market impact on larger trades

## 🛡️ Overfitting Prevention & Risk Management

### Model Regularization
- Use dropout layers and depth limits
- Apply L1/L2 regularization
- Implement purged walk-forward cross-validation

### Entry Buffers
- Require small delay before entry
- Wait for confirming uptick/signal
- Train labels that account for trading costs (predict moves > fees)

## 💡 Key Execution Insight

**The Real Test:** If your edge survives realistic slippage, costs, and modest buffering delays, then the alpha is likely genuine and tradeable. 

**Otherwise:** You're just capturing the untradeable liquidation tick itself, which won't work in live trading.

---
*Remember: The goal isn't just to predict liquidation events, but to predict profitable trades AFTER accounting for all real-world trading costs.*


---

### Notes
- "What's the probability of a 0.5% move? - predict this
- KPIs
    RMSE (Root Mean Square Error)     # Penalizes large errors heavily
    MAE (Mean Absolute Error)         # Average prediction error
    R² (R-squared)                    # How much variance explained
    MAPE (Mean Absolute % Error)  
- Lambda Labs for faster Model training:
    - labda labs 
    💰 COST COMPARISON:
            Your Current Setup: 25 hours × FREE = $0 (but 25 hours!)
            Lambda Options:
            8x H100: ~$24 total, 1 hour ⚡
            8x A100: ~$18 total, 1.5 hours 🚀
            4x H100: ~$30 total, 2.5 hours 💪
    ⭐️ Go with the 1x A6000 at ~$5 total cost and ~5 hours training!
        You're basically paying $5 to get 20 hours of your life back - that's incredible value! 🌙💰
    🔥 when i need super speed: 8x A100: ~$18 total, 1.5 hours 🚀
- before moving to lambda, run on my comp to see if looking good. below is how to skinny up the runs to test on comp
    - in my code have LOCAL_MODE = True for local runs to test fast, and false when in cloud 
    - SAMPLE_FRACTION = .1 if LOCAL_MODE else 1.0 # reduces the amount of data in order to train faster
    # Smaller LSTM for local testing
    LSTM_UNITS_1 = 64 if LOCAL_MODE else 128
    LSTM_UNITS_2 = 32 if LOCAL_MODE else 64
    LSTM_UNITS_3 = 16 if LOCAL_MODE else 32
    EPOCHS = 5 if LOCAL_MODE else 25
    BATCH_SIZE = 32 if LOCAL_MODE else 64
- WHAT TO LOOK FOR IN LOCAL TESTING:
    ✅ Green Flags (Go to Lambda!):
    Loss decreasing steadily (6.0 → 4.0 → 2.0 → 1.5...)
    Validation loss following training loss (not wildly different)
    MAE under 2.0 by end of training
    No crashes or infinite values
    Model actually learns patterns (better than random guessing)
    🚨 Red Flags (Fix before Lambda!):
    Loss stuck/increasing (6.0 → 6.2 → 6.5...)
    Validation loss exploding (overfitting)
    MAE stays high (>3.0 throughout)
    Crashes or memory errors
    Model predicts same value for everything
- do some data cleaning to only keep big symbols, cutting up this data will make it a new data set, and a new idea. unlimited things to test. 
- Training loss drops, validation loss shoots up = Overfitting!
- models to test: GRU, Temporal Convolution Network, 
    - o3: Run a Modern TCN, a TimesNet/Informer Transformer, a Residual CycleNet, a LightGBM baseline, and a hybrid TCCT convolution-transformer model next.
    - sonnet4: Run Random Forest first (quick interpretable baseline), then XGBoost (feature importance master), then Transformer/Attention (pattern detection), then CNN-LSTM hybrid (cascade detection) - in that order. 🚀🌙

Todo to improve models
- mixing small liquidations amounts like < $5 makes a lot of noise which can hurt models
- too many symbols may drown things out
- liquidations happen in Miliseconds and we are sampling into 1-minute... we may be missing some things. 
- i made a results page, and working from there... 
- test cleaning up features to not have so many, just a couple, see how it changes things. 
- build a hybrid
- random forest trees do not need to be more than 300, max 500 but most research indicates that 300 is fine
- same features from RF usuuauly work well in LSTM, so i can test there faster
- AOC > 0.6 has some edge
- AUC is good for filtering trash (like eliminating anything < 0.55), but accuracy is king for actual trading




6/13-
-Your original 1-hour LSTM with 40+ features is STILL your best model! 0.6243 AUC
- it looks like our RF, random forest models are solid, but the lstm above is still sickest. i like testing the RF cause its way faster and supposedly, the features will carry over
- RF 3min is the best one so far
- 6 featuresworked best for me, 14, no go, but keep testing bro brooo


6/12-
- lets test the 1 hour and 4 hour


6/11 - got some poor results so testing things like btc only data, looking into hyper parameter optimization for time series 
    - our parmaeters were not optimized for time series.
    - once i optimized them for the RF, it became real good. i run this file to optimize params /Users/md/Dropbox/dev/github/moon-dev-trading-bots/research/machine_learning/rf_param_optimizer.py
    then i put them in the main file and run with those: rf_liquidations
- models AUC was only .56 or something which is bad. 
here are ideas to improve
    - need a 0.65 minumyum AUC to trade, but 0.7 is better
Data Quality: Liquidation data might be too noisy for 5-minute predictions
Feature Engineering: Need more sophisticated features (ratios, momentum, market microstructure)
Time Horizon: 5-minute predictions might be too short - try 15min, 30min, 1hr
- do a data check to make sure all data is gucci
- intraday is just hard, try longer patterns
- added AUC to my lstm_liquidations too
- do a full code review in order to ensure quality steps, ask ai about every step

6/10- started predicting the direction in the next x minutes instead of price exactly
    - implementing into RF and LSTM
    * fire - changing to direction got the RF to a 75% prediction rate. 