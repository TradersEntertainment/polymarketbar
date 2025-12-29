
import asyncio
import logging
import os
import json
from typing import Optional, List, Dict
from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import httpx

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Notifier")

app = FastAPI(title="Polymarket Notifier")

# Templates
templates = Jinja2Templates(directory="templates")

# State (In-memory for simplicity, can be saved to JSON)
SETTINGS_FILE = "/data/notifier_settings.json" if os.path.exists("/data") else "notifier_settings.json"

class Settings:
    def __init__(self):
        self.target_url = "https://polymarketbar-production.up.railway.app"
        self.telegram_token = ""
        self.telegram_chat_id = ""
        self.streak_threshold = 5
        self.enabled = False
        self.load()

    def load(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    self.target_url = data.get("target_url", self.target_url)
                    self.telegram_token = data.get("telegram_token", self.telegram_token)
                    self.telegram_chat_id = data.get("telegram_chat_id", self.telegram_chat_id)
                    self.streak_threshold = int(data.get("streak_threshold", self.streak_threshold))
                    self.enabled = bool(data.get("enabled", self.enabled))
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")

    def save(self):
        try:
            data = {
                "target_url": self.target_url,
                "telegram_token": self.telegram_token,
                "telegram_chat_id": self.telegram_chat_id,
                "streak_threshold": self.streak_threshold,
                "enabled": self.enabled
            }
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

settings = Settings()

# Alert History to prevent spam
# Key: (symbol, timeframe) -> int (last alerted streak count)
alert_history: Dict[tuple, int] = {}

# Background Task
async def monitor_loop():
    logger.info("Starting Monitor Loop...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        while True:
            if settings.enabled and settings.target_url:
                try:
                    # We need to fetch stats. Ideally the main app has a batch endpoint.
                    # Or we check each timeframe.
                    # Let's assume we check 15m, 1h, 4h, 1d
                    timeframes = ['15m', '1h', '4h', '1d']
                    
                    # Optimized: Fetch batch stats if available? 
                    # Main app has /api/batch-stats/{timeframe} that returns list of ALL symbols
                    
                    for tf in timeframes:
                        try:
                            url = f"{settings.target_url.rstrip('/')}/api/batch-stats/{tf}"
                            resp = await client.get(url)
                            if resp.status_code == 200:
                                data = resp.json() # List of {symbol, price, streak_type, streak_count...}
                                await process_stats(data, tf, client)
                            else:
                                logger.warning(f"Failed to fetch {tf}: {resp.status_code}")
                        except Exception as e:
                            logger.error(f"Error checking {tf}: {e}")
                            
                except Exception as e:
                    logger.error(f"Monitor loop error: {e}")
            
            await asyncio.sleep(15) # Check every 15s

async def process_stats(stats_list: List[Dict], timeframe: str, client: httpx.AsyncClient):
    global alert_history
    
    for item in stats_list:
        symbol = item.get('symbol')
        count = item.get('streak_count', 0)
        s_type = item.get('streak_type', 'flat')
        price = item.get('price', 0)
        
        if count >= settings.streak_threshold:
            # Check history
            key = (symbol, timeframe)
            last_alerted = alert_history.get(key, 0)
            
            # Alert on NEW threshold breach or INCREASE
            # Only alert if count > last_alerted check is strict
            if count > last_alerted:
                await send_telegram_alert(client, symbol, timeframe, s_type, count, price)
                alert_history[key] = count
        else:
            # Reset history if streak drops
            key = (symbol, timeframe)
            if key in alert_history:
                del alert_history[key]

async def send_telegram_alert(client: httpx.AsyncClient, symbol, timeframe, s_type, count, price):
    if not settings.telegram_token or not settings.telegram_chat_id:
        return

    emoji = "🟢" if s_type == "up" else "🔴"
    direction = "YÜKSELİŞ" if s_type == "up" else "DÜŞÜŞ"
    
    msg = (
        f"🚨 **STREAK ALARMI: {symbol}** 🚨\n\n"
        f"{emoji} **{count} Mumdur {direction}** ({timeframe})\n"
        f"💰 Fiyat: ${price}\n\n"
        f"#{symbol} #{s_type} #PolymarketBar"
    )
    
    url = f"https://api.telegram.org/bot{settings.telegram_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": msg,
        "parse_mode": "Markdown"
    }
    
    try:
        resp = await client.post(url, json=payload)
        if resp.status_code == 200:
            logger.info(f"Sent alert for {symbol} {timeframe}")
        else:
            logger.error(f"Telegram fail: {resp.text}")
    except Exception as e:
        logger.error(f"Telegram send error: {e}")

# Lifecycle
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(monitor_loop())

# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "settings": settings,
        "alert_count": len(alert_history)
    })

@app.post("/settings")
async def update_settings(
    request: Request,
    target_url: str = Form(...),
    telegram_token: str = Form(...),
    telegram_chat_id: str = Form(...),
    streak_threshold: int = Form(...),
    enabled: Optional[str] = Form(None)
):
    settings.target_url = target_url
    settings.telegram_token = telegram_token
    settings.telegram_chat_id = telegram_chat_id
    settings.streak_threshold = streak_threshold
    settings.enabled = True if enabled == "on" else False
    settings.save()
    
    # Reset history on significant change? Maybe not.
    return RedirectResponse(url="/", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
