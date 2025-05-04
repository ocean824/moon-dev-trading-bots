from termcolor import cprint
from pprint import pprint
from termcolor import cprint
# from time import time
import base58
import json
import time
import os
from dotenv import load_dotenv

from solana.rpc.api import Client
from solana.rpc.commitment import Commitment
from solana.rpc.types import TokenAccountOpts
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import close_account
from spl.token.instructions import CloseAccountParams
# import dontshare as d  # Assuming this is a module you have

# Load environment variables
load_dotenv()

# RPC URL and wallet information
rpc_url = os.getenv('RPC_URL')
wallet_addr = "G1vNV2SkzGPTBTDd7c3iypL4TPNGbe37rEbJb7cxVTQS"
wallet_key = os.getenv('SOL_KEY2')

# Print debug info without exposing sensitive data
print("🌙 MoonDev Debug: RPC URL loaded:", "✓" if rpc_url else "✗")
print("🌙 MoonDev Debug: Wallet Key loaded:", "✓" if wallet_key else "✗")

# Convert wallet address and key to pubkey and keypair
wallet_pubkey = Pubkey(base58.b58decode(wallet_addr))

if wallet_key:
    wallet_keypair = Keypair.from_base58_string(wallet_key)
else:
    wallet_keypair = None

# Print wallet public key and keypair public key for debugging
print(f"wallet_pubkey          : {wallet_pubkey}")
print(f"wallet_keypair pubkey  : {wallet_keypair.pubkey()}")

# Check if the wallet_keypair's public key matches the wallet_pubkey
if wallet_pubkey != wallet_keypair.pubkey():
    print("Error: The provided wallet_key does not correspond to the wallet_addr.")
    print("Please ensure that the private key (wallet_key) matches the wallet address (wallet_addr).")
    exit(1)

client = Client(rpc_url, commitment=Commitment("confirmed"), timeout=30)

# <=====> #

def release_the_kraken(wallet_pubkey):
    sol_refunded = 0
    tot_sol_refunded = 0

    client = Client(rpc_url, commitment=Commitment("confirmed"), timeout=30)

    accts = client.get_token_accounts_by_owner_json_parsed(
        owner=wallet_pubkey,
        opts=TokenAccountOpts(program_id=TOKEN_PROGRAM_ID),
        commitment=None
    )
    how_many = len(accts.value)
    usual_sol_rclm = 0.00203928
    exp_refund = how_many * usual_sol_rclm
    print('estimating : {:21.8f} on {} token accts'.format(exp_refund, how_many))
    print('')

    if not accts.value:
        print("No token accounts found.")
        return

    for acct in accts.value:
        print(acct)
        print('')
        print('')

        # Rebuild client to keep things fresh
        client = Client(rpc_url, commitment=Commitment("confirmed"), timeout=30)

        tkn_acct_pubkey = acct.pubkey
        tkn_addr = acct.account.data.parsed['info']['mint']
        tkn_owner = acct.account.data.parsed['info']['owner']
        tkn_bal = acct.account.data.parsed['info']['tokenAmount']['uiAmount']
        tkn_dec = acct.account.data.parsed['info']['tokenAmount']['decimals']
        tkn_rent = acct.account.rent_epoch
        lamports = acct.account.lamports

        print('tkn_owner            : {} ({})'.format(tkn_owner, type(tkn_owner)))
        print('tkn_addr             : {} ({})'.format(tkn_addr, type(tkn_addr)))
        print('tkn_acct_pubkey      : {} ({})'.format(tkn_acct_pubkey, type(tkn_acct_pubkey)))
        print('tkn_bal              : {} ({})'.format(tkn_bal, type(tkn_bal)))
        print('tkn_dec              : {} ({})'.format(tkn_dec, type(tkn_dec)))
        print('tkn_rent             : {} ({})'.format(tkn_rent, type(tkn_rent)))

        tkn_pubkey = Pubkey(base58.b58decode(tkn_addr))
        prog_id_pubkey = TOKEN_PROGRAM_ID

        print(f"Account             : {tkn_acct_pubkey}")
        print(f"Token Mint          : {tkn_addr}")
        print(f"Token Balance       : {tkn_bal}")
        print(f"Lamports (SOL)      : {lamports / 1e9}")

        # Decision to close the account
        if tkn_bal > 0:
            WoR("NOT CLOSING account...")
        if tkn_bal == 0:
            # Close the account
            WoG("CLOSING account...")

            sol_refunded = lamports / 1e9
            tot_sol_refunded += lamports / 1e9
            print("refund_amt : {:>14.8f}, tot_refund_amt : {:14.8f}".format(sol_refunded, tot_sol_refunded))
            if wallet_keypair:
                close_account_instr = close_account(
                    CloseAccountParams(
                        account=tkn_acct_pubkey,
                        dest=wallet_pubkey,
                        owner=wallet_pubkey,
                        program_id=prog_id_pubkey
                    )
                )
                transaction = Transaction()
                transaction.add(close_account_instr)
                time.sleep(3)

                try:
                    # Get a recent blockhash first
                    recent_blockhash = client.get_latest_blockhash()
                    print(f"🌙 MoonDev Debug: Got recent blockhash: {recent_blockhash.value.blockhash} ✨")
                    
                    # Set the recent blockhash in the transaction
                    transaction.recent_blockhash = recent_blockhash.value.blockhash
                    
                    # Sign and serialize transaction
                    transaction.sign(wallet_keypair)
                    print(f"🌙 MoonDev Debug: Transaction signed by {wallet_keypair.pubkey()} ✨")
                    
                    serialized_tx = transaction.serialize()
                    print(f"🌙 MoonDev Debug: Transaction serialized successfully! ✨")
                    
                    # Send only the serialized transaction
                    response = client.send_transaction(
                        serialized_tx
                    )
                    print(f"🌙 MoonDev's Transaction Success! ✨ Closed account {tkn_acct_pubkey} {tkn_addr}: {response}")
                except Exception as e:
                    print(f"💫 Houston, MoonDev has a problem! Account {tkn_acct_pubkey}: {e}")
                    raise
                time.sleep(10)

# <=====> #

def force_feed_kraken(wallet_pubkey, tkn_addr):
    client = Client(rpc_url, commitment=Commitment("confirmed"), timeout=30)

    tkn_pubkey = Pubkey(base58.b58decode(tkn_addr))
    prog_id_pubkey = TOKEN_PROGRAM_ID

    time.sleep(1)

    acct = client.get_token_accounts_by_owner_json_parsed(
        wallet_pubkey,
        TokenAccountOpts(tkn_pubkey)
    )

    print(acct.value[0].account.data)

    tkn_acct_pubkey = acct.value[0].pubkey
    tkn_addr = acct.value[0].account.data.parsed['info']['mint']
    tkn_native = acct.value[0].account.data.parsed['info']['isNative']
    tkn_owner = acct.value[0].account.data.parsed['info']['owner']
    tkn_bal = acct.value[0].account.data.parsed['info']['tokenAmount']['uiAmount']
    tkn_dec = acct.value[0].account.data.parsed['info']['tokenAmount']['decimals']
    tkn_rent = acct.value[0].account.rent_epoch
    lamports = acct.value[0].account.lamports

    print('tkn_owner            : {} ({})'.format(tkn_owner, type(tkn_owner)))
    print('tkn_addr             : {} ({})'.format(tkn_addr, type(tkn_addr)))
    print('tkn_native           : {} ({})'.format(tkn_native, type(tkn_native)))
    print('tkn_acct_pubkey      : {} ({})'.format(tkn_acct_pubkey, type(tkn_acct_pubkey)))
    print('tkn_bal              : {} ({})'.format(tkn_bal, type(tkn_bal)))
    print('tkn_dec              : {} ({})'.format(tkn_dec, type(tkn_dec)))
    print('tkn_rent             : {} ({})'.format(tkn_rent, type(tkn_rent)))
    
    print(f"Account             : {tkn_acct_pubkey}")
    print(f"Token Mint          : {tkn_addr}")
    print(f"Token Balance       : {tkn_bal}")
    print(f"Lamports (SOL)      : {lamports / 1e9}")

    # Close the account
    WoG("CLOSING account...")

    sol_refunded = lamports / 1e9
    print("refund_amt         : {:>14.8f}".format(sol_refunded))
    if wallet_keypair:
        close_account_instr = close_account(
            CloseAccountParams(
                account=tkn_acct_pubkey,
                dest=wallet_pubkey,
                owner=wallet_pubkey,
                program_id=prog_id_pubkey
            )
        )
        transaction = Transaction()
        transaction.add(close_account_instr)
        time.sleep(1)
        try:
            # Get a recent blockhash first
            recent_blockhash = client.get_latest_blockhash()
            print(f"🌙 MoonDev Debug: Got recent blockhash: {recent_blockhash.value.blockhash} ✨")
            
            # Set the recent blockhash in the transaction
            transaction.recent_blockhash = recent_blockhash.value.blockhash
            
            transaction.sign(wallet_keypair)
            print(f"🌙 MoonDev Debug: Transaction signed by {wallet_keypair.pubkey()} ✨")
            
            serialized_tx = transaction.serialize()
            print(f"🌙 MoonDev Debug: Transaction serialized successfully! ✨")
            
            response = client.send_transaction(
                serialized_tx
            )
            print(f"🌙 MoonDev's Transaction Success! ✨ Closed account {tkn_acct_pubkey} {tkn_addr}: {response}")
        except Exception as e:
            print(f"💫 Houston, MoonDev has a problem! Account {tkn_acct_pubkey}: {e}")
            raise

# <=====> #

def WoG(in_str, print_tf=True):
    if print_tf:
        cprint(in_str, 'white', 'on_green')
    else:
        return colored(in_str, 'white', 'on_green')

# <=====> #

def WoR(in_str, print_tf=True):
    if print_tf:
        cprint(in_str, 'white', 'on_red')
    else:
        return colored(in_str, 'white', 'on_red')

# <=====> #

def beep():
    print('\a', end='', flush=True)

# <=====> #

# Uncomment and use the function you need
# force_feed_kraken(wallet_pubkey, tkn_addr="5bnN9VZeDUhCh8PUGP4GAuMXYcBzvCpehbPJCYU2t9Zy")
release_the_kraken(wallet_pubkey)
