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
        # Initialize exchanges in priority order
        # Hyperliquid -> Coinbase Futures -> Coinbase Spot -> Kraken -> Binance (Deprioritized)
        self.exchanges = []
        # Patched for Railway IP Block: Prioritize Coinbase -> Kraken -> Binance -> Hyperliquid
        
        self.exchanges.append(ccxt.coinbase({'timeout': 5000, 'enableRateLimit': True}))
        self.exchanges.append(ccxt.kraken({'timeout': 5000, 'enableRateLimit': True}))
        self.exchanges.append(ccxt.binance({'timeout': 5000, 'enableRateLimit': True}))
        
        try: self.exchanges.append(ccxt.coinbaseinternational({'timeout': 5000, 'enableRateLimit': True}))
        except: pass

        # DISABLE HYPERLIQUID COMPLETELY (Causes crashes on Railway due to IP block + CancelledError propagation)
        # try: self.exchanges.append(ccxt.hyperliquid({'timeout': 5000, 'enableRateLimit': True}))
        # except: pass

        # Map common symbols to exchange-specific symbols
        self.symbol_map = {
            'BTC': {
                'binance': 'BTC/USDT', 
                'coinbase': 'BTC/USD', 
                'kraken': 'BTC/USD', 
                'hyperliquid': 'BTC/USDC:USDC',
                'coinbaseinternational': 'BTC/USDC:USDC'
            },
            'ETH': {
                'binance': 'ETH/USDT', 
                'coinbase': 'ETH/USD', 
                'kraken': 'ETH/USD',
                'hyperliquid': 'ETH/USDC:USDC',
                'coinbaseinternational': 'ETH/USDC:USDC'
            },
            'SOL': {
                'binance': 'SOL/USDT', 
                'coinbase': 'SOL/USD', 
                'kraken': 'SOL/USD',
                'hyperliquid': 'SOL/USDC:USDC',
                'coinbaseinternational': 'SOL/USDC:USDC'
            },
            'XRP': {
                'binance': 'XRP/USDT', 
                'coinbase': 'XRP/USD', 
                'kraken': 'XRP/USD',
                'hyperliquid': 'XRP/USDC:USDC',
                'coinbaseinternational': 'XRP/USDC:USDC'
            },
        }
        # In-memory cache: { "SYMBOL_TIMEFRAME": pd.DataFrame }
        self.cache: Dict[str, pd.DataFrame] = {}
        # Short-term price cache: { "SYMBOL": (price, timestamp) }
        self.price_cache: Dict[str, tuple] = {}
        
        # Persistence
        self.DATA_DIR = "/data" if os.path.exists("/data") else "." 
        self.CACHE_FILE = os.path.join(self.DATA_DIR, "ohlcv_cache.pkl")
        
        # Concurrency Lock
        self.update_lock = asyncio.Lock()
        
        # Throttling
        self.last_update: Dict[str, float] = {}
        
        self.load_cache()

    def load_cache(self):
        if os.path.exists(self.CACHE_FILE):
            try:
                import pickle
                with open(self.CACHE_FILE, 'rb') as f:
                    self.cache = pickle.load(f)
                
                # Reset throttling timers on load to ensure we fetch fresh data immediately on startup
                self.last_update = {} 
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
        
        # Re-init exchanges (Same logic as __init__)
        self.exchanges = []
        try: self.exchanges.append(ccxt.hyperliquid({'timeout': 10000, 'enableRateLimit': True}))
        except: pass
        try: self.exchanges.append(ccxt.coinbaseinternational({'timeout': 10000, 'enableRateLimit': True}))
        except: pass
        self.exchanges.append(ccxt.coinbase({'timeout': 10000, 'enableRateLimit': True}))
        self.exchanges.append(ccxt.kraken({'timeout': 10000, 'enableRateLimit': True}))
        self.exchanges.append(ccxt.binance({'timeout': 10000, 'enableRateLimit': True}))
        
        logger.info("CCXT Adapter restarted successfully.")

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 1000) -> pd.DataFrame:
        """
        Returns cached data. If missing, triggers immediate update (Hybrid Mode).
        For 4h and 1d, this ensures resampling happens if 1h is available.
        """
        key = f"{symbol}_{timeframe}"
        data = self.cache.get(key, pd.DataFrame())
        
        # If cash miss or empty, fetch immediately
        if data.empty:
            logger.info(f"Cache miss for {key}, fetching immediately...")
            
            # For 4h/1d, we need 1h update logic which handles recursion
            if timeframe in ['4h', '1d']:
                await self.update_cache(symbol, '1h')
            else:
                await self.update_cache(symbol, timeframe)
                
            return self.cache.get(key, pd.DataFrame())
            
        return data

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
            # We use a fixed recent origin.
            origin = pd.Timestamp("2024-01-01 12:00:00").tz_localize("US/Eastern")
            rule = '24h'
        elif timeframe == '4h':
            # 4h candles align to 00, 04, 08...
            origin = pd.Timestamp("2024-01-01 00:00:00").tz_localize("US/Eastern")
            rule = '4h'
        else:
            origin = pd.Timestamp("2024-01-01 00:00:00").tz_localize("US/Eastern")
            rule = timeframe
        
        # Ensure sorted
        df_et = df_et.sort_index()

        # Strategy 1: Strict Noon ET (Preferred)
        try:
            resampled = df_et.resample(rule, origin=origin).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })
            # Check if valid
            # Allow partial last bin by NOT dropping all NaNs if we have at least some data
            # But we want to avoid completely empty rows.
            # partial bins usually have data, just maybe 'volume' missing? No, pandas resample handles it.
            # The issue is probably that the first bin is partial and getting dropped?
            # Let's just return resampled if not empty, without strict dropna if it kills everything.
            if not resampled.empty:
                # Only drop execution errors (all-NaN rows), keep partials
                clean = resampled.dropna(how='all')
                if not clean.empty:
                    return clean
            
            logger.warning(f"Strategy 1 (Strict) returned empty for {timeframe}. Trying fallback...")
        except Exception as e:
            logger.error(f"Strategy 1 failed for {timeframe}: {e}")

        # Strategy 2: Simple/Standard Resampling (Fallback)
        # Just use standard daily/4h without custom origin if the above fails
        try:
            fallback_rule = '1D' if timeframe == '1d' else '4h'
            fallback = df_et.resample(fallback_rule).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })
            clean_fallback = fallback.dropna()
            if not clean_fallback.empty:
                logger.info(f"Strategy 2 (Fallback) succeeded for {timeframe}.")
                return clean_fallback
        except Exception as e:
             logger.error(f"Strategy 2 failed for {timeframe}: {e}")

        return pd.DataFrame()

    async def update_cache(self, symbol: str, timeframe: str):
        # If 4h/1d requested, we redirect to 1h update
        if timeframe in ['4h', '1d']:
            await self.update_cache(symbol, '1h')
            return

        key = f"{symbol}_{timeframe}"
        
        # Use simple locking to prevent thundering herd
        async with self.update_lock:
            # Throttling/Cooldown: Don't hit API if updated recently (e.g. 10s)
            import time
            now = time.time()
            last_ts = self.last_update.get(key, 0)
            if now - last_ts < 10.0:
                 # Cache is fresh enough
                 return

            # Check cache again inside lock (Double-Check Pattern)
            if key in self.cache and timeframe not in ['4h', '1d']:
                pass

            current_df = self.cache.get(key)
            
            try:
                # Case 1: Updating existing cache (Fast)
                if current_df is not None and not current_df.empty:
                    last_ts_val = current_df.index[-1].value // 10**6
                    # Fetch only new data
                    new_data = await self._fetch_aggregated_ohlcv(symbol, timeframe, limit=100, since=last_ts_val)
                    
                    if new_data.empty:
                        self.last_update[key] = now  # Mark check as done even if empty
                        if timeframe == '1h': self._update_derived_cache(symbol)
                        return

                    combined = pd.concat([current_df, new_data])
                    combined = combined[~combined.index.duplicated(keep='last')]
                    combined.sort_index(inplace=True)
                    
                    # Keep up to 10,000 candles
                    if len(combined) > 10000:
                        combined = combined.iloc[-10000:]
                    
                    self.cache[key] = combined
                    self.last_update[key] = now
                    logger.info(f"Updated cache for {key}. New total: {len(combined)}")

                # Case 2: Initial Deep Fetch (DISABLED FOR DEBUGGING/STABILITY)
                else:
                     # Standard fetch for new cache
                     logger.info(f"Initializing cache for {key} (Standard fetch)...")
                     new_data = await self._fetch_aggregated_ohlcv(symbol, timeframe, limit=1000)
                     if not new_data.empty:
                         self.cache[key] = new_data
                         self.last_update[key] = now
                         
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
                # Default logic if map misses
                if exchange.id == 'binance': mapped_symbol = f"{base_currency}/USDT"
                elif 'coinbase' in exchange.id: mapped_symbol = f"{base_currency}/USD" 
                elif 'hyperliquid' in exchange.id: mapped_symbol = f"{base_currency}/USDC:USDC"
                else: mapped_symbol = f"{base_currency}/USD"
            
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

    async def backfill_history(self, symbol: str, timeframe: str = '1h', days: int = 30):
        """
        Fetches deep history (backfill) for a symbol.
        Used primarily for 1h data to ensure robust 4h/1d resampling.
        Iterates through exchanges until one works.
        """
        import time
        logger.info(f"Backfilling {symbol} {timeframe} for {days} days...")
        
        target_hours = days * 24
        if timeframe != '1h':
            pass
            
        start_ts = int(time.time() * 1000) - (days * 86400 * 1000)
        
        # Try each exchange in priority order
        for exchange in self.exchanges:
            logger.info(f"Attempting backfill on {exchange.id}...")
            
            current_since = start_ts
            all_candles = []
            failed_exchange = False
            
            # Map symbol
            base_currency = symbol.split('/')[0] if '/' in symbol else symbol
            mapped_symbol = self.symbol_map.get(base_currency, {}).get(exchange.id)
            
            if not mapped_symbol:
                # Basic fallback
                if 'hyperliquid' in exchange.id: mapped_symbol = f"{base_currency}/USDC:USDC"
                elif 'coinbase' in exchange.id: mapped_symbol = f"{base_currency}/USD" # Covers intl too mostly
                else: mapped_symbol = f"{base_currency}/USDT"
                
                # Careful with Coinbase futures if not mapped
                if exchange.id == 'coinbaseinternational': mapped_symbol = f"{base_currency}/USDC:USDC"

            try:
                while True:
                    # Don't fetch future
                    if current_since > int(time.time() * 1000):
                        break
                        
                    try:
                        ohlcv = await exchange.fetch_ohlcv(mapped_symbol, timeframe, since=current_since, limit=1000)
                    except (ccxt.NetworkError, ccxt.ExchangeError) as e:
                        # If HTTP 451 or other block, this exchange is dead for us
                        if "451" in str(e):
                            logger.warning(f"{exchange.id} gave 451 (Restricted). Skipping exchange.")
                        else:
                            logger.warning(f"{exchange.id} fetch error: {e}")
                        failed_exchange = True
                        break

                    if not ohlcv:
                        break
                    
                    all_candles.extend(ohlcv)
                    
                    last_ts = ohlcv[-1][0]
                    # If we caught up to now (approx), break
                    if last_ts >= int(time.time() * 1000) - 3600000:
                        break
                        
                    if last_ts == current_since:
                        current_since += 1
                    else:
                        current_since = last_ts + 1
                    
                    await asyncio.sleep(0.5) # Respect rate limits

                if failed_exchange:
                    continue # Try next exchange

                if all_candles:
                    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                    df.set_index('timestamp', inplace=True)
                    
                    # Update Cache
                    key = f"{symbol}_{timeframe}"
                    existing = self.cache.get(key, pd.DataFrame())
                    
                    combined = pd.concat([existing, df])
                    combined = combined[~combined.index.duplicated(keep='last')].sort_index()
                    
                    self.cache[key] = combined
                    # Trigger derived updates (4h/1d)
                    self._update_derived_cache(symbol)
                    return # Success! Exit function

            except Exception as e:
                logger.error(f"Backfill loop error on {exchange.id}: {e}")
                continue # Try next exchange
        
        logger.error(f"All exchanges failed to backfill {symbol}")

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
                if 'hyperliquid' in ex.id: mapped = f"{base}/USDC:USDC"
                elif 'coinbase' in ex.id: mapped = f"{base}/USD" # International uses USDC but spot uses USD
                elif ex.id == 'binance': mapped = f"{base}/USDT"
                else: mapped = f"{base}/USD"

            # Create a task for each exchange and track them
            t = asyncio.create_task(self._safe_fetch_ticker(ex, mapped))
            tasks.append(t)
            
        # Process as they complete (First Success Wins)
        try:
            for future in asyncio.as_completed(tasks):
                try:
                    price = await future
                    if price > 0:
                        # Update cache and return immediately
                        self.price_cache[symbol] = (price, now)
                        
                        # Cancel remaining tasks to free connections
                        for t in tasks:
                            if not t.done():
                                t.cancel()
                                
                        return price
                except Exception:
                    continue
        except Exception as e:
            # Fallback cancellation
            for t in tasks:
                if not t.done(): t.cancel()
            logger.error(f"Error in fetch_current_price: {e}")
                
        # If all failed (or returned 0)
        return 0.0

    async def _safe_fetch_ticker(self, exchange, symbol: str) -> float:
        try:
            # Short timeout for live checks
            ticker = await asyncio.wait_for(exchange.fetch_ticker(symbol), timeout=5.0)
            
            # Helper to get first valid price
            price = ticker.get('last')
            if price is None: price = ticker.get('close')
            if price is None: price = ticker.get('markPrice')
            if price is None: price = ticker.get('indexPrice')
            
            if price is not None:
                return float(price)
            return 0.0
        except Exception:
            return 0.0



