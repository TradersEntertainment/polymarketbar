import requests
import time
import datetime

def test_4h_stats():
    try:
        url = "http://localhost:8000/api/stats/BTC/4h"
        print(f"Fetching {url}...")
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        
        close_time_ms = data['candle_close_time']
        open_time_str = data.get('candle_open_time_str', 'N/A') # Not in response but open price is
        
        now_ms = int(time.time() * 1000)
        diff = close_time_ms - now_ms
        
        print("\n--- 4h Stats Debug (BTC) ---")
        print(f"Server Time (Approx): {datetime.datetime.now()}")
        print(f"Candle Close Time (ms): {close_time_ms}")
        print(f"Candle Close Time (ISO): {datetime.datetime.fromtimestamp(close_time_ms/1000)}")
        print(f"Current Time (ms): {now_ms}")
        print(f"Difference (ms): {diff}")
        
        hours = diff // (1000 * 60 * 60)
        minutes = (diff % (1000 * 60 * 60)) // (1000 * 60)
        seconds = (diff % (1000 * 60)) // 1000
        
        print(f"Time Left: {hours}h {minutes}m {seconds}s")
        
        # Also fetch 1h for comparison
        res_1h = requests.get("http://localhost:8000/api/stats/BTC/1h").json()
        print(f"\n1h Close Time (ISO): {datetime.datetime.fromtimestamp(res_1h['candle_close_time']/1000)}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_4h_stats()
