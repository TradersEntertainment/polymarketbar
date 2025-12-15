import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import datetime

async def debug_btc_15m():
    print("Connecting to Binance...")
    exchange = ccxt.binance()
    try:
        # Fetch last 10 candles
        ohlcv = await exchange.fetch_ohlcv('BTC/USDT', '15m', limit=10)
        
        print(f"\nLast 10 BTC 15m Candles (Binance):")
        print(f"{'Time (Local)':<25} {'Open':<10} {'Close':<10} {'Color':<6}")
        print("-" * 60)
        
        for candle in ohlcv:
            ts = candle[0]
            open_p = candle[1]
            close_p = candle[4]
            dt = datetime.datetime.fromtimestamp(ts/1000)
            color = "GREEN" if close_p >= open_p else "RED"
            print(f"{str(dt):<25} {open_p:<10} {close_p:<10} {color:<6}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(debug_btc_15m())
