# 🌙 Moon Dev's Dune Data Fetcher 🚀

This tool fetches USDC deposit data from Dune Analytics for Hyperliquid whales and updates the whale address list used by the position tracker.

## 📋 Overview

The `dune_data.py` script connects to the Dune Analytics API to fetch data from the [Hyperliquid USDC Deposit dashboard](https://dune.com/kouei/hyperliquid-usdc-deposit). It extracts wallet addresses of users who have deposited significant amounts of USDC into Hyperliquid, which can be considered "whales" for tracking purposes.

## 🔧 Setup

1. **Get a Dune API Key**:
   - Sign up for a Dune Analytics account at [dune.com](https://dune.com)
   - Go to your profile settings and generate an API key
   - Add this key to your `.env` file:
     ```
     DUNE_KEY=your_api_key_here
     ```

2. **Install Required Packages**:
   ```
   pip install pandas requests tqdm colorama python-dotenv
   ```

## 🚀 Usage

Run the script from the project root directory:

```bash
python -m bots.hyperliquid.dune_data
```

The script will:
1. Generate mock data with random Ethereum addresses and deposit amounts
2. Process the data and save it to CSV files
3. Extract wallet addresses of whales (users with deposits >= $25,000)
4. Update the main `whale_addresses.txt` file used by `ppls_positions.py`

### Using Real Dune API Data

By default, the script uses mock data to avoid issues with the Dune API. If you want to use real data from Dune:

1. Set `USE_MOCK_DATA = False` in the script
2. Make sure you have a valid Dune API key in your `.env` file
3. Find the correct query ID for the dashboard (see below)

## 📁 Output Files

The script generates several files in the `bots/hyperliquid/data/dune_data` directory:

- `hlp_usdc_deposit.csv`: Raw data from the Dune query
- `dune_whale_addresses.txt`: List of whale addresses extracted from the data
- `dune_whale_addresses_with_deposits.csv`: Addresses with their deposit amounts

It also updates the main whale addresses file at:
- `bots/hyperliquid/data/ppls_positions/whale_addresses.txt`

## ⚙️ Configuration

You can modify these variables in the script:

- `MIN_POSITION_VALUE`: Minimum deposit amount to consider an address as a whale (default: $25,000)
- `QUERY_ID`: The Dune query ID (currently hardcoded, should be updated with the correct ID)
- `USE_MOCK_DATA`: Set to `False` to use the real Dune API instead of mock data

## 🔍 Finding the Query ID

The script currently uses a query ID that may need to be updated. To find the actual query ID:

1. Open the dashboard in your browser: https://dune.com/kouei/hyperliquid-usdc-deposit
2. Open the browser's developer tools (F12)
3. Go to the Network tab
4. Refresh the page and look for API calls
5. Find a request that contains a query ID in the URL or response
6. Update the `query_id` variable in the `get_query_id` function

### Alternative Method to Find Query ID

If you can't find the query ID through the network tab:

1. Click on any visualization in the dashboard
2. Look for "Edit Query" or similar option
3. The URL of the query editor will contain the query ID in the format: `https://dune.com/queries/QUERY_ID/...`

### Understanding the Data Structure

The script expects the query results to have at least these columns:
- `address`: The wallet address
- `deposit_usd`: The deposit amount in USD

If the column names are different, the script will try to find columns with similar names. If you encounter issues, check the actual column names in the query results and update the script accordingly.

## 🌟 Integration with Position Tracker

After running this script, you can run the position tracker to analyze the positions of the newly added whale addresses:

```bash
python -m bots.hyperliquid.ppls_positions
```

## 🚨 Troubleshooting

- **Mock Data**: By default, the script uses mock data to avoid issues with the Dune API. Set `USE_MOCK_DATA = False` to use real data.
- **API Key Issues**: Make sure your Dune API key is valid and has not expired. The script looks for the `DUNE_KEY` environment variable.
- **Query ID Issues**: If the query ID is incorrect, the script will fail to execute the query
- **Rate Limiting**: Dune API has rate limits, so avoid running the script too frequently
- **Query Execution Failures**: If the query fails to execute, check if the query is public and accessible with your API key

## 🌙 Created by Moon Dev 🚀

Happy whale tracking! 🐋 