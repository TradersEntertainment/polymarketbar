import httpx
import asyncio
import json
import time

async def fetch_and_analyze():
    # Calculate current 15m timestamp (Round DOWN)
    now = time.time()
    # Round down to nearest 900s (15m)
    timestamp = int(now // 900) * 900
    
    slug = f"btc-updown-15m-{timestamp}"
    print(f"Fetching EVENT by slug: {slug}...")
    
    url = "https://gamma-api.polymarket.com/events"
    params = {"slug": slug}
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        data = resp.json()
        
    if isinstance(data, list) and len(data) > 0:
        event = data[0]
        print("\n--- Event Metadata ---")
        print(f"ID: {event.get('id')}")
        print(f"Title: {event.get('title')}")
        print(f"Slug: {event.get('slug')}")
        
        for m in event.get('markets', []):
            print(f"  - Market ID: {m.get('id')}")
            print(f"    Question: {m.get('question')}")
            print(f"    CLOB Token IDs: {json.dumps(m.get('clobTokenIds'))}")
            print(f"    Accepting Orders: {m.get('acceptingOrders')}")
            print(f"    Active: {m.get('active')}")
            
    else:
        print("No event found or unexpected format.")
        print(data)

if __name__ == "__main__":
    asyncio.run(fetch_and_analyze())
