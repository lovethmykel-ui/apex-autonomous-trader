"""
Apex Autonomous Trader — FastAPI Application Entry Point
==========================================================
Binds all routers, middleware, database initialization, and background tasks.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.core.config import settings
from apps.api.core.database import engine
from shared.db import base

from apps.api.routers import auth, bot, portfolio, market
from services.telegram_bot.service import start_telegram_bot, stop_telegram_bot
from services.trading_engine.bot_loop import start_bot, stop_bot

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("apex_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events: Start Telegram polling and autonomous loop if enabled."""
    logger.info("Initializing Apex Autonomous Trader...")
    
    # 1. Create database tables if they don't exist
    base.Base.metadata.create_all(bind=engine)
    logger.info("Database models verified.")
    
    # 2. Start Telegram listener
    start_telegram_bot()
    
    # 3. Start Trading Loop automatically
    # (In a real setup, you might want it to wait for a /start command)
    start_bot()
    
    yield
    
    # 4. Shutdown gracefully
    logger.info("Shutting down Apex Autonomous Trader...")
    stop_bot()
    stop_telegram_bot()


# Create FastAPI App
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API for Apex Autonomous Trader",
    lifespan=lifespan,
)

# Setup Structured Logging
from services.monitoring.logger import setup_structured_logging
setup_structured_logging()

# CORS configuration for Web Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus Metrics Endpoint
from prometheus_client import make_asgi_app
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include Routers
app.include_router(auth.router)
app.include_router(bot.router)
app.include_router(portfolio.router)
app.include_router(market.router)


@app.get("/health")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "agent": "alive"}
