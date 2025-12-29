import json
import os
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from .datasources.ccxt_adapter import CCXTAdapter

class Analyzer:
    def __init__(self):
        self.adapter = CCXTAdapter()
        self.HISTORY_FILE = "/data/streak_history.json" if os.path.exists("/data") else "streak_history.json"
        self._load_history()

    def _load_history(self):
        self.history = {}
        if os.path.exists(self.HISTORY_FILE):
            try:
                with open(self.HISTORY_FILE, 'r') as f:
                    self.history = json.load(f)
            except: pass

    def _save_history(self):
        try:
            with open(self.HISTORY_FILE, 'w') as f:
                json.dump(self.history, f)
        except: pass

    def _update_and_get_distribution(self, symbol, timeframe, streaks_df, active_color):
        key = f"{symbol}_{timeframe}"
        if key not in self.history:
            self.history[key] = {"last_processed_ts": 0, "green": {"counts": {}, "last_happened": {}}, "red": {"counts": {}, "last_happened": {}}}
        
        hist = self.history[key]
        last_ts = hist["last_processed_ts"]
        
        completed_streaks = streaks_df.iloc[:-1]
        
        updated = False
        for _, row in completed_streaks.iterrows():
            end_time_ts = row['end_time']
            end_ts_ms = int(end_time_ts.timestamp() * 1000)
            
            if end_ts_ms > last_ts:
                color = row['color'] # 'green' or 'red'
                length = str(row['length'])
                
                # Safety for unexpected colors
                if color not in ['green', 'red']: continue
                
                sub_hist = hist[color]
                sub_hist["counts"][length] = sub_hist["counts"].get(length, 0) + 1
                sub_hist["last_happened"][length] = max(sub_hist["last_happened"].get(length, 0), end_ts_ms)
                
                hist["last_processed_ts"] = max(hist["last_processed_ts"], end_ts_ms)
                updated = True
        
        if updated:
            self._save_history()
            
        # Return distribution for ACTIVE color
        if active_color not in ['green', 'red']: return {}
        
        target_data = hist[active_color]
        dist_out = {}
        for length_str, count in target_data["counts"].items():
            last_ts_val = target_data["last_happened"].get(length_str, 0)
            date_str = pd.to_datetime(last_ts_val, unit='ms').strftime("%d.%m.%Y")
            dist_out[int(length_str)] = {
                "count": count,
                "last_happened": date_str
            }
            
        return dict(sorted(dist_out.items()))

    def _get_timeframe_ms(self, tf: str) -> int:
        if not tf: return 0
        unit = tf[-1]
        if not tf[:-1].isdigit(): return 0
        value = int(tf[:-1])
        if unit == 'm': return value * 60 * 1000
        if unit == 'h': return value * 60 * 60 * 1000
        if unit == 'd': return value * 24 * 60 * 60 * 1000
        return 0

    async def get_stats(self, symbol: str, timeframe: str):
        # Request more data (5000 candles) to ensure accurate streak history
        df = await self.adapter.fetch_ohlcv(symbol, timeframe, limit=5000)
        if df.empty:
            return None

        # --- SYNC WITH LIVE PRICE ---
        # Overwrite the last candle's close with the real-time price to ensure instant streak updates
        try:
            live_price = await self.adapter.fetch_current_price(symbol)
            if live_price > 0:
                # Update the last row's close price
                # We use .iloc[-1, index_of_close] to be safe
                close_col_idx = df.columns.get_loc('close')
                df.iloc[-1, close_col_idx] = live_price
        except Exception:
            pass # Fail silently and use cached close if live fetch fails
        # -----------------------------

        # Determine candle colors (Close > Open: Green, Close < Open: Red)
        # For flat candles (Close == Open), we continue the previous color (Trend persistence)
        conditions = [
            df['close'] > df['open'],
            df['close'] < df['open']
        ]
        choices = ['green', 'red']
        
        # Use select to assign colors, defaulting to None (NaN) for flat candles
        df['color'] = np.select(conditions, choices, default=None)
        
        # Forward fill to propagate previous color to flat candles
        df['color'] = df['color'].ffill()
        
        # Fallback: If the very first candle is flat, default to Green (or Red, arbitrary but needed)
        df['color'] = df['color'].fillna('green')
        
        # Calculate streaks
        df['ts'] = df.index
        df['streak_group'] = (df['color'] != df['color'].shift()).cumsum()
        
        streaks = df.groupby('streak_group').agg(
            color=('color', 'first'),
            length=('color', 'count'),
            end_time=('ts', 'max')
        )
        
        # Current streak
        current_streak_node = streaks.iloc[-1]
        current_streak_type = current_streak_node['color']
        current_streak_len = current_streak_node['length']
        
        # Historical Probability Logic
        
        # Count all streaks of this color with length >= N
        total_instances_reaching_N = len(streaks[
            (streaks['color'] == current_streak_type) & 
            (streaks['length'] >= current_streak_len)
        ])
        
        # Count all streaks of this color with length > N (meaning it continued)
        instances_continuing = len(streaks[
            (streaks['color'] == current_streak_type) & 
            (streaks['length'] > current_streak_len)
        ])
        
        # Probability to continue (Streak increases)
        if total_instances_reaching_N <= 1:
            # Only the current streak has reached this length (New Record)
            prob_continue = None
            prob_reverse = None
        else:
            prob_continue = instances_continuing / total_instances_reaching_N
            prob_reverse = 1.0 - prob_continue
        
        # Distribution Data (Persistent Accumulator)
        # Using persistent history to track all-time stats even if cache is short
        distribution = self._update_and_get_distribution(symbol, timeframe, streaks, current_streak_type)

        # --- NEW METRICS ---
        
        # 1. Volatility (Last 100 candles standard deviation of % returns)
        df['returns'] = df['close'].pct_change()
        vol_std = df['returns'].tail(100).std()
        volatility = (vol_std * 100) if pd.notna(vol_std) else 0.0 # In percentage
        
        # 2. Streak Stats
        avg_streak = streaks['length'].mean()
        max_streak = streaks['length'].max()
        
        # 3. Conditional Probability Curve
        # Calculate probability of continuing for streaks 1 to 10
        prob_curve = []
        for i in range(1, 13): # 1 to 12
            # Find streaks of this length (regardless of color for general "continuation" prob, 
            # or specific to current color? User asked for "Probability After Streak Length".
            # Usually streaks behave similarly regardless of direction in crypto, but let's stick to current color for precision
            # or maybe aggregate both for more data? 
            # Let's use the current streak color to be specific.
            
            total_at_i = len(streaks[(streaks['color'] == current_streak_type) & (streaks['length'] >= i)])
            continued_after_i = len(streaks[(streaks['color'] == current_streak_type) & (streaks['length'] > i)])
            
            prob = (continued_after_i / total_at_i * 100) if total_at_i > 0 else 0
            prob_curve.append({"length": i, "prob": round(prob, 1)})

        # Duration Calculation for Close Time
        # Robust Wall-Clock Calculation (Decoupled from data freshness)
        # Polymarket uses US/Eastern Time alignment (Daily at Noon ET)
        import time
        now_ts = time.time()
        
        try:
            now_et = pd.Timestamp.now(tz='US/Eastern')
            
            if timeframe == '1d':
                # Target: Next Noon (12:00:00) ET
                target = now_et.replace(hour=12, minute=0, second=0, microsecond=0)
                if now_et >= target:
                    target += pd.Timedelta(days=1)
                close_time = int(target.timestamp() * 1000)
                
            elif timeframe == '4h':
                # Target: Next 0, 4, 8, 12, 16, 20
                current_hour = now_et.hour
                # Find next multiple of 4
                next_hour = (current_hour // 4 + 1) * 4
                
                target = now_et.replace(minute=0, second=0, microsecond=0)
                if next_hour >= 24:
                    target = target.replace(hour=0) + pd.Timedelta(days=1)
                else:
                    target = target.replace(hour=next_hour)
                
                close_time = int(target.timestamp() * 1000)
                
            else:
                # 15m, 1h - These align cleanly with UTC standard logic
                # 1h: Top of next hour
                # 15m: Next 0, 15, 30, 45
                duration_s = self._get_timeframe_ms(timeframe) / 1000
                if duration_s > 0:
                     next_boundary = ((int(now_ts) // int(duration_s)) + 1) * int(duration_s)
                     close_time = next_boundary * 1000
                else:
                     close_time = int(df.index[-1].timestamp() * 1000) + self._get_timeframe_ms(timeframe)

        except Exception as e:
            # Fallback in case of timezone errors
            print(f"Timezone calc error: {e}")
            duration_s = self._get_timeframe_ms(timeframe) / 1000
            if duration_s > 0:
                 next_boundary = ((int(now_ts) // int(duration_s)) + 1) * int(duration_s)
                 close_time = next_boundary * 1000
            else:
                 close_time = int(df.index[-1].timestamp() * 1000) + self._get_timeframe_ms(timeframe)

        # Check for staleness (if data is older than 2x timeframe)
        last_data_ts = df.index[-1].timestamp()
        duration_s = self._get_timeframe_ms(timeframe) / 1000
        is_stale = (now_ts - last_data_ts) > (duration_s * 2) if duration_s > 0 else False

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "current_price": df['close'].iloc[-1],
            "candle_open": df['open'].iloc[-1],
            "candle_close_time": close_time,
            "is_stale": is_stale,
            "current_streak": {
                "type": current_streak_type,
                "length": int(current_streak_len)
            },
            "next_candle_prob": {
                "continue": round(prob_continue * 100, 1) if prob_continue is not None else None,
                "reverse": round(prob_reverse * 100, 1) if prob_reverse is not None else None
            },
            "stats": {
                "volatility": round(volatility, 2),
                "avg_streak": round(avg_streak, 1),
                "max_streak": int(max_streak)
            },
            "smart_trading": {
                "microtrends": {
                    "1m": "up" if df['close'].iloc[-1] > df['open'].iloc[-1] else "down",
                    "5m": ("up" if df['close'].iloc[-1] > df['close'].iloc[-5] else "down") if len(df) > 5 else "flat",
                    "15m": ("up" if df['close'].iloc[-1] > df['close'].iloc[-15] else "down") if len(df) > 15 else "flat"
                },
                "spread": round(volatility * 0.05, 4), # Simulated spread based on vol
                "slippage": round(volatility * 0.02, 4),
                "smart_exit": {
                    "optimal_price": round(df['close'].iloc[-1] * (1.0 + (volatility/100 * 0.5)), 2),
                    "offset_pct": round(volatility * 0.5, 1),
                    "liquidity_tightness": "High" if volatility > 1.0 else "Medium" if volatility > 0.5 else "Low",
                    "est_fill_time_ms": int(200 + (volatility * 100))
                },
                "whipsaw_risk": {
                    "probability": round(len(df[((df['high'] - df['low']) > 0) & ((abs(df['open'] - df['close']) / (df['high'] - df['low'])) < 0.4)]) / len(df) * 100, 1),
                    "category": "High" if volatility > 2.0 else "Normal" if volatility > 1.0 else "Low"
                }
            },
            "distribution": distribution,
            "probability_curve": prob_curve,
            "total_candles": len(df),
            "debug_candles": [
                {
                    "time": str(df.index[i]),
                    "open": df.iloc[i]['open'],
                    "close": df.iloc[i]['close'],
                    "color": df.iloc[i]['color']
                } for i in range(max(0, len(df)-5), len(df))
            ]
        }

    async def close(self):
        await self.adapter.close()

    async def restart(self):
        await self.adapter.restart()
