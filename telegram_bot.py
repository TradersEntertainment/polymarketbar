
import asyncio
import os
import sys
import json
import logging
import httpx
from datetime import datetime

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("TeleBot")

# Ensure we can import from backend
sys.path.append(os.getcwd())

try:
    from backend.analyzer import Analyzer
except ImportError:
    # Handle case where user runs from inside a subdir
    sys.path.append(os.path.join(os.getcwd(), '..'))
    from backend.analyzer import Analyzer

# Configuration
SETTINGS_FILE = "telegram_settings.json"

def load_settings():
    defaults = {
        "streak_threshold": 5,
        "symbols": ["BTC", "ETH", "SOL", "XRP"],
        "timeframes": ["15m", "1h", "4h", "1d"]
    }
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(defaults, f, indent=4)
        return defaults
    
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        return defaults

async def send_telegram_msg(token, chat_id, text):
    if not token or not chat_id:
        logger.warning("No Telegram credentials found.")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        # Sanitize Unicode surrogates
        try:
             text = text.encode('utf-16', 'surrogatepass').decode('utf-16')
        except:
             pass 

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10.0)
            resp.raise_for_status()
            logger.info("Notification sent success.")
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")

def get_emotional_comment(streak_length):
    if streak_length <= 2: return "Pretty Normal \U0001F634"
    elif streak_length <= 4: return "Things getting suspicious... \U0001F914"
    elif streak_length <= 7: return "Market Anomaly Detected! \U0001F525"
    else: return "\U0001F6A8 EXTREME DEVIATION EVENT \U0001F6A8\U0001F4E2"

async def main():
    logger.info("Starting Standalone Telegram Bot...")
    
    # Load Env
    from dotenv import load_dotenv
    load_dotenv()
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN missing in .env")
        return

    analyzer = Analyzer()
    last_alerted = {} # Key: SYMBOL_TF, Value: length

    logger.info("Bot initialized. Monitoring markets...")
    await send_telegram_msg(token, chat_id, "\u2705 <b>Bot Started Monitoring</b>")

    while True:
        try:
            settings = load_settings()
            threshold = settings.get("streak_threshold", 5)
            symbols = settings.get("symbols", ["BTC"])
            timeframes = settings.get("timeframes", ["1h"])
            
            for symbol in symbols:
                for tf in timeframes:
                    # Update & Fetch
                    # We rely on Analyzer's adapter which uses CCXT
                    # Note: Analyzer instance persists, so CCXT connection is reused
                    
                    try:
                        # Force update cache first (this handles API calls)
                        await analyzer.adapter.update_cache(symbol, tf)
                        
                        stats = await analyzer.get_stats(symbol, tf)
                        if not stats: continue
                        
                        streak = stats['current_streak']
                        length = streak['length']
                        s_type = streak['type']
                        
                        key = f"{symbol}_{tf}"
                        prev_len = last_alerted.get(key, 0)
                        
                        # Reset
                        if length < prev_len:
                            last_alerted[key] = 0
                            prev_len = 0
                            
                        # Alert Condition
                        if length >= threshold and length > prev_len:
                            emoji = "\U0001F7E2" if s_type == 'green' else "\U0001F534"
                            comment = get_emotional_comment(length)
                            
                            msg = (
                                f"{emoji} <b>{symbol} {tf} Streak: {length}</b>\n"
                                f"{comment}\n"
                                f"<i>Previous record: {prev_len}</i>"
                            )
                            
                            logger.info(f"Triggering alert for {symbol} {tf} (Len: {length})")
                            await send_telegram_msg(token, chat_id, msg)
                            
                            last_alerted[key] = length
                            
                    except Exception as loop_e:
                        logger.error(f"Error processing {symbol} {tf}: {loop_e}")
                        
                    # Slow down to be nice to APIs
                    await asyncio.sleep(1)
            
            logger.info("Cycle complete. Sleeping 30s...")
            await asyncio.sleep(30)
            
        except KeyboardInterrupt:
            break
        except Exception as main_e:
            logger.critical(f"Main loop crash: {main_e}")
            await asyncio.sleep(60) # Wait a minute before restart
            
    await analyzer.close()

if __name__ == "__main__":
    asyncio.run(main())
