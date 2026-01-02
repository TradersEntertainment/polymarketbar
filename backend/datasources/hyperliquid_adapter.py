import ccxt.async_support as ccxt
import asyncio
import pandas as pd
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class HyperliquidAdapter:
    def __init__(self):
        self.exchange = None
        self.symbol_map = {
            'BTC': 'BTC/USDC:USDC',
            'ETH': 'ETH/USDC:USDC',
            'SOL': 'SOL/USDC:USDC',
            'XRP': 'XRP/USDC:USDC',
            'SUI': 'SUI/USDC:USDC',
            'AVA': 'AVA/USDC:USDC',
            # Add others as needed
        }
        self._init_exchange()

    def _init_exchange(self):
        try:
            self.exchange = ccxt.hyperliquid({
                'timeout': 10000,
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'} 
            })
        except Exception as e:
            logger.error(f"Failed to init Hyperliquid: {e}")

    async def close(self):
        if self.exchange:
            await self.exchange.close()

    async def restart(self):
        logger.info("Restarting Hyperliquid Adapter...")
        await self.close()
        self._init_exchange()
        
    # --- Compatibility Stubs for CCXTAdapter ---
    async def update_cache(self, *args, **kwargs): pass
    async def backfill_history(self, *args, **kwargs): pass
    def save_cache(self): pass
    # -------------------------------------------

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 1000) -> pd.DataFrame:
        """
        Direct fetch from Hyperliquid.
        """
        if not self.exchange: return pd.DataFrame()

        try:
            # Map symbol
            base = symbol.split('/')[0] if '/' in symbol else symbol
            mapped = self.symbol_map.get(base, f"{base}/USDC:USDC")
            
            # Hyperliquid supports standard timeframes usually
            # If not, we might need basic mapping, but ccxt handles '15m', '1h', '4h', '1d' well.
            
            ohlcv = await self.exchange.fetch_ohlcv(mapped, timeframe, limit=limit)
            
            if not ohlcv:
                return pd.DataFrame()

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Hyperliquid OHLCV Error ({symbol} {timeframe}): {e}")
            return pd.DataFrame()

    async def fetch_current_price(self, symbol: str) -> float:
        """
        Fetches live price (fast).
        """
        if not self.exchange: return 0.0

        try:
            base = symbol.split('/')[0] if '/' in symbol else symbol
            mapped = self.symbol_map.get(base, f"{base}/USDC:USDC")
            
            ticker = await self.exchange.fetch_ticker(mapped)
            
            # Priority: last -> close -> mark -> index
            price = ticker.get('last')
            if price is None: price = ticker.get('close')
            if price is None: price = ticker.get('markPrice')
            if price is None: price = ticker.get('indexPrice')
            
            return float(price) if price else 0.0
            
        except Exception as e:
            logger.error(f"Hyperliquid Ticker Error ({symbol}): {e}")
            return 0.0
