"""
Apex Autonomous Trader — Market Router
========================================
Endpoints to retrieve the agent's real-time view of the market.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List

from apps.api.core import bybit as bybit_client
from services.market_intelligence.engine import MarketIntelligence

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/scan")
async def get_market_scan(limit: int = 20) -> List[Dict[str, Any]]:
    """Get the top volume pairs currently being monitored."""
    try:
        pairs = bybit_client.scan_market(top_n=limit)
        return pairs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/{symbol}")
async def analyze_symbol(symbol: str) -> Dict[str, Any]:
    """Run Market Intelligence on a specific symbol and return the assessment."""
    try:
        candles = bybit_client.get_candles(symbol, "5", 200)
        if len(candles) < 30:
            return {"error": "Insufficient data"}
            
        funding = bybit_client.get_funding_rate(symbol)
        oi = bybit_client.get_open_interest(symbol)
        
        assessment = MarketIntelligence.analyze(
            candles_5m=candles,
            funding_rate=funding.get("funding_rate", 0) if funding else 0,
            open_interest=oi.get("open_interest", 0) if oi else 0,
            symbol=symbol,
        )
        return assessment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
