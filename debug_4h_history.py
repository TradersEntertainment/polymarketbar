import requests
import datetime

def check_history():
    try:
        url = "http://localhost:8000/api/history/BTC/4h"
        print(f"Fetching {url}...")
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        
        print(f"\nLast 5 4h Candles:")
        for candle in data[-5:]:
            ts = candle['time'] # seconds
            dt_utc = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
            dt_local = datetime.datetime.fromtimestamp(ts)
            print(f"TS: {ts} | UTC: {dt_utc} | Local: {dt_local}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_history()
