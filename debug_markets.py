import asyncio
import httpx
from datetime import datetime

async def main():
    url = "https://gamma-api.polymarket.com/events"
    # Search for BTC 15m markets
    params = {
        "slug": "btc-updown-15m", 
        # API exact match or partial? usually strict.
        # Let's try broad search through "markets" endpoint
    }
    
    # Better: Use the same endpoint the frontend uses: /api/poly/markets (proxied to gamma markets)
    # But I'll use direct URL to verify assumption
    url_markets = "https://gamma-api.polymarket.com/markets"
    params_markets = {
        "active": "true",
        "limit": 20,
        "closed": "false",
        "tag_id": "90" # Crypto? Or just search text.
        # Let's just fetch recent active markets and filter for 15m
    }
    
    async with httpx.AsyncClient() as client:
        print("Fetching markets...")
        resp = await client.get(url_markets, params=params_markets)
        data = resp.json()
        
        print(f"Got {len(data)} markets.")
        
        print(f"Got {len(data)} markets.")
        
        print("\n--- First 5 Markets ---")
        for m in data[:5]:
            print(f"Slug: {m.get('market_slug')}")
            print(f"Question: {m.get('question')}")
            print(f"End Date: {m.get('end_date_iso')}")
            print("---")
            
        # Also try to reverse engineer the timestamp in slug
        # slug format: btc-updown-15m-yyyymmdd... or timestamp?
        # User code assumes: btc-updown-15m-TIMESTAMP

if __name__ == "__main__":
    asyncio.run(main())
