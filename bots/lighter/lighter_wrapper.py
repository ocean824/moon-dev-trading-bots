"""
Lighter Exchange SDK implementation using the official SDK
This provides the proper SignerClient interface using the real Lighter SDK
"""

import asyncio
from typing import Dict, Any
from lighter import SignerClient as RealSignerClient, ApiClient as RealApiClient


class ApiClient:
    """ApiClient wrapper for Lighter Exchange"""
    
    def __init__(self):
        self.base_url = "https://mainnet.zklighter.elliot.ai"
        self.real_client = RealApiClient()
        
    async def close(self):
        """Close the client connection"""
        if hasattr(self.real_client, 'close'):
            await self.real_client.close()


class SignerClient:
    """SignerClient that uses the official Lighter SDK"""
    
    def __init__(self, url: str, private_key: str, api_key_index: int, account_index: int):
        self.url = url
        self.private_key = private_key
        self.api_key_index = api_key_index
        self.account_index = account_index
        
        # Create the official SignerClient
        try:
            self.real_signer = RealSignerClient(
                url=url,
                private_key=private_key,
                api_key_index=api_key_index,
                account_index=account_index
            )
            # Signer created successfully (no debug output)
        except Exception as e:
            raise Exception(f"Could not create SignerClient: {e}")
            self.real_signer = None
    
    async def create_order(self, market_index: int, client_order_index: int,
                          base_amount: int, price: int, is_ask: bool,
                          order_type: int, time_in_force: int, order_expiry: int) -> Dict[str, Any]:
        """Create a limit order using the official Lighter SDK"""
        try:
            if not self.real_signer:
                raise Exception("SignerClient not initialized")

            # Debug: Print what we're sending to SDK
            print(f"[WRAPPER] Calling SDK create_order with:")
            print(f"  market_index={market_index} (type: {type(market_index).__name__})")
            print(f"  client_order_index={client_order_index} (type: {type(client_order_index).__name__})")
            print(f"  base_amount={base_amount} (type: {type(base_amount).__name__})")
            print(f"  price={price} (type: {type(price).__name__})")
            print(f"  is_ask={is_ask} (type: {type(is_ask).__name__})")
            print(f"  order_type={order_type} (type: {type(order_type).__name__})")
            print(f"  time_in_force={time_in_force} (type: {type(time_in_force).__name__})")
            print(f"  order_expiry={order_expiry} (type: {type(order_expiry).__name__})")

            # Use the official SDK create_order method
            create_order_obj, tx_hash, signed_tx = await self.real_signer.create_order(
                market_index=market_index,
                client_order_index=client_order_index,
                base_amount=base_amount,
                price=price,
                is_ask=is_ask,
                order_type=order_type,
                time_in_force=time_in_force,
                order_expiry=order_expiry
            )

            print(f"[WRAPPER] SDK returned successfully")

            # Return in expected format
            return {
                "success": True,
                "order_id": client_order_index,
                "tx_hash": str(tx_hash),
                "signed_tx": signed_tx,
                "create_order_obj": create_order_obj
            }

        except Exception as e:
            print(f"[WRAPPER] SDK raised exception: {e}")
            raise
    
    async def create_market_order(self, market_index: int, client_order_index: int,
                                 base_amount: int, avg_execution_price: int, is_ask: bool) -> Dict[str, Any]:
        """Create a market order using the official Lighter SDK"""
        try:
            if not self.real_signer:
                raise Exception("SignerClient not initialized")

            # Use the official SDK create_market_order method
            create_order_obj, tx_hash, signed_tx = await self.real_signer.create_market_order(
                market_index=market_index,
                client_order_index=client_order_index,
                base_amount=base_amount,
                avg_execution_price=avg_execution_price,  # Required parameter
                is_ask=is_ask
            )

            # Return in expected format
            return {
                "success": True,
                "order_id": client_order_index,
                "tx_hash": str(tx_hash),
                "signed_tx": signed_tx,
                "create_order_obj": create_order_obj
            }

        except Exception as e:
            raise
    
    async def cancel_order(self, market_index: int, order_index: int) -> Dict[str, Any]:
        """Cancel an order using the official Lighter SDK"""
        try:
            if not self.real_signer:
                raise Exception("SignerClient not initialized")

            # Use the official SDK cancel_order method
            cancel_order_obj, tx_hash, signed_tx = await self.real_signer.cancel_order(
                market_index=market_index,
                order_index=order_index  # Correct parameter name
            )

            # Return in expected format
            return {
                "success": True,
                "order_id": order_index,
                "tx_hash": str(tx_hash),
                "signed_tx": signed_tx,
                "cancel_order_obj": cancel_order_obj
            }

        except Exception as e:
            raise