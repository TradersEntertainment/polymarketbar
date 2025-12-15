import requests
import datetime

def check_api_stats():
    output = []
    try:
        url = "http://localhost:8000/api/stats/BTC/15m"
        output.append(f"Fetching {url}...")
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        
        output.append("\n--- API Response (BTC 15m) ---")
        curr_streak = data.get('current_streak', {})
        output.append(f"Current Streak: {curr_streak}")
        
        close_time = data.get('candle_close_time')
        if close_time:
            dt = datetime.datetime.fromtimestamp(close_time/1000)
            output.append(f"Next Close Time: {dt}")
            
        output.append(f"Current Price: {data.get('current_price')}")
        output.append(f"Candle Open: {data.get('candle_open')}")
        
    except Exception as e:
        output.append(f"Error: {e}")

    with open("debug_api_results.txt", "w") as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    check_api_stats()
