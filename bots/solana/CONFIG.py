# I CAN CHANGE THE AMOUNT OF TOKENS IN THE TRENDING_TOKENS IM BUYING BY TWEAKING THE BELOW.

# Configuration
USDC_SIZE = 1
MINUTES_TO_CHECK = 30  # Variable to set the time window for checking transactions
SLEEP_TIME = .1  # Time to sleep between checking each wallet
DAYS_BACK = 0 # how many days back to check for txs
TP = 49 # 50x return
SL = .6 # 60% loss
MAX_POSITIONS = 50
MIN_TRADES_LAST_HOUR  = 60
MAX_MARKET_CAP = 1000000
MIN_LIQUIDITY = 1000
UNIQUE_WALLETS = 30
MAX_DD = -70 # 70% drop
TOP_10PERC_MAX = .7 # IF MORE THAN 70% OF TOP 10 HOLDERS DROP, GET GHOSTED
DO_NOT_TRADE_LIST = ['So11111111111111111111111111111111111111111','KhALz1buce8zVHjoGzGjGqiJXu9bYyJ1H1shT3vNq1i','hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux','4ySwgHAevvDi65ZQ1rEhc5L5ZK386Fm95VgTiLqVpump', 'EXukF7ynKHPC1BTGxJ4ajDusoEhNvpF8xbzZxU8mpump','3qvnewRfvjum6SMunykwXYswmeAF2QKr6khrLqmipump','kvoPvdfHUVnxD4t2jdqkm4a34HMRMseKx19JFZPpump','FtMXRF47Jm9yB6abJeK7pgeeDhwxa2GiPfAdv9Fipump','5qvqjA8vxwS7rhMEmox1Vi7v3C8qWr74wgcK4TQapump','FivkLHJiYhoZT1YrSRWsD6XPBvSNVwmwff1y82vZpump','3jN3zPSE2nNHuQ7bT2JH2JYhkzbL7vnvJnoMNQ8LyTTM','LoxQiS7XLhbtZsdYFCSKjjGPfu4En6pdoerRuTzpump','GMrCLQP6XeiJAmJfFj3ApJPwKQt4xusd69rve3Dxpump','CwkcC3MF58gxcxfGt46onbqNb3jq4EhVnJVMAa1ipump','Fs6Ucti3HjXjqLaQLiXfgVg7wxJw5msrrYDAQPDFpump', '5146zXQWqRvGPytJtRFXYjcbYBwg6XfkWQUobZcxJZHX','7ZWweKCCyVzWTToS1EuB3V3krTxz142KmcbbnUEypump','D1ySHVWnaWQsf8WiskayoF7oHuvXLp4CXvYw3PaS8N7B','BXoz2cxZi65oQBhcSvxgv7dwFMhg184v1N3idhJhpump','5NegGDJBWqfJbKFYwuuUnWcnKQtez7jkRkzAx6Rjpump','DsfwbGtT2pSFaFTZUe6hwwir2wQvFvXsYahC4uv6T85y','rjyT9DdKu47fsX9JfozX4z6Qk25y12kFaVuV7cFpump','GV2HFvE9quMWMp5BDuRz3XudHyRPEAMMtdAqoF2u7yE8','Eq1qrNGCiCtcZhFUGDYAmRJQ2w9kdLPak1Gx4mvkTQCE', 'Q1BaFmfN8TXdMVS98RYMhFZWRzVTCp8tUDhqM9CgcAL','HiZZAjSHf8W53QPtWYzj1y9wqhdirg124fiEHFGiUpQh', 'AuabGXArmR3QwuKxT3jvSViVPscQASkFAvnGDQCE8tfm','rxkExwV2Gay2Bf1so4chsZj7f4MiLKTx45bd9hQy6dK','BmDXugmfBhqKE7S2KVdDnVSNGER5LXhZfPkRmsDfVuov','423scBCY2bzX6YyqwkjCfWN114JY3xvyNNZ1WsWytZbF','7S6i87ZY29bWNbkviR2hyEgRUdojjMzs1fqMSXoe3HHy', '8nBNfJsvtVmZXhbyLCBg3ndVW2Zwef7oHuCPjQVbRqfc','FqW3CJYF3TfR49WXRusxqCbJMNSjnay1A51sqP34ZxcB','EwsHNUuAtPc6SHkhMu8sQoyL6R4jnWYUU1ugstHXo5qQ','EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', '9Y9yqdNUL76v1ybpkQnVUj35traGEHXTBJB2b1iszFVv', 'Fd1hzhprThxCwz2tv5rTKyFeVCyEKRHaGqhT7hDh4fsW', '83227N9Fq4h1HMNnuKut61beYcB7fsCnRbzuFDCt2rRQ', 'J1oqg1WphZaiRDTfq7gAXho6K1xLoRMxVvVG5BBva3fh', 'GEvQuL9DT2UDtuTCCyjxm6KXEc7B5oguTHecPhKad8Dr',"3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh", "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263","7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr","7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",'zBTCug3er3tLyffELcvDNrKkCymbPWysGcWihESYfLg','EyzgnBfHGe9hh169B8993muBVcoeURCnSgPbddBeSybo'] 
SELL_AMOUNT_PERC = .7
ORDERS_PER_OPEN = 1
MIN_TRADES_30M_ONCE_IN_POSITION = 5
RANDOM_WALLETS = 1200 # if set to 0, will loop through all wallets


SLIPPAGE = 499  # 5000 is 50%, 500 is 5% and 50 is .5%
PRIORITY_FEE = 20000 # 200000 is about .035 usd at 150 sol, after a bit of testing 100000 is sufficient and is .02 usd

# Load environment variables
from dotenv import load_dotenv
import os
load_dotenv()

# API Keys from environment variables
BIRDEYE_KEY = os.getenv('BIRDEYE_KEY')
SOL_KEY = os.getenv('SOL_KEY')
RPC_URL = os.getenv('RPC_URL')

TIMEFRAME_FOR_SMA = '4H'

RECENT_TXS_CSV = 'csvs/recenttxs.csv'
TRENDING_TOKENS_CSV = 'csvs/trending_tokens.csv'
CURRENT_PORTFOLIO_CSV = 'csvs/current_portfolio.csv'  # For tracking current holdings
BIRDEYE_TRENDING_TOKENS_CSV = 'csvs/birdeye_trending_tokens.csv'
BIRDEYE_TRENDING_FINAL = 'csvs/birdeye_trending_final.csv'
NEW_TOKEN_HOURS_CSV = 'csvs/new_token_hours.csv'
TOP_TRADERS_BIRDEYE_CSV = 'csvs/top_traders_birdeye.csv'
PPL_TO_FOLLOW_CSV = 'csvs/ppl_to_follow.csv'
BOTS_TO_STUDY_CSV = 'csvs/bots_to_study.csv'
WALLET_TOKENS_CSV = 'csvs/wallet_tokens.csv'
CLOSED_POSITIONS_TXT = 'data/closed_positions.txt'
READY_TO_BUY_CSV = 'csvs/trending_tokens.csv'  # Point to trending_tokens.csv
TOKEN_PER_ADDY_CSV = 'csvs/token_per_addy.csv'
ALL_TRENDING_EVER_CSV = 'csvs/all_trending_ever.csv'
LEADERBOARD_CSV = 'csvs/leaderboard.csv'

MY_ADDRESS = '4wgfCBf2WwLSRKLef9iW7JXZ2AfkxUxGM4XcKpHm3Sin'
MY_ADDRESS2 = 'G1vNV2SkzGPTBTDd7c3iypL4TPNGbe37rEbJb7cxVTQS'
USDC_CONTRACT_ADDRESS = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'

# Number of most recent token launches to process
PAST_NEW_LAUNCHES = 20  # Only process this many of the most recent token launches