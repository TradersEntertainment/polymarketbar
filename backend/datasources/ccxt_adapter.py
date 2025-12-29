import ccxt.async_support as ccxt
import asyncio
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from .adapter_base import DataAdapter
import logging
import os

logger = logging.getLogger(__name__)

class CCXTAdapter(DataAdapter):
    def __init__(self):
        self.exchanges = [
            ccxt.binance({'timeout': 10000, 'enableRateLimit': True}),
            ccxt.coinbase({'timeout': 10000, 'enableRateLimit': True}),
            ccxt.kraken({'timeout': 10000, 'enableRateLimit': True})
        ]
        # Map common symbols to exchange-specific symbols
        self.symbol_map = {
            'BTC': {'binance': 'BTC/USDT', 'coinbase': 'BTC/USD', 'kraken': 'BTC/USD'},
            'ETH': {'binance': 'ETH/USDT', 'coinbase': 'ETH/USD', 'kraken': 'ETH/USD'},
            'SOL': {'binance': 'SOL/USDT', 'coinbase': 'SOL/USD', 'kraken': 'SOL/USD'},
            'XRP': {'binance': 'XRP/USDT', 'coinbase': 'XRP/USD', 'kraken': 'XRP/USD'},
        }
        # In-memory cache: { "SYMBOL_TIMEFRAME": pd.DataFrame }
        self.cache: Dict[str, pd.DataFrame] = {}
        # Short-term price cache: { "SYMBOL": (price, timestamp) }
        self.price_cache: Dict[str, tuple] = {}
        
        # Persistence
        self.DATA_DIR = "/data" if os.path.exists("/data") else "." 
        self.CACHE_FILE = os.path.join(self.DATA_DIR, "ohlcv_cache.pkl")
        
        self.load_cache()

    def load_cache(self):
        if os.path.exists(self.CACHE_FILE):
            try:
                import pickle
                with open(self.CACHE_FILE, 'rb') as f:
                    self.cache = pickle.load(f)
                logger.info(f"Loaded persist cache from {self.CACHE_FILE}. Keys: {list(self.cache.keys())}")
            except Exception as e:
                logger.error(f"Failed to load cache: {e}")
        else:
            logger.info("No persistent cache found. Starting fresh.")

    def save_cache(self):
        try:
            import pickle
            # Create temp file then rename for atomic write
            temp_file = self.CACHE_FILE + ".tmp"
            with open(temp_file, 'wb') as f:
                pickle.dump(self.cache, f)
            os.replace(temp_file, self.CACHE_FILE)
            logger.info(f"Saved cache to {self.CACHE_FILE}")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    async def close(self):
        for exchange in self.exchanges:
            await exchange.close()

    async def restart(self):
        """
        Closes current connections and re-initializes exchanges.
        Useful for long-running processes where connections might stale.
        """
        logger.info("Restarting CCXT Adapter...")
        await self.close()
        
        # Re-init exchanges
        self.exchanges = [
            ccxt.binance({'timeout': 10000, 'enableRateLimit': True}),
            ccxt.coinbase({'timeout': 10000, 'enableRateLimit': True}),
            ccxt.kraken({'timeout': 10000, 'enableRateLimit': True})
        ]
        logger.info("CCXT Adapter restarted successfully.")

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 1000) -> pd.DataFrame:
        """
        Returns cached data if available.
        For 4h and 1d, we return the cached resampled data.
        """
        key = f"{symbol}_{timeframe}"
        
        # If we have it in cache, return immediately (fastest)
        if key in self.cache:
            return self.cache[key]
            
        # If not, we need to update.
        # For 4h/1d, this means updating 1h, which triggers resampling.
        if timeframe in ['4h', '1d']:
            await self.update_cache(symbol, '1h')
            # After update, it should be in cache
            return self.cache.get(key, pd.DataFrame())
        
        # For 15m/1h, standard update
        await self.update_cache(symbol, timeframe)
        return self.cache.get(key, pd.DataFrame())

    def resample_ohlcv(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Resample 1h data to custom timeframe.
        Polymarket Daily: 12:00 ET to 12:00 ET (Noon).
        """
        if df.empty:
            return df
            
        # Ensure index is datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index, utc=True)
            
        # Convert to US/Eastern to handle DST automatically
        df_et = df.tz_convert('US/Eastern')
        
        # Use a fixed origin to ensure stable alignment
        # We use a recent date to ensure no timezone weirdness (though US/Eastern handles it)
        # 2024-01-01 is a Monday.
        midnight_et = pd.Timestamp("2024-01-01 00:00:00").tz_localize("US/Eastern")
        
        if timeframe == '1d':
            # Daily closes at 12:00 PM (Noon) ET.
            # Origin at 12:00 PM ensures bins are 12:00 -> 12:00.
            origin = midnight_et + pd.Timedelta(hours=12)
            rule = '24h'
        elif timeframe == '4h':
            # 4h candles should align to 00, 04, 08, 12, 16, 20.
            # Midnight origin covers this perfectly.
            origin = midnight_et
            rule = '4h'
        else:
            origin = midnight_et
            rule = timeframe
        
        # Resample
        # close='right', label='right' is default for M/D/Y but usually left for lower freqs.
        # We want the timestamp to represent the CLOSE time usually in this app context 
        # (calculated elsewhere as end_time). 
        # Standard OHLVC usually uses OPEN time as the label. 
        # CCXT/Lightweight charts verify this.
        # Let's keep default behavior but ensure origin is correct.
        resampled = df_et.resample(rule, origin=origin).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        
        return resampled.dropna()

    async def update_cache(self, symbol: str, timeframe: str):
        # If 4h/1d requested, we redirect to 1h update
        if timeframe in ['4h', '1d']:
            await self.update_cache(symbol, '1h')
            return

        key = f"{symbol}_{timeframe}"
        current_df = self.cache.get(key)
        
        try:
            # Case 1: Updating existing cache (Fast)
            if current_df is not None and not current_df.empty:
                last_ts = current_df.index[-1].value // 10**6
                # Fetch only new data
                new_data = await self._fetch_aggregated_ohlcv(symbol, timeframe, limit=100, since=last_ts)
                
                if new_data.empty:
                    if timeframe == '1h': self._update_derived_cache(symbol)
                    return

                combined = pd.concat([current_df, new_data])
                combined = combined[~combined.index.duplicated(keep='last')]
                combined.sort_index(inplace=True)
                
                # Keep up to 10,000 candles
                if len(combined) > 10000:
                    combined = combined.iloc[-10000:]
                
                self.cache[key] = combined
                logger.info(f"Updated cache for {key}. New total: {len(combined)}")

            # Case 2: Initial Deep Fetch (DISABLED FOR DEBUGGING/STABILITY)
            else:
                 # Standard fetch for new cache
                 logger.info(f"Initializing cache for {key} (Standard fetch)...")
                 new_data = await self._fetch_aggregated_ohlcv(symbol, timeframe, limit=1000)
                 if not new_data.empty:
                     self.cache[key] = new_data
                     
            # Trigger derived cache update if we just updated 1h
            if timeframe == '1h':
                self._update_derived_cache(symbol)
                
        except Exception as e:
            logger.error(f"Failed to update cache for {key}: {e}")

    def _update_derived_cache(self, symbol: str):
        """
        Resamples 1h data to 4h and 1d and updates their caches.
        """
        df_1h = self.cache.get(f"{symbol}_1h")
        if df_1h is None or df_1h.empty:
            return

        # Resample to 4h
        df_4h = self.resample_ohlcv(df_1h, '4h')
        self.cache[f"{symbol}_4h"] = df_4h
        
        # Resample to 1d
        df_1d = self.resample_ohlcv(df_1h, '1d')
        self.cache[f"{symbol}_1d"] = df_1d
        
        # logger.info(f"Updated derived cache (4h/1d) for {symbol}")

    async def _fetch_aggregated_ohlcv(self, symbol: str, timeframe: str, limit: int, since: Optional[int] = None) -> pd.DataFrame:
        tasks = [self._fetch_full_ohlcv(ex, symbol, timeframe, limit, since) for ex in self.exchanges]
        results = await asyncio.gather(*tasks)
        
        dfs = [df for df in results if not df.empty]
        if not dfs:
            return pd.DataFrame()

        # Concatenate all
        all_data = pd.concat(dfs)
        
        # Group by index (timestamp) and take median
        aggregated = all_data.groupby(all_data.index).median()
        
        if not aggregated.empty:
            last_close = aggregated['close'].iloc[-1]
            # logger.info(f"Aggregated {timeframe} candle for {symbol}: {last_close} (from {len(dfs)} exchanges)")
            if last_close > 250000 and symbol == 'BTC':
                 logger.error(f"ANOMALY DETECTED: BTC price {last_close} > 250k! Data breakdown: {[d['close'].iloc[-1] for d in dfs]}")

        return aggregated.sort_index()

    async def _fetch_full_ohlcv(self, exchange, symbol: str, timeframe: str, limit: int, since: Optional[int] = None) -> pd.DataFrame:
        try:
            base_currency = symbol.split('/')[0] if '/' in symbol else symbol
            mapped_symbol = self.symbol_map.get(base_currency, {}).get(exchange.id)
            if not mapped_symbol:
                mapped_symbol = f"{base_currency}/USDT" if exchange.id == 'binance' else f"{base_currency}/USD"
            
            # logger.info(f"Fetching {mapped_symbol} from {exchange.id} ({timeframe}) since={since}...")
            ohlcv = await asyncio.wait_for(exchange.fetch_ohlcv(mapped_symbol, timeframe, limit=limit, since=since), timeout=10.0)
            # logger.info(f"Fetched {len(ohlcv)} candles from {exchange.id}")
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            # logger.warning(f"Error {exchange.id}: {e}")
            return pd.DataFrame()

    async def fetch_current_price(self, symbol: str) -> float:
        # Check cache (TTL 2 seconds)
        import time
        now = time.time()
            
        if symbol in self.price_cache:
            price, ts = self.price_cache[symbol]
            if now - ts < 2.0: # 2 second cache
                return price

        # Similar logic for ticker
        tasks = []
        for ex in self.exchanges:
            base = symbol.split('/')[0] if '/' in symbol else symbol
            mapped = self.symbol_map.get(base, {}).get(ex.id)
            if not mapped:
                mapped = f"{base}/USDT" if ex.id == 'binance' else f"{base}/USD"
            tasks.append(asyncio.wait_for(ex.fetch_ticker(mapped), timeout=5.0))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        prices = []
        for r in results:
            if isinstance(r, dict) and 'last' in r:
                prices.append(r['last'])
                
        if not prices:
            return 0.0
            
        median_price = float(np.median(prices))
        
        # Update cache
        self.price_cache[symbol] = (median_price, now)
        
        return median_price


