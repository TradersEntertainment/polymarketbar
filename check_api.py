import requests
import json
import time

def check_15m_stats():
    url = "http://127.0.0.1:8000/api/batch-stats/15m"
    try:
        res = requests.get(url)
        data = res.json()
        
        print(f"\nTime: {time.strftime('%H:%M:%S')}")
        for symbol, stats in data.items():
            print(f"\n--- {symbol} ---")
            streak = stats['current_streak']
            print(f"Streak: {streak['length']} {streak['type'].upper()}")
            
            # Print debug candles
            candles = stats.get('debug_candles', [])
            print("Last 5 Candles:")
            for c in candles:
                color = c['color'].upper() if 'color' in c else '?'
                print(f"  {c['time']} | O: {c['open']} | C: {c['close']} | {color}")
                
            # Manual verification
            if len(candles) > 0:
                last_color = candles[-1]['color']
                count = 0
                for i in range(len(candles)-1, -1, -1):
                    if candles[i]['color'] == last_color:
                        count += 1
                    else:
                        break
                print(f"Manual Check from last 5: {count} {last_color.upper()}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_15m_stats()
