import ccxt.async_support as ccxt
import asyncio
import pandas as pd
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class HyperliquidAdapter:
    """
    Unified Adapter handling Hyperliquid with fallbacks to Coinbase/Kraken/BinanceUS.
    Name kept as HyperliquidAdapter to prevent import errors in Analyzer.
    """
    def __init__(self):
        self.exchanges = {}
        # Priority Order
        self.exchange_ids = ['hyperliquid', 'coinbase', 'kraken', 'binanceus']
        self._init_exchanges()

    def _init_exchanges(self):
        common_config = {
            'timeout': 10000,
            'enableRateLimit': True,
        }
        
        # Hyperliquid (Futures)
        try:
            self.exchanges['hyperliquid'] = ccxt.hyperliquid({
                **common_config,
                'options': {'defaultType': 'swap'}
            })
        except: pass
        
        # Coinbase (Spot - reliable US)
        try:
            self.exchanges['coinbase'] = ccxt.coinbase(common_config)
        except: pass
        
        # Kraken (Spot)
        try:
            self.exchanges['kraken'] = ccxt.kraken(common_config)
        except: pass
        
        # Binance US (Spot)
        try:
            self.exchanges['binanceus'] = ccxt.binanceus(common_config)
        except: pass
        
        logger.info(f"Initialized exchanges: {list(self.exchanges.keys())}")

    async def close(self):
        for name, exchange in self.exchanges.items():
            try:
                await exchange.close()
            except: pass

    async def restart(self):
        logger.info("Restarting Adapters...")
        await self.close()
        self.exchanges = {}
        self._init_exchanges()
        
    # --- Compatibility Stubs for CCXTAdapter ---
    async def update_cache(self, *args, **kwargs): pass
    async def backfill_history(self, *args, **kwargs): pass
    def save_cache(self): pass
    # -------------------------------------------

    def _map_symbol(self, exchange_id: str, symbol: str) -> str:
        """
        Maps generic 'BTC' to exchange-specific symbol.
        """
        base = symbol.split('/')[0] if '/' in symbol else symbol
        
        if exchange_id == 'hyperliquid':
            # Hyperliquid uses USDC:USDC notation often
            # Mapping common large caps
            mapping = {
                'BTC': 'BTC/USDC:USDC', 'ETH': 'ETH/USDC:USDC', 
                'SOL': 'SOL/USDC:USDC', 'XRP': 'XRP/USDC:USDC',
                'SUI': 'SUI/USDC:USDC', 'AVA': 'AVA/USDC:USDC'
            }
            return mapping.get(base, f"{base}/USDC:USDC")
            
        elif exchange_id == 'coinbase':
            # Coinbase uses BTC/USD
            return f"{base}/USD"
            
        elif exchange_id == 'kraken':
            # Kraken uses BTC/USD
            return f"{base}/USD"
            
        elif exchange_id == 'binanceus':
            # BinanceUS uses BTC/USDT or BTC/USD
            return f"{base}/USDT" # Higher volume usually
            
        return f"{base}/USDT"

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 1000) -> pd.DataFrame:
        """
        Fetch OHLCV with fallback strategy.
        """
        for eid in self.exchange_ids:
            exchange = self.exchanges.get(eid)
            if not exchange: continue
            
            try:
                mapped_symbol = self._map_symbol(eid, symbol)
                # Ensure timeframe compatibility if needed, but standard ones match
                
                # Fetch
                ohlcv = await exchange.fetch_ohlcv(mapped_symbol, timeframe, limit=limit)
                
                if not ohlcv or len(ohlcv) == 0:
                    continue

                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                df.set_index('timestamp', inplace=True)
                df.sort_index(inplace=True)
                
                logger.info(f"Fetched OHLCV from {eid} for {symbol}")
                return df
                
            except Exception as e:
                logger.warning(f"Failed to fetch OHLCV from {eid} for {symbol}: {e}")
                continue
                
        logger.error(f"All exchanges failed to fetch OHLCV for {symbol}")
        return pd.DataFrame()

    async def fetch_current_price(self, symbol: str) -> float:
        """
        Fetch live price with fallback strategy.
        """
        for eid in self.exchange_ids:
            exchange = self.exchanges.get(eid)
            if not exchange: continue
            
            try:
                mapped_symbol = self._map_symbol(eid, symbol)
                ticker = await exchange.fetch_ticker(mapped_symbol)
                
                price = None
                if eid == 'hyperliquid':
                    price = ticker.get('last') or ticker.get('close') or ticker.get('markPrice')
                else:
                    price = ticker.get('last') or ticker.get('close')
                
                if price and float(price) > 0:
                    return float(price)
                    
            except Exception as e:
                # logger.warning(f"Failed to fetch price from {eid} for {symbol}")
                continue
                
        logger.error(f"All exchanges failed to fetch PRICE for {symbol}")
        return 0.0
