from datetime import datetime, timezone, timedelta
try:
    import pytz
    has_pytz = True
except ImportError:
    has_pytz = False
    print("No pytz, using fixed offset for ET check (approx)")

def get_natural_slug(asset, offset_hours=0):
    # Mocking ET time
    # Eastern is UTC-5 (Standard) or UTC-4 (DST). currently UTC-5 (Dec).
    now = datetime.now(timezone.utc)
    
    # Start of Hour
    start_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=offset_hours)
    
    # Convert to ET manually if no pytz
    # Dec -> Standard Time -> UTC-5
    et_time = start_hour - timedelta(hours=5)
    
    month = et_time.strftime("%B").lower()
    day = et_time.day
    
    # Hour formatting: 3am, 12pm, etc
    hour_int = et_time.hour
    ampm = "am" if hour_int < 12 else "pm"
    hour_12 = hour_int if hour_int <= 12 else hour_int - 12
    if hour_12 == 0: hour_12 = 12
    
    time_str = f"{hour_12}{ampm}-et"
    
    asset_map = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "xrp"}
    slug_asset = asset_map.get(asset, asset.lower())
    
    return f"{slug_asset}-up-or-down-{month}-{day}-{time_str}"

print("Predicted Current 1H Slug:", get_natural_slug("BTC"))
print("Predicted Next 1H Slug:", get_natural_slug("BTC", 1))

# Check validity
import requests
def check(slug):
    try:
        r = requests.get(f"http://localhost:8000/api/poly/events?slug={slug}")
        if len(r.json()) > 0: print(f"[FOUND] {slug}")
        else: print(f"[MISS] {slug}")
    except: print("Error fetching")

check(get_natural_slug("BTC"))
check(get_natural_slug("BTC", 1))
