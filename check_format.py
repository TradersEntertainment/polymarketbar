import requests
from datetime import datetime

def check_slug(slug):
    url = f"http://localhost:8000/api/poly/events?slug={slug}"
    try:
        res = requests.get(url)
        if res.status_code == 200 and len(res.json()) > 0:
            print(f"[FOUND] {slug}")
        else:
            print(f"[MISS] {slug}")
    except:
        pass

# Check 1h
# Try to find a valid 1h timestamp
# 1h buckets usually expire on the hour?
now = datetime.utcnow()
current_hour_ts = int(now.replace(minute=0, second=0, microsecond=0).timestamp())
next_hour_ts = current_hour_ts + 3600

# Daily
# "bitcoin-up-or-down-on-december-8"
month = now.strftime("%B").lower()
day = now.day
daily_slug = f"bitcoin-up-or-down-on-{month}-{day}"

slugs = [
    f"btc-updown-1h-{next_hour_ts}",
    f"eth-updown-1h-{next_hour_ts}",
    daily_slug
]

for s in slugs:
    check_slug(s)
