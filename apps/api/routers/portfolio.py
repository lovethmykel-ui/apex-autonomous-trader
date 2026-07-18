"""
Apex Autonomous Trader — Portfolio Router
===========================================
Endpoints to view generation data, treasury snapshots, and trade memories.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from apps.api.core.database import get_db
from shared.db.models import Generation, Position, TreasurySnapshot, TradeMemory
from services.treasury.manager import TreasuryManager
from services.memory.engine import MemoryEngine

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/generation/active")
async def get_active_generation(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get stats for the currently active generation."""
    gen = TreasuryManager.get_active_generation(db)
    if not gen:
        return {"status": "No active generation"}
    return TreasuryManager.get_generation_summary(gen)


@router.get("/treasury/snapshots")
async def get_treasury_snapshots(
    limit: int = 100, db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get historical equity curve data for the dashboard charts."""
    gen = TreasuryManager.get_active_generation(db)
    if not gen:
        return []
        
    snapshots = db.query(TreasurySnapshot).filter(
        TreasurySnapshot.generation_id == gen.id
    ).order_by(TreasurySnapshot.timestamp.desc()).limit(limit).all()
    
    return [
        {
            "timestamp": s.timestamp.isoformat(),
            "balance": s.balance,
            "daily_drawdown_pct": s.daily_drawdown_pct,
            "open_positions": s.open_positions_count,
        }
        for s in reversed(snapshots)
    ]


@router.get("/positions")
async def get_open_positions(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Get all currently open positions."""
    gen = TreasuryManager.get_active_generation(db)
    if not gen:
        return []
        
    positions = db.query(Position).filter(
        Position.generation_id == gen.id
    ).order_by(Position.opened_at.desc()).all()
    
    return [
        {
            "id": p.id,
            "symbol": p.symbol,
            "side": p.side,
            "size": p.size,
            "entry_price": p.entry_price,
            "current_price": p.current_price,
            "unrealized_pnl": p.unrealized_pnl,
            "leverage": p.leverage,
            "strategy": p.strategy_used,
            "opened_at": p.opened_at.isoformat(),
        }
        for p in positions
    ]


@router.get("/memory")
async def get_trade_memories(
    limit: int = 50, db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get historical trades and their scores."""
    gen = TreasuryManager.get_active_generation(db)
    if not gen:
        return []
        
    memories = MemoryEngine.get_trade_history(db, gen.id, limit=limit)
    
    return [
        {
            "id": m.id,
            "symbol": m.symbol,
            "side": m.side,
            "pnl": m.pnl,
            "pnl_pct": m.pnl_pct,
            "strategy": m.strategy_used,
            "overall_score": m.overall_score,
            "lessons": m.lessons_learned,
            "closed_at": m.closed_at.isoformat() if m.closed_at else None,
        }
        for m in memories
    ]
