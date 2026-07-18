"""
Apex Autonomous Trader — Memory Engine
========================================
Layer 5: Remember everything. No deletion.

Every trade receives a Trade Score (0-100) across 5 dimensions:
  - Entry quality
  - Exit quality
  - Risk quality
  - Timing quality
  - Outcome quality
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from shared.db.models import TradeMemory, Generation, MarketSnapshot

logger = logging.getLogger("memory")


class MemoryEngine:
    """
    Permanent memory system.
    Records every trade, scores performance, identifies patterns.
    """

    @staticmethod
    def record_trade_open(
        db: Session,
        generation: Generation,
        symbol: str,
        side: str,
        entry_price: float,
        size: float,
        leverage: int,
        strategy: str,
        confidence: float,
        market_regime: str = None,
        indicators: Dict = None,
        reason: str = None,
    ) -> TradeMemory:
        """Record a trade opening in permanent memory."""
        memory = TradeMemory(
            generation_id=generation.id,
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            size=size,
            leverage=leverage,
            strategy_used=strategy,
            confidence_at_entry=confidence,
            market_regime=market_regime,
            indicators_snapshot=indicators,
            entry_reason=reason,
            opened_at=datetime.now(timezone.utc),
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)

        logger.info(
            f"Memory: Trade opened | {side} {symbol} @ ${entry_price:,.2f} | "
            f"Strategy: {strategy} | Confidence: {confidence:.0f}%"
        )
        return memory

    @staticmethod
    def record_trade_close(
        db: Session,
        memory: TradeMemory,
        exit_price: float,
        pnl: float,
        fee: float = 0.0,
        slippage: float = 0.0,
        exit_reason: str = None,
    ) -> TradeMemory:
        """Record a trade closing and calculate scores."""
        now = datetime.now(timezone.utc)

        memory.exit_price = exit_price
        memory.pnl = pnl
        memory.pnl_pct = (pnl / (memory.entry_price * memory.size)) * 100 if memory.entry_price * memory.size > 0 else 0
        memory.fee_paid = fee
        memory.slippage = slippage
        memory.exit_reason = exit_reason
        memory.closed_at = now

        # Calculate duration
        if memory.opened_at:
            delta = now - memory.opened_at
            memory.duration_seconds = int(delta.total_seconds())

        # ── Calculate Trade Scores ──
        memory.outcome_score = MemoryEngine._score_outcome(pnl, memory.pnl_pct)
        memory.risk_score = MemoryEngine._score_risk(memory)
        memory.entry_score = MemoryEngine._score_entry(memory)
        memory.exit_score = MemoryEngine._score_exit(memory)
        memory.timing_score = MemoryEngine._score_timing(memory)

        # Composite score (weighted average)
        memory.overall_score = round(
            memory.entry_score * 0.20 +
            memory.exit_score * 0.20 +
            memory.risk_score * 0.20 +
            memory.timing_score * 0.15 +
            memory.outcome_score * 0.25,
            1
        )

        # Generate lessons
        memory.lessons_learned = MemoryEngine._generate_lessons(memory)

        db.commit()

        logger.info(
            f"Memory: Trade closed | {memory.symbol} | PnL: ${pnl:+,.2f} ({memory.pnl_pct:+.1f}%) | "
            f"Score: {memory.overall_score}/100"
        )
        return memory

    @staticmethod
    def _score_outcome(pnl: float, pnl_pct: float) -> float:
        """Score based on final P&L result."""
        if pnl > 0:
            # Profitable: base 60 + bonus for size
            return min(100, 60 + abs(pnl_pct) * 4)
        else:
            # Loss: penalize based on severity
            return max(0, 50 - abs(pnl_pct) * 5)

    @staticmethod
    def _score_risk(memory: TradeMemory) -> float:
        """Score based on risk management quality."""
        score = 50

        # Good leverage usage (lower is better for risk)
        if memory.leverage <= 3:
            score += 20
        elif memory.leverage <= 5:
            score += 10
        elif memory.leverage <= 10:
            score += 0
        else:
            score -= 20

        # Position sizing (smaller positions = better risk management)
        if memory.pnl < 0:
            # Lost money — was the loss contained?
            if abs(memory.pnl_pct) < 2:
                score += 20  # Small loss, well managed
            elif abs(memory.pnl_pct) < 5:
                score += 10
            else:
                score -= 10  # Large loss

        if memory.pnl > 0:
            score += 10  # Positive outcome

        return max(0, min(100, score))

    @staticmethod
    def _score_entry(memory: TradeMemory) -> float:
        """Score entry quality based on confidence and subsequent movement."""
        score = 50

        # High confidence entries score better
        if memory.confidence_at_entry > 80:
            score += 20
        elif memory.confidence_at_entry > 60:
            score += 10

        # If trade was profitable, entry was good
        if memory.pnl and memory.pnl > 0:
            score += 20
        elif memory.pnl and memory.pnl < 0:
            score -= 10

        return max(0, min(100, score))

    @staticmethod
    def _score_exit(memory: TradeMemory) -> float:
        """Score exit quality."""
        score = 50

        if memory.pnl and memory.pnl > 0:
            # Profitable exit
            score += 25
            # Bonus if exit captured good portion of move
            if memory.pnl_pct and memory.pnl_pct > 3:
                score += 15
        else:
            # Did we cut losses quickly?
            if memory.duration_seconds and memory.duration_seconds < 3600:
                score += 10  # Quick loss cut
            if memory.pnl_pct and abs(memory.pnl_pct) < 2:
                score += 10  # Small loss

        return max(0, min(100, score))

    @staticmethod
    def _score_timing(memory: TradeMemory) -> float:
        """Score timing quality based on duration and market regime."""
        score = 50

        # Duration analysis
        hours = (memory.duration_seconds or 0) / 3600

        if memory.pnl and memory.pnl > 0:
            # Profitable: shorter is better (efficiency)
            if hours < 1:
                score += 30
            elif hours < 4:
                score += 20
            elif hours < 24:
                score += 10
        else:
            # Loss: shorter is better (quick cut)
            if hours < 0.5:
                score += 20
            elif hours < 2:
                score += 10
            elif hours > 24:
                score -= 10  # Held losing trade too long

        return max(0, min(100, score))

    @staticmethod
    def _generate_lessons(memory: TradeMemory) -> str:
        """Generate lessons learned from the trade."""
        lessons = []

        if memory.pnl and memory.pnl > 0:
            lessons.append(f"✅ Profitable {memory.strategy_used} trade on {memory.symbol}")
            if memory.pnl_pct and memory.pnl_pct > 5:
                lessons.append(f"Strong move captured ({memory.pnl_pct:+.1f}%)")
        else:
            lessons.append(f"❌ Loss on {memory.symbol} using {memory.strategy_used}")
            if memory.pnl_pct and abs(memory.pnl_pct) > 3:
                lessons.append("Consider tighter stop loss")

        if memory.market_regime:
            if memory.pnl and memory.pnl > 0:
                lessons.append(f"Strategy works well in {memory.market_regime} regime")
            else:
                lessons.append(f"Strategy may not suit {memory.market_regime} regime")

        if memory.overall_score < 40:
            lessons.append("Low score — review strategy parameters")

        return " | ".join(lessons)

    @staticmethod
    def get_trade_history(
        db: Session,
        generation_id: int = None,
        symbol: str = None,
        limit: int = 50,
    ):
        """Retrieve trade memories with optional filters."""
        query = db.query(TradeMemory)
        if generation_id:
            query = query.filter(TradeMemory.generation_id == generation_id)
        if symbol:
            query = query.filter(TradeMemory.symbol == symbol)
        return query.order_by(TradeMemory.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_best_strategies(db: Session, generation_id: int) -> Dict[str, Any]:
        """Analyze which strategies performed best in current generation."""
        memories = db.query(TradeMemory).filter(
            TradeMemory.generation_id == generation_id,
            TradeMemory.closed_at.isnot(None),
        ).all()

        strategy_stats = {}
        for m in memories:
            name = m.strategy_used or "unknown"
            if name not in strategy_stats:
                strategy_stats[name] = {"trades": 0, "wins": 0, "total_pnl": 0, "scores": []}
            strategy_stats[name]["trades"] += 1
            if m.pnl and m.pnl > 0:
                strategy_stats[name]["wins"] += 1
            strategy_stats[name]["total_pnl"] += m.pnl or 0
            if m.overall_score:
                strategy_stats[name]["scores"].append(m.overall_score)

        result = {}
        for name, stats in strategy_stats.items():
            result[name] = {
                "trades": stats["trades"],
                "win_rate": (stats["wins"] / stats["trades"] * 100) if stats["trades"] > 0 else 0,
                "total_pnl": round(stats["total_pnl"], 2),
                "avg_score": round(sum(stats["scores"]) / len(stats["scores"]), 1) if stats["scores"] else 0,
            }

        return result
