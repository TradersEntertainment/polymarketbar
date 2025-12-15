import requests
import datetime

def check_api_stats():
    try:
        url = "http://localhost:8000/api/stats/BTC/15m"
        print(f"Fetching {url}...")
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        
        print("\n--- API Response (BTC 15m) ---")
        curr_streak = data.get('current_streak', {})
        print(f"Current Streak: {curr_streak}")
        
        close_time = data.get('candle_close_time')
        if close_time:
            dt = datetime.datetime.fromtimestamp(close_time/1000)
            print(f"Next Close Time: {dt}")
            
        print(f"Current Price: {data.get('current_price')}")
        print(f"Candle Open: {data.get('candle_open')}")
        
        # Check distribution last update
        dist = data.get('distribution', {})
        # Just print top item
        first_key = list(dist.keys())[0] if dist else "None"
        print(f"Distribution First Key: {first_key}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_api_stats()
