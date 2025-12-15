import requests
import json
from datetime import datetime

slugs = [
    "bitcoin-up-or-down-december-8-3am-et",
    "ethereum-up-or-down-december-8-3am-et",
    "solana-up-or-down-december-8-3am-et",
    "xrp-up-or-down-december-8-3am-et"
]

def check_slug(slug):
    url = f"http://localhost:8000/api/poly/events?slug={slug}"
    try:
        print(f"Checking {slug}...")
        res = requests.get(url)
        data = res.json()
        if len(data) > 0:
            market = data[0]['markets'][0]
            print(f"  [FOUND] ID: {market.get('id')}")
            print(f"  EndDate: {market.get('endDate')} (ISO: {market.get('end_date_iso')})")
            print(f"  Question: {market.get('question')}")
        else:
            print("  [MISS] Not found")
    except Exception as e:
        print(f"  [ERR] {e}")

for s in slugs:
    check_slug(s)
