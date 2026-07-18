"""
Apex Autonomous Trader — Bot Control Router
=============================================
Endpoints to control the autonomous agent via the web dashboard.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from apps.api.core.database import get_db
from services.trading_engine.bot_loop import start_bot, stop_bot, get_status

router = APIRouter(prefix="/bot", tags=["bot"])


@router.get("/status")
async def get_bot_status() -> Dict[str, Any]:
    """Get real-time status of the trading loop."""
    return get_status()


@router.post("/start")
async def start_autonomous_bot() -> Dict[str, str]:
    """Wake the agent up."""
    success = start_bot()
    if not success:
        raise HTTPException(status_code=400, detail="Bot is already running")
    return {"status": "Bot started"}


@router.post("/stop")
async def stop_autonomous_bot() -> Dict[str, str]:
    """Put the agent to sleep."""
    success = stop_bot()
    if not success:
        raise HTTPException(status_code=400, detail="Bot is already stopped")
    return {"status": "Bot stopped"}
