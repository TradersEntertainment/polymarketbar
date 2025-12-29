import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from .datasources.ccxt_adapter import CCXTAdapter

class Analyzer:
    def __init__(self):
        self.adapter = CCXTAdapter()

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
        
        # Distribution Data (Histogram) with Last Happened Date
        same_color_streaks = streaks[streaks['color'] == current_streak_type]
        dist_counts = same_color_streaks['length'].value_counts()
        dist_last_times = same_color_streaks.groupby('length')['end_time'].max()
        
        distribution = {}
        for length in dist_counts.index:
            count = dist_counts[length]
            last_time = dist_last_times[length]
            distribution[int(length)] = {
                "count": int(count),
                "last_happened": last_time.strftime("%d.%m.%Y")
            }
        
        # Sort by length key
        distribution = dict(sorted(distribution.items()))

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
        duration_ms = self._get_timeframe_ms(timeframe)
        close_time = int(df.index[-1].timestamp() * 1000) + duration_ms

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "current_price": df['close'].iloc[-1],
            "candle_open": df['open'].iloc[-1],
            "candle_close_time": close_time,
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
                    "1m": "up" if df['close'].iloc[-1] > df['open'].iloc[-1] else "down", # Simple proxy
                    "5m": "up" if df['close'].iloc[-1] > df['close'].iloc[-5] else "down" if len(df) > 5 else "flat",
                    "15m": "up" if df['close'].iloc[-1] > df['close'].iloc[-15] else "down" if len(df) > 15 else "flat"
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
