
'''
This bot is a quick buy and sell. The objective is to be able to buy a token as quickly as possible or sell a token as quickly as possible. 
The way this is done is by token_addresses.txt file. 

This code will constantly monitor that TXT file and any contract address added there. It will instant buy the USDC size below 
You can adjust the priority fee, slippage, et cetera, below. 
I personally will be using this a lot as it is very close to hand trading, but I think it will be great to have in the case of some big launch or some big arbitrage that is seen. 

Now to buy, you simply just put the Contract Address in the txt file
to sell - you put the contract address and then a space and then a c or x


buying launches is a very hard game to play, if you use this tool i would suggest on bigger tokens. nfa tho. 

'''


# bulding a tool that will buy/sell sol tokens as quick as possible 
import time
import os
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import colorama
from termcolor import colored, cprint
from colorama import Fore, Style
import requests
import json
import base64
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from dotenv import load_dotenv
import pandas as pd
from solders.pubkey import Pubkey

# Load environment variables
load_dotenv()

# Constants
USDC_SIZE = 1  # $1 USDC for testing  
SLIPPAGE = 49  # 0.49% slippage (49 bps)
PRIORITY_FEE = 20000  # Priority fee for faster execution
CHECK_DELAY = 7  # Seconds to wait before checking position after orders
MAX_RETRIES = 3  # Maximum number of attempts
BUYS_PER_BATCH = 1  # Number of rapid buy orders to execute before checking position
SELLS_PER_BATCH = 3  # Number of rapid sell orders to execute before checking position

QUOTE_TOKEN = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC token address
MY_ADDRESS = "G1vNV2SkzGPTBTDd7c3iypL4TPNGbe37rEbJb7cxVTQS"  # Your actual Solana wallet address

# Initialize colorama
colorama.init()

def get_position(token_mint_address):
    #print(f'getting position for {token_mint_address[:4]}')
    dataframe = fetch_wallet_token_single(MY_ADDRESS, token_mint_address)

    if dataframe.empty:
        #print(f"No se encontró posición para {token_mint_address}")
        return 0
    
    # Asumiendo que 'Amount' es la columna correcta (con A mayúscula)
    if 'Amount' in dataframe.columns:
        return float(dataframe['Amount'].values[0])
    else:
        #print(f"No se encontró columna 'Amount'. Columnas disponibles: {dataframe.columns}")
        return 0

def fetch_wallet_token_single(wallet_address, token_mint_address):
    API_KEY = os.getenv('BIRDEYE_KEY')  # Use environment variable
    
    url = f"https://public-api.birdeye.so/v1/wallet/token_list?wallet={wallet_address}"
    
    headers = {
        "accept": "application/json",
        "x-chain": "solana",
        "X-API-KEY": API_KEY
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Esto levantará una excepción para códigos de estado HTTP no exitosos
        
        data = response.json()
        
        if 'data' in data and 'items' in data['data']:
            df = pd.DataFrame(data['data']['items'])
            
            # Filtra por el token_mint_address específico
            if 'address' in df.columns:
                df = df[df['address'] == token_mint_address]
            elif 'tokenAddress' in df.columns:
                df = df[df['tokenAddress'] == token_mint_address]
            else:
                #print(f"No se encontró columna 'address' o 'tokenAddress'. Columnas disponibles: {df.columns}")
                return pd.DataFrame()
            
            if not df.empty:
                # Renombra las columnas para mantener la consistencia con el formato anterior
                df = df.rename(columns={
                    'address': 'Mint Address',
                    'uiAmount': 'Amount',
                    'valueUsd': 'USD Value'
                })
                
                # Selecciona solo las columnas necesarias
                df = df[['Mint Address', 'Amount', 'USD Value']]
                
                return df
            else:
                #print(f'No data found for token {token_mint_address[:4]}')
                return pd.DataFrame(columns=['Mint Address', 'Amount', 'USD Value'])
        else:
            #print("No data available in the response.")
            return pd.DataFrame(columns=['Mint Address', 'Amount', 'USD Value'])
    
    except requests.RequestException as e:
        #print(f"Error fetching data for token {token_mint_address[:4]}: {e}")
        return pd.DataFrame(columns=['Mint Address', 'Amount', 'USD Value'])

def get_decimals(token_mint_address):
    """Get token decimals"""
    try:
        load_dotenv()
        RPC_URL = os.getenv('RPC_URL')
        http_client = Client(RPC_URL)
        
        # Convert string address to Pubkey
        token_pubkey = Pubkey.from_string(token_mint_address)
        
        response = http_client.get_token_supply(token_pubkey)
        return response.value.decimals
        
    except Exception as e:
        print(f"❌ MOON DEV Error getting decimals: {str(e)}")
        print("🔄 Using default decimals of 9")
        return 9  # Default to 9 decimals if error

def market_buy(token_address, amount):
    """Quick market buy function optimized for speed"""
    try:
        load_dotenv()
        KEY = Keypair.from_base58_string(os.getenv('SOL_KEY2'))
        RPC_URL = os.getenv('RPC_URL')
        
        http_client = Client(RPC_URL)
        
        quote_url = f'https://quote-api.jup.ag/v6/quote?inputMint={QUOTE_TOKEN}&outputMint={token_address}&amount={amount}&slippageBps={SLIPPAGE}&restrictIntermediateTokens=true'
        swap_url = 'https://quote-api.jup.ag/v6/swap'
        
        quote = requests.get(quote_url).json()
        
        tx_res = requests.post(
            swap_url,
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "quoteResponse": quote,
                "userPublicKey": str(KEY.pubkey()),
                "prioritizationFeeLamports": PRIORITY_FEE
            })
        ).json()
        
        swap_tx = base64.b64decode(tx_res['swapTransaction'])
        tx1 = VersionedTransaction.from_bytes(swap_tx)
        tx = VersionedTransaction(tx1.message, [KEY])
        tx_id = http_client.send_raw_transaction(bytes(tx), TxOpts(skip_preflight=True)).value
        
        print(f"🌙 MOON DEV Buy Transaction: https://solscan.io/tx/{str(tx_id)}")
        return True
        
    except Exception as e:
        print(f"❌ MOON DEV Error: {str(e)}")
        return False

def market_sell(token_address, amount):
    """Quick market sell function optimized for speed"""
    try:
        load_dotenv()
        KEY = Keypair.from_base58_string(os.getenv('SOL_KEY2'))
        RPC_URL = os.getenv('RPC_URL')
        
        http_client = Client(RPC_URL)
        
        quote_url = f'https://quote-api.jup.ag/v6/quote?inputMint={token_address}&outputMint={QUOTE_TOKEN}&amount={amount}&slippageBps={SLIPPAGE}'
        swap_url = 'https://quote-api.jup.ag/v6/swap'
        
        quote = requests.get(quote_url).json()
        
        tx_res = requests.post(
            swap_url,
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "quoteResponse": quote,
                "userPublicKey": str(KEY.pubkey()),
                "prioritizationFeeLamports": PRIORITY_FEE
            })
        ).json()
        
        swap_tx = base64.b64decode(tx_res['swapTransaction'])
        tx1 = VersionedTransaction.from_bytes(swap_tx)
        tx = VersionedTransaction(tx1.message, [KEY])
        tx_id = http_client.send_raw_transaction(bytes(tx), TxOpts(skip_preflight=True)).value
        
        print(f"🌙 MOON DEV Sell Transaction: https://solscan.io/tx/{str(tx_id)}")
        return True
        
    except Exception as e:
        print(f"❌ MOON DEV Error: {str(e)}")
        return False

class TokenFileHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.file_path = os.path.join(os.path.dirname(__file__), 'token_addresses.txt')
        self.last_processed = set()
        
    def on_modified(self, event):
        if event.src_path == self.file_path:
            self.process_new_tokens()
            
    def quick_buy(self, token_address):
        """Execute quick buy with minimal checks"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-4]
        print(f"\n{Fore.CYAN}🚀 MOON DEV QUICK BUY INITIATED 🚀{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}⏰ Time: {timestamp}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}📝 Token Address: {token_address}{Style.RESET_ALL}")
        
        # Convert USDC_SIZE to smallest units (6 decimals for USDC)
        amount = int(USDC_SIZE * 10**6)
        
        # First instant buy attempt
        success = market_buy(token_address, str(amount))
        if not success:
            print(f"{Fore.RED}❌ Initial buy failed{Style.RESET_ALL}")
            return
            
        # Wait briefly then check position
        time.sleep(CHECK_DELAY)
        position = get_position(token_address)
        
        # Retry if position is too small
        retries = 0
        while position < (0.9 * USDC_SIZE) and retries < MAX_RETRIES:
            print(f"{Fore.YELLOW}🔄 Position size: ${position:.2f}, attempting batch buy...{Style.RESET_ALL}")
            
            # Execute buys in rapid succession
            for i in range(BUYS_PER_BATCH):
                success = market_buy(token_address, str(amount))
                if not success:
                    print(f"{Fore.RED}❌ Buy {i+1}/{BUYS_PER_BATCH} failed{Style.RESET_ALL}")
                    break
                print(f"{Fore.GREEN}✅ Buy {i+1}/{BUYS_PER_BATCH} complete{Style.RESET_ALL}")
            
            # Wait after batch to verify completion
            print(f"{Fore.YELLOW}⏳ Waiting {CHECK_DELAY}s to verify position...{Style.RESET_ALL}")
            time.sleep(CHECK_DELAY)
            position = get_position(token_address)
            
            # If position still not complete, retry the batch
            if position < (0.9 * USDC_SIZE):
                print(f"{Fore.YELLOW}🔄 Position incomplete (${position:.2f}), retrying batch...{Style.RESET_ALL}")
                retries += 1
                continue
            else:
                print(f"{Fore.GREEN}✅ Position successfully filled: ${position:.2f}{Style.RESET_ALL}")
                break
            
        # Final status message
        if position >= (0.9 * USDC_SIZE):
            print(f"{Fore.GREEN}🌙 MOON DEV BUY ✅ SUCCESS | Final Position: ${position:.2f} 🌙{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}🌙 MOON DEV BUY ⚠️ ORDERS COMPLETE | Final Position: ${position:.2f} 🌙{Style.RESET_ALL}")

    def quick_sell(self, token_address):
        """Execute quick sell with minimal checks"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-4]
        print(f"\n{Fore.CYAN}🚀 MOON DEV QUICK SELL INITIATED 🚀{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}⏰ Time: {timestamp}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}📝 Token Address: {token_address}{Style.RESET_ALL}")
        
        # Get initial position to determine sell size
        initial_position = get_position(token_address)
        if initial_position == 0:
            print(f"{Fore.RED}❌ No position found to sell{Style.RESET_ALL}")
            return
            
        print(f"{Fore.YELLOW}📊 Initial position: {initial_position}{Style.RESET_ALL}")
        
        # Calculate sell size
        decimals = get_decimals(token_address)
        sell_size = int(initial_position * 10**decimals)
        
        # Retry if position still exists
        retries = 0
        while initial_position > 0 and retries < MAX_RETRIES:
            print(f"\n{Fore.YELLOW}🔄 Batch {retries + 1}/{MAX_RETRIES}: Executing {SELLS_PER_BATCH} rapid sells...{Style.RESET_ALL}")
            
            # Execute sells in rapid succession
            for i in range(SELLS_PER_BATCH):
                success = market_sell(token_address, str(sell_size))
                if not success:
                    print(f"{Fore.RED}❌ Sell {i+1}/{SELLS_PER_BATCH} failed{Style.RESET_ALL}")
                    continue
                print(f"{Fore.GREEN}✅ Sell {i+1}/{SELLS_PER_BATCH} complete{Style.RESET_ALL}")
            
            # Wait after batch to verify completion
            print(f"{Fore.YELLOW}⏳ Waiting {CHECK_DELAY}s to verify position...{Style.RESET_ALL}")
            time.sleep(CHECK_DELAY)
            
            # Check if position is closed
            remaining_position = get_position(token_address)
            if remaining_position == 0:
                print(f"{Fore.GREEN}✅ Position successfully closed!{Style.RESET_ALL}")
                break
            else:
                print(f"{Fore.YELLOW}⚠️ Position still open: {remaining_position} remaining{Style.RESET_ALL}")
                # Update sell size for remaining position
                sell_size = int(remaining_position * 10**decimals)
                retries += 1
                if retries < MAX_RETRIES:
                    print(f"{Fore.YELLOW}🔄 Preparing next batch of {SELLS_PER_BATCH} sells...{Style.RESET_ALL}")
                
        # Final status message
        if remaining_position == 0:
            print(f"{Fore.GREEN}🌙 MOON DEV SELL ✅ SUCCESS | Position Closed 🌙{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}🌙 MOON DEV SELL ⚠️ ORDERS COMPLETE | Remaining Position: {remaining_position} 🌙{Style.RESET_ALL}")

    def process_new_tokens(self):
        try:
            with open(self.file_path, 'r') as file:
                current_tokens = set(line.strip() for line in file if line.strip() and not line.startswith('#'))
            
            new_tokens = current_tokens - self.last_processed
            
            for token in new_tokens:
                # Check if token has sell command
                parts = token.split()
                if len(parts) == 2:  # Token address followed by command
                    token_address = parts[0]
                    command = parts[1].lower()
                    if command in ['x', 'c']:
                        self.quick_sell(token_address)
                    else:
                        self.quick_buy(token_address)
                else:
                    self.quick_buy(token)
            
            self.last_processed = current_tokens
                
        except Exception as e:
            print(f"{Fore.RED}🌙 MOON DEV ERROR: Failed to process token file: {e} 🌙{Style.RESET_ALL}")

if __name__ == "__main__":
    print(f"{Fore.CYAN}🌙 MOON DEV Quick Buy/Sell Monitor Starting... 🌙{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}👀 Watching for new tokens in token_addresses.txt{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}💡 Add 'x' or 'c' after token address to trigger quick sell{Style.RESET_ALL}")
    
    event_handler = TokenFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path=os.path.dirname(__file__), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(0.1)  # Check every 0.1 seconds
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}🌙 MOON DEV Monitor stopping...{Style.RESET_ALL}")
        observer.stop()
        observer.join() 