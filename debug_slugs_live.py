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
            print(f"[MISS]  {slug}")
    except Exception as e:
        print(f"[ERR]   {slug}: {e}")
    return False

def main():
    # Emulate Frontend Logic
    # now = new Date() (UTC based)
    now = datetime.now(timezone.utc)
    print(f"Current UTC: {now}")
    
    minutes = now.minute
    remainder = minutes % 15
    
    # startOfCurrent = now - remainder
    current_start = now - timedelta(minutes=remainder, seconds=now.second, microseconds=now.microsecond)
    
    print(f"Current Bucket Start: {current_start}")
    
    # Current Expiry = Start + 15m
    curr_expiry = current_start + timedelta(minutes=15)
    # Next Expiry = Start + 30m
    next_expiry = current_start + timedelta(minutes=30)
    
    ts_curr = int(curr_expiry.timestamp())
    ts_next = int(next_expiry.timestamp())
    
    slug_curr = f"btc-updown-15m-{ts_curr}"
    slug_next = f"btc-updown-15m-{ts_next}"
    
    print("Checking predicted slugs...")
    check_slug(slug_curr)
    check_slug(slug_next)
    
    print("\nListing ALL btc-updown-15m markets from active list:")
    try:
        res = requests.get("http://localhost:8000/api/poly/markets?active=true&limit=1000")
        markets = res.json()
        for m in markets:
            if "btc" in m.get("market_slug", "") and "15m" in m.get("market_slug", ""):
                print(f"  - {m['market_slug']} (Expires: {m.get('end_date_iso')})")
    except Exception as e:
        print(f"Error fetching list: {e}")

if __name__ == "__main__":
    main()
