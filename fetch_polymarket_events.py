import requests
import json

def fetch_events():
    url = "https://gamma-api.polymarket.com/events?closed=false&limit=100"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        print(f"Fetched {len(data)} events.")
        
        relevant_events = []
        for event in data:
            title = event.get('title', '').lower()
            if '15m' in title:
                relevant_events.append({
                    'title': event.get('title'),
                    'slug': event.get('slug'),
                    'id': event.get('id')
                })
        
        print(f"Found {len(relevant_events)} '15m' events.")
        print(json.dumps(relevant_events, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_events()
