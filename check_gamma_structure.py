import requests
import json
from datetime import datetime, timezone, timedelta

def check_market_details(slug):
    url = f"http://localhost:8000/api/poly/events?slug={slug}"
    try:
        res = requests.get(url)
        data = res.json()
        if len(data) > 0:
            market = data[0]['markets'][0]
            print(f"slug: {slug}")
            print(f"clobTokenIds: {market.get('clobTokenIds')}")
            print(f"conditionId: {market.get('conditionId')}")
            print("Keys:", market.keys())
        else:
            print("No data found")
    except Exception as e:
        print(e)
        
ts = 1765182600 # 08:30 UTC
slug = f"btc-updown-15m-{ts}"
check_market_details(slug)
