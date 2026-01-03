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
        # Priority Order: Coinbase First (Speed/Reliability)
        self.exchange_ids = ['coinbase', 'kraken', 'binanceus', 'hyperliquid']
        self._init_exchanges()

    def _init_exchanges(self):
        common_config = {
            'timeout': 2500, # Fast failover (2.5s) to allow multiple fallbacks within frontend's 15s limit
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

    def _is_timeframe_supported(self, exchange_id: str, timeframe: str) -> bool:
        """
        Check if exchange supports the timeframe.
        Coinbase does not support 4h.
        """
        if exchange_id == 'coinbase' and timeframe == '4h':
            return False
        return True

    async def _fetch_from_exchange(self, eid: str, method: str, symbol: str, *args, **kwargs):
        """
        Helper to run a single exchange fetch.
        """
        exchange = self.exchanges.get(eid)
        if not exchange: return None

        # Timeframe Check for OHLCV
        if method == 'fetch_ohlcv':
            timeframe = args[0]
            if not self._is_timeframe_supported(eid, timeframe):
                return None

        try:
            mapped_symbol = self._map_symbol(eid, symbol)
            
            if method == 'fetch_ohlcv':
                # limit handled in args/kwargs usually
                result = await exchange.fetch_ohlcv(mapped_symbol, *args, **kwargs)
                if not result: return None
                
                # Format DataFrame immediately
                df = pd.DataFrame(result, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                df.set_index('timestamp', inplace=True)
                df.sort_index(inplace=True)
                return df
                
            elif method == 'fetch_ticker':
                ticker = await exchange.fetch_ticker(mapped_symbol)
                price = None
                if eid == 'hyperliquid':
                    price = ticker.get('last') or ticker.get('close') or ticker.get('markPrice')
                else:
                    price = ticker.get('last') or ticker.get('close')
                
                if price and float(price) > 0:
                    return float(price)
                    
        except Exception as e:
            # logger.debug(f"{eid} failed: {e}") 
            pass
            
        return None

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 1000) -> pd.DataFrame:
        """
        Parallel Race: Fetch from ALL exchanges simultaneously. Return first success.
        """
        tasks = []
        for eid in self.exchange_ids:
            tasks.append(
                asyncio.create_task(self._fetch_from_exchange(eid, 'fetch_ohlcv', symbol, timeframe, limit=limit))
            )
            
        try:
            # Wait for the FIRST one to complete successfully
            # effectively 'race' but we need to ignore failures until we find a success
            pending = set(tasks)
            while pending:
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    try:
                        result = task.result()
                        if result is not None and not result.empty:
                            # We have a winner!
                            # Cancel others (optional, but good for resources)
                            for p in pending: p.cancel()
                            return result
                    except: pass
                    
            logger.error(f"All exchanges failed OHLCV race for {symbol}")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Race Error: {e}")
            return pd.DataFrame()

    async def fetch_current_price(self, symbol: str) -> float:
        """
        Parallel Race for Price.
        """
        tasks = []
        for eid in self.exchange_ids:
            tasks.append(
                asyncio.create_task(self._fetch_from_exchange(eid, 'fetch_ticker', symbol))
            )

        try:
            pending = set(tasks)
            while pending:
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    try:
                        result = task.result()
                        if result is not None and result > 0:
                            for p in pending: p.cancel()
                            return result
                    except: pass
                    
            logger.error(f"All exchanges failed Price race for {symbol}")
            return 0.0
        except:
            return 0.0
