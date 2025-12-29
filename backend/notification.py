
import os
import httpx
import logging
import asyncio

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.client = httpx.AsyncClient(timeout=10.0)
        # Store last alerted level for each (symbol, timeframe)
        # Key: (symbol, timeframe) -> int (last streak length alerted)
        self.alert_history = {}

    async def check_and_alert(self, symbol: str, timeframe: str, streak_type: str, streak_count: int, price: float):
        if not self.token or not self.chat_id:
            # logger.warning("Telegram credentials missing.")
            return

        if streak_count < 5:
            # Reset history if streak broke or dropped below threshold
            if (symbol, timeframe) in self.alert_history:
                del self.alert_history[(symbol, timeframe)]
            return

        # Check loop prevention
        last_alerted = self.alert_history.get((symbol, timeframe), 0)
        
        # Alert ONLY if:
        # 1. New streak count is strictly greater than last alerted count
        #    (Prevents spamming "Streak is 5" every 15 seconds)
        if streak_count > last_alerted:
            await self.send_alert(symbol, timeframe, streak_type, streak_count, price)
            self.alert_history[(symbol, timeframe)] = streak_count

    async def send_alert(self, symbol: str, timeframe: str, streak_type: str, count: int, price: float):
        try:
            emoji = "🟢" if streak_type == "up" else "🔴"
            direction = "YÜKSELİŞ" if streak_type == "up" else "DÜŞÜŞ"
            
            msg = (
                f"🚨 **STREAK ALARMI: {symbol}** 🚨\n\n"
                f"{emoji} **{count} Mumdur {direction}** ({timeframe})\n"
                f"💰 Fiyat: ${price}\n\n"
                f"#{symbol} #{streak_type} #PolymarketBar"
            )
            
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": msg,
                "parse_mode": "Markdown"
            }
            
            resp = await self.client.post(url, json=payload)
            if resp.status_code == 200:
                logger.info(f"Telegram alert sent for {symbol} {timeframe} ({count})")
            else:
                logger.error(f"Telegram failed: {resp.text}")
                
        except Exception as e:
            logger.error(f"Telegram exception: {e}")

    async def close(self):
        await self.client.aclose()
