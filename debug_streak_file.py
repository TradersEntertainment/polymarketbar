import asyncio
import ccxt.async_support as ccxt
import datetime

async def debug_btc_15m():
    output = []
    output.append("Connecting to Binance...")
    exchange = ccxt.binance()
    try:
        # Fetch last 10 candles
        ohlcv = await exchange.fetch_ohlcv('BTC/USDT', '15m', limit=10)
        
        output.append(f"\nLast 10 BTC 15m Candles (Binance):")
        output.append(f"{'Time (Local)':<25} {'Open':<10} {'Close':<10} {'Color':<6}")
        output.append("-" * 60)
        
        for candle in ohlcv:
            ts = candle[0]
            open_p = candle[1]
            close_p = candle[4]
            dt = datetime.datetime.fromtimestamp(ts/1000)
            color = "GREEN" if close_p >= open_p else "RED"
            output.append(f"{str(dt):<25} {open_p:<10} {close_p:<10} {color:<6}")
            
    except Exception as e:
        output.append(f"Error: {e}")
    finally:
        await exchange.close()

    with open("debug_streak_results.txt", "w") as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    asyncio.run(debug_btc_15m())
