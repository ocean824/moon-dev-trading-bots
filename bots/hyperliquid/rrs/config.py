# config.py
import os


# API Settings
API_URL = 'https://api.hyperliquid.xyz/info'
API_HEADERS = {'Content-Type': 'application/json'}


# Data Settings
SYMBOLS = ['BTC', 'ETH', 'SOL', 'WIF', 'ADA', 'DOT', 'LINK', 'XRP', 'LTC', 'BCH',
           'kBONK', 'kPEPE', 'GOAT', 'SUI', 'POPCAT', 'MOODENG', 'kSHIB', 'HBAR', 'TIA', 'NEAR',
           'PNUT', 'BNB', 'FTM', 'CRV', 'AAVE', 'AVAX', 'OP', 'ARB', 'RUNE', 'FET', 'JUP']  # 30 tokens


# Timeframe Settings
TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1d']  # 🌙 Moon Dev's favorite timeframes
DEFAULT_TIMEFRAME = '1m'  # Used as fallback


# Analysis Settings
LOOKBACK_DAYS = 90
MAX_CALL_LIMIT = 5000  # Max records per API call


# Directory Settings
DATA_DIR = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/bots/hyperliquid/rrs/data'
RESULTS_DIR = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/bots/hyperliquid/rrs/results'


# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
