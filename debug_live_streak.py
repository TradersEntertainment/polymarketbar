import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
import datetime

async def get_candles(symbol):
    exchange = ccxt.binance()
    try:
        print(f"Fetching {symbol} 15m...")
        ohlcv = await exchange.fetch_ohlcv(symbol, '15m', limit=20)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['dt'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    finally:
        await exchange.close()

def calculate_stats(df):
    df['color'] = np.where(df['close'] >= df['open'], 'green', 'red')
    df['streak_group'] = (df['color'] != df['color'].shift()).cumsum()
    
    streaks = df.groupby('streak_group').agg(
        color=('color', 'first'),
        length=('color', 'count'),
        end_time=('dt', 'max')
    )
    return df, streaks

async def main():
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT']
    
    for sym in symbols:
        df = await get_candles(sym)
        if df.empty:
            print(f"No data for {sym}")
            continue
            
        df, streaks = calculate_stats(df)
        
        print(f"\n=== {sym} Analysis ===")
        # Show last 5 candles
        print(df[['dt', 'open', 'close', 'color', 'streak_group']].tail(5))
        
        current_streak = streaks.iloc[-1]
        print(f"CALCULATED STREAK: {int(current_streak['length'])} {current_streak['color'].upper()}")
        
        # Manual verification text
        last_color = df['color'].iloc[-1]
        count = 0
        for i in range(len(df)-1, -1, -1):
            if df['color'].iloc[i] == last_color:
                count += 1
            else:
                break
        print(f"MANUAL VERIFICATION: {count} {last_color.upper()}")
        
        if count != current_streak['length']:
            print("MISMATCH DETECTED!")

if __name__ == "__main__":
    asyncio.run(main())
