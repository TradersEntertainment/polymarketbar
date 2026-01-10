from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import asyncio
import httpx
import os
from .analyzer import Analyzer
from .live_stats import LiveStats
from .datasources.ccxt_adapter import CCXTAdapter
from .notification import TelegramNotifier
from dotenv import load_dotenv

# Load env vars
load_dotenv()

app = FastAPI(title="Polymarket Stats API")

# Initialize Analyzer & Notifier
analyzer = Analyzer()
notifier = TelegramNotifier()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for now, restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_header(request, call_next):
    try:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    except RuntimeError as e:
        if str(e) == "No response returned.":
            # Client disconnected or timeout occurred downstream
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": "Request timed out or client disconnected"}, status_code=504)
        raise e

analyzer = Analyzer()
live_stats = LiveStats()

# Cache to avoid hitting rate limits too hard
# Simple in-memory cache
stats_cache = {}
CACHE_DURATION = 60 # seconds


# Global HTTP client
http_client = None

@app.on_event("startup")
async def startup():
    global http_client
    # timeouts=None or reasonable defaults? httpx default is 5s.
    # Let's set a reasonable timeout to avoid hanging indefinitely if Polymarket is down.
    http_client = httpx.AsyncClient(timeout=10.0)

@app.on_event("shutdown")
async def shutdown():
    await analyzer.close()
    if http_client:
        await http_client.aclose()

# --- NEW: Polymarket Proxy Endpoints ---

@app.get("/api/poly/markets")
async def get_poly_markets(active: bool = True, limit: int = 20):
    """
    Proxy for Polymarket Markets API.
    """
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "active": str(active).lower(),
        "limit": limit,
        "closed": "false"
    }
    try:
        resp = await http_client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        print(f"Proxy Error {url}: {exc.response.status_code} - {exc.response.text}")
        raise HTTPException(status_code=exc.response.status_code, detail=f"Upstream Error: {exc.response.text}")
    except Exception as e:
        print(f"Proxy Exception {url}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/poly/orderbook")
async def get_poly_orderbook(market_id: str):
    """
    Proxy for Polymarket Orderbook API.
    """
    url = "https://gamma-api.polymarket.com/orderbook"
    params = {"market_id": market_id}
    try:
        resp = await http_client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        print(f"Proxy Error {url}: {exc.response.status_code} - {exc.response.text}")
        raise HTTPException(status_code=exc.response.status_code, detail=f"Upstream Error: {exc.response.text}")
    except Exception as e:
        print(f"Proxy Exception {url}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/poly/clob/book")
async def get_clob_book(token_id: str):
    """
    Proxy for Polymarket CLOB Orderbook API.
    """
    url = "https://clob.polymarket.com/book"
    params = {"token_id": token_id}
    try:
        resp = await http_client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        print(f"Proxy Error {url} ({token_id}): {exc.response.status_code} - {exc.response.text}")
        raise HTTPException(status_code=exc.response.status_code, detail=f"Upstream Error: {exc.response.text}")
    except Exception as e:
        print(f"Proxy Exception {url} ({token_id}): {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/poly/events")
async def get_poly_events(slug: str = None):
    """
    Proxy for Polymarket Events API (by slug).
    """
    url = "https://gamma-api.polymarket.com/events"
    params = {}
    if slug:
        params["slug"] = slug
        
    try:
        resp = await http_client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        print(f"Proxy Error {url}: {exc.response.status_code} - {exc.response.text}")
        raise HTTPException(status_code=exc.response.status_code, detail=f"Upstream Error: {exc.response.text}")
    except Exception as e:
        print(f"Proxy Exception {url}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/poly/candles")
async def get_poly_candles(market_id: str, tf: str = "1h"):
    """
    Proxy for Polymarket Candles API.
    """
    # Map our tf to Polymarket tf if needed, or pass through
    # Polymarket supports: 1m, 5m, 15m, 30m, 1h, 6h, 1d
    url = "https://gamma-api.polymarket.com/candles"
    params = {"market_id": market_id, "resolution": tf} 
    try:
        resp = await http_client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        print(f"Proxy Error {url}: {exc.response.status_code} - {exc.response.text}")
        raise HTTPException(status_code=exc.response.status_code, detail=f"Upstream Error: {exc.response.text}")
    except Exception as e:
        print(f"Proxy Exception {url}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Original Endpoints ---

@app.get("/api/batch-stats/{timeframe}")
async def get_batch_stats(timeframe: str, symbols: str = "BTC,ETH,SOL,XRP"):
    """
    Fetch stats for multiple symbols in one request.
    symbols: comma-separated list of symbols
    """
    symbol_list = symbols.split(',')
    results = {}
    
    # Process sequentially or with gather. Gather is better.
    tasks = []
    for symbol in symbol_list:
        tasks.append(analyzer.get_stats(symbol, timeframe))
    
    stats_list = await asyncio.gather(*tasks)
    
    for symbol, stats in zip(symbol_list, stats_list):
        if not stats:
            results[symbol] = {"error": "No data"}
        else:
            results[symbol] = stats
            
    return results

@app.get("/api/stats/{symbol}/{timeframe}")
async def get_stats(symbol: str, timeframe: str):
    """
    Get historical streak stats and probabilities.
    """
    # Normalize symbol
    symbol = symbol.upper()
    
    try:
        data = await analyzer.get_stats(symbol, timeframe)
        if not data:
            raise HTTPException(status_code=404, detail="Data not found")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/live/{symbol}")
async def get_live(symbol: str):
    """
    Get live price and simple probability for current candle.
    """
    try:
        price = await analyzer.adapter.fetch_current_price(symbol)
        return {"symbol": symbol, "price": price}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history/{symbol}/{timeframe}")
async def get_history(symbol: str, timeframe: str, limit: int = 2000):
    """
    Get OHLCV history for a symbol. Optimized for speed.
    """
    try:
        # Use CCXT adapter directly
        ohlcv = await analyzer.adapter.fetch_ohlcv(symbol, timeframe)
        
        if ohlcv.empty:
            return []

        # Slice to limit
        if len(ohlcv) > limit:
            ohlcv = ohlcv.iloc[-limit:]
        
        # Vectorized formatting (100x faster than iterrows)
        # Create a temp df for serialization
        export_df = ohlcv.copy()
        # Convert index (Datetime) to seconds
        export_df['time'] = (export_df.index.astype('int64') // 10**9).astype(int)
        export_df['price'] = export_df['close']
        
        # Return as list of dicts
        return export_df[['time', 'price']].to_dict(orient='records')
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok"}

@app.on_event("startup")
async def startup_event():
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Starting up App (Hyperliquid Mode)...")
    
    # Valid Symbols
    symbols = ['BTC', 'ETH', 'SOL', 'XRP']
    
    # Warmup & Backfill Cache (Reduced to 30 days to prevent startup congestion)
    logger.info("Starting Deep Backfill (30 Days) for major symbols...")
    for sym in symbols:
       # We only backfill 1h, others derived
       if hasattr(analyzer.adapter, 'backfill_history'):
            asyncio.create_task(analyzer.adapter.backfill_history(sym, '1h', days=30))

    # Start background updater
    asyncio.create_task(background_updater())

async def background_updater():
    """
    Background task to keep data fresh and check alerts.
    """
    import logging
    import time
    logger = logging.getLogger(__name__)
    symbols = ['BTC', 'ETH', 'SOL', 'XRP']
    timeframes = ['15m', '1h']
    
    logger.info("Starting background updater...")
    
    consecutive_errors = 0
    last_restart_time = time.time()
    RESTART_INTERVAL = 6 * 60 * 60  # 6 hours
    MAX_CONSECUTIVE_ERRORS = 3
    
    while True:
        # Periodic proactive restart
        if time.time() - last_restart_time > RESTART_INTERVAL:
            logger.info("Performing scheduled restart of adapters...")
            try:
                await analyzer.restart()
                last_restart_time = time.time()
                consecutive_errors = 0
            except Exception as e:
                logger.error(f"Failed to restart adapters: {e}")

        try:
            for symbol in symbols:
                for timeframe in timeframes:
                    # In Hyperliquid Mode, get_stats fetches fresh data directly.
                    # We just need to call it to check for alerts.
                    
                    # Check for Alerts
                    try:
                        stats = await analyzer.get_stats(symbol, timeframe)
                        if stats:
                            await notifier.check_and_alert(
                                symbol, 
                                timeframe, 
                                stats['current_streak']['type'], # Fixed key from previous logic?
                                stats['current_streak']['length'], # Fixed key
                                stats['current_price'] # Fixed key
                            )
                    except Exception as e:
                        # logger.error(f"Alert check failed for {symbol} {timeframe}: {e}")
                        pass

                    await asyncio.sleep(0.5) 
            
            # logger.info("Background update cycle complete.")
            consecutive_errors = 0 # Reset on success
            await asyncio.sleep(15) 
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"Error in background updater (Count: {consecutive_errors}): {e}")
            
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                logger.warning("Too many consecutive errors. Restarting adapters...")
                try:
                    await analyzer.restart()
                    consecutive_errors = 0
                    last_restart_time = time.time() 
                except Exception as restart_err:
                    logger.error(f"Failed to restart adapters during recovery: {restart_err}")
            
            await asyncio.sleep(15)

# Mount frontend static files
# This expects the frontend to be built and located at ../frontend/dist (relative to where main.py is run, which is usually root)
# In Docker, we copy to /app/frontend/dist. Locally it might be different.
# Let's assume standard structure:
# root/
#   backend/
#   frontend/dist/

# We need to find the absolute path to frontend/dist relative to this file
import pathlib
current_dir = pathlib.Path(__file__).parent.resolve()
# Go up one level to root, then into frontend/dist
frontend_dist = current_dir.parent / "frontend" / "dist"

if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    
    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"])
    async def catch_all(full_path: str):
        # Allow API routes to pass through
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not found")
            
        # Serve index.html for everything else (SPA)
        # Check if specific file exists first (like favicon)
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
             return FileResponse(file_path)
             
        return FileResponse(frontend_dist / "index.html")
else:
    print(f"WARNING: Frontend dist not found at {frontend_dist}. API only mode.")
