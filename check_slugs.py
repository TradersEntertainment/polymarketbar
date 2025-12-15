import requests
import time
from datetime import datetime, timezone, timedelta

def check_slug(slug):
    url = f"http://localhost:8000/api/poly/events?slug={slug}"
    try:
        res = requests.get(url)
        if res.status_code == 200 and len(res.json()) > 0:
            print(f"[FOUND] {slug}")
            return True
        else:
            print(f"[MISS] {slug}")
    except Exception as e:
        print(f"[ERR] {slug}: {e}")
    return False

def main():
    # Calculate timestamps
    now = datetime.utcnow()
    print(f"Current UTC: {now}")
    
    # 15m buckets
    # Start of current bucket
    minutes = now.minute
    remainder = minutes % 15
    current_start = now - timedelta(minutes=remainder, seconds=now.second, microseconds=now.microsecond)
    current_end = current_start + timedelta(minutes=15)
    
    timestamps = [
        int(current_start.timestamp()), # Start time
        int(current_end.timestamp()),   # End time
        int(current_end.timestamp()) - 1, # End time minus 1 sec?
    ]
    
    assets = ['btc', 'bitcoin', 'eth', 'ethereum']
    
    for asset in assets:
        for ts in timestamps:
            # Check various formats
            slugs = [
                f"{asset}-updown-15m-{ts}",
                f"{asset}-updown-15m-{ts+900}", # Next bucket
            ]
            
            for s in slugs:
                check_slug(s)

if __name__ == "__main__":
    main()
