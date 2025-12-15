import requests
import json

def check_api_debug():
    output = []
    try:
        url = "http://localhost:8000/api/stats/BTC/15m"
        output.append(f"Fetching {url}...")
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        
        output.append("\n--- API Response (BTC 15m) ---")
        output.append(f"Current Streak: {data.get('current_streak')}")
        output.append(f"Current Price: {data.get('current_price')}")
        
        debug_candles = data.get('debug_candles', [])
        output.append("\nLast 5 Candles (Internal):")
        for c in debug_candles:
            output.append(f"Time: {c['time']} | Open: {c['open']} | Close: {c['close']} | Color: {c['color']}")
            
    except Exception as e:
        output.append(f"Error: {e}")

    with open("debug_api_internal.txt", "w") as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    check_api_debug()
