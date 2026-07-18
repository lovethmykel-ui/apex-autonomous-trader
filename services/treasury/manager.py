"""
Apex Autonomous Trader — Treasury Manager
==========================================
Every dollar in the treasury represents life.
The treasury is the agent's life force.

Responsibilities:
  - Real-time balance monitoring
  - Drawdown calculation (daily/weekly/monthly)
  - Risk allocation per trade
  - Automatic trading halt on limit breach
  - Survival mode activation
  - Death event triggering
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from shared.db.models import (
    Generation, GenerationStatus, TreasurySnapshot,
    Balance, Position, TradeMemory
)
from apps.api.core.config import settings

logger = logging.getLogger("treasury")


class TreasuryManager:
    """
    Protects capital. The most important system in the agent.
    If this fails, the agent dies.
    """

    @staticmethod
    def get_current_treasury(db: Session, account_id: int) -> float:
        """Get current USDT balance."""
        bal = db.query(Balance).filter(
            Balance.account_id == account_id,
            Balance.asset == "USDT"
        ).first()
        return (bal.free + bal.locked) if bal else 0.0

    @staticmethod
    def get_active_generation(db: Session) -> Optional[Generation]:
        """Get the currently active generation."""
        return db.query(Generation).filter(
            Generation.status.in_([
                GenerationStatus.ACTIVE.value,
                GenerationStatus.SURVIVAL.value,
                GenerationStatus.DYING.value,
            ])
        ).order_by(Generation.number.desc()).first()

    @staticmethod
    def create_generation(
        db: Session,
        treasury_amount: float,
        death_threshold_pct: float = None,
    ) -> Generation:
        """
        Spawn a new generation.
        The death threshold is calculated as a percentage of initial treasury.
        """
        if death_threshold_pct is None:
            death_threshold_pct = settings.GENERATION_DEATH_THRESHOLD_PCT

        # Calculate generation number
        last_gen = db.query(Generation).order_by(Generation.number.desc()).first()
        gen_number = (last_gen.number + 1) if last_gen else 1

        death_threshold = treasury_amount * (death_threshold_pct / 100.0)

        generation = Generation(
            number=gen_number,
            status=GenerationStatus.ACTIVE.value,
            initial_treasury=treasury_amount,
            current_treasury=treasury_amount,
            peak_treasury=treasury_amount,
            death_threshold=death_threshold,
        )
        db.add(generation)
        db.commit()
        db.refresh(generation)

        logger.info(
            f"Generation G-{gen_number:02d} BORN | "
            f"Treasury: ${treasury_amount:,.2f} | "
            f"Death Threshold: ${death_threshold:,.2f}"
        )
        return generation

    @staticmethod
    def update_treasury(
        db: Session,
        generation: Generation,
        current_balance: float,
    ) -> Dict[str, Any]:
        """
        Update the generation's treasury state and check all risk limits.
        Returns a status dict with any alerts triggered.
        """
        alerts = []
        generation.current_treasury = current_balance

        # Update peak
        if current_balance > generation.peak_treasury:
            generation.peak_treasury = current_balance

        # ─── DEATH CHECK ───
        if current_balance <= generation.death_threshold:
            generation.status = GenerationStatus.DEAD.value
            generation.died_at = datetime.now(timezone.utc)
            generation.death_reason = (
                f"Treasury ${current_balance:,.2f} fell below "
                f"death threshold ${generation.death_threshold:,.2f}"
            )
            db.commit()
            alerts.append({
                "type": "DEATH",
                "message": generation.death_reason,
                "severity": "CRITICAL",
            })
            return {"status": "DEAD", "alerts": alerts, "can_trade": False}

        # ─── DRAWDOWN CALCULATIONS ───
        drawdowns = TreasuryManager.calculate_drawdowns(db, generation)

        # Daily drawdown check
        if drawdowns["daily_pct"] >= settings.MAX_DAILY_DRAWDOWN_PCT:
            alerts.append({
                "type": "DAILY_LIMIT",
                "message": f"Daily drawdown {drawdowns['daily_pct']:.1f}% >= {settings.MAX_DAILY_DRAWDOWN_PCT}%",
                "severity": "HIGH",
            })

        # Weekly drawdown check → Survival mode
        if drawdowns["weekly_pct"] >= settings.MAX_WEEKLY_DRAWDOWN_PCT:
            if generation.status != GenerationStatus.SURVIVAL.value:
                generation.status = GenerationStatus.SURVIVAL.value
                alerts.append({
                    "type": "SURVIVAL_MODE",
                    "message": f"Weekly drawdown {drawdowns['weekly_pct']:.1f}% — SURVIVAL MODE ACTIVATED",
                    "severity": "HIGH",
                })

        # Monthly drawdown check → Dying
        if drawdowns["monthly_pct"] >= settings.MAX_MONTHLY_DRAWDOWN_PCT:
            if generation.status != GenerationStatus.DYING.value:
                generation.status = GenerationStatus.DYING.value
                alerts.append({
                    "type": "DYING",
                    "message": f"Monthly drawdown {drawdowns['monthly_pct']:.1f}% — GENERATION MARKED AS FAILING",
                    "severity": "CRITICAL",
                })

        # Update max drawdown
        current_dd = TreasuryManager._peak_drawdown_pct(generation)
        if current_dd > generation.max_drawdown_pct:
            generation.max_drawdown_pct = current_dd

        db.commit()

        can_trade = (
            generation.status in (GenerationStatus.ACTIVE.value, GenerationStatus.SURVIVAL.value)
            and drawdowns["daily_pct"] < settings.MAX_DAILY_DRAWDOWN_PCT
        )

        return {
            "status": generation.status,
            "alerts": alerts,
            "can_trade": can_trade,
            "drawdowns": drawdowns,
        }

    @staticmethod
    def calculate_drawdowns(db: Session, generation: Generation) -> Dict[str, float]:
        """Calculate daily, weekly, and monthly drawdowns."""
        now = datetime.now(timezone.utc)

        # Get snapshots for each time window
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(weeks=1)
        month_ago = now - timedelta(days=30)

        daily_start = TreasuryManager._get_balance_at(db, generation.id, day_ago)
        weekly_start = TreasuryManager._get_balance_at(db, generation.id, week_ago)
        monthly_start = TreasuryManager._get_balance_at(db, generation.id, month_ago)

        current = generation.current_treasury

        def dd_pct(start_bal: float) -> float:
            if start_bal <= 0:
                return 0.0
            return max(0.0, ((start_bal - current) / start_bal) * 100)

        return {
            "daily_pct": dd_pct(daily_start),
            "weekly_pct": dd_pct(weekly_start),
            "monthly_pct": dd_pct(monthly_start),
            "daily_pnl": current - daily_start,
            "weekly_pnl": current - weekly_start,
            "monthly_pnl": current - monthly_start,
        }

    @staticmethod
    def _get_balance_at(
        db: Session,
        generation_id: int,
        target_time: datetime,
    ) -> float:
        """Get treasury balance at a specific point in time from snapshots."""
        snapshot = db.query(TreasurySnapshot).filter(
            TreasurySnapshot.generation_id == generation_id,
            TreasurySnapshot.timestamp <= target_time,
        ).order_by(TreasurySnapshot.timestamp.desc()).first()

        if snapshot:
            return snapshot.balance

        # Fallback to initial treasury
        gen = db.query(Generation).filter(Generation.id == generation_id).first()
        return gen.initial_treasury if gen else 0.0

    @staticmethod
    def _peak_drawdown_pct(generation: Generation) -> float:
        """Calculate current peak-to-trough drawdown percentage."""
        if generation.peak_treasury <= 0:
            return 0.0
        return max(
            0.0,
            ((generation.peak_treasury - generation.current_treasury) / generation.peak_treasury) * 100
        )

    @staticmethod
    def take_snapshot(db: Session, generation: Generation):
        """Take a point-in-time treasury snapshot for historical tracking."""
        drawdowns = TreasuryManager.calculate_drawdowns(db, generation)

        # Count open positions
        open_positions = db.query(Position).filter(
            Position.generation_id == generation.id
        ).count()

        snapshot = TreasurySnapshot(
            generation_id=generation.id,
            balance=generation.current_treasury,
            daily_pnl=drawdowns["daily_pnl"],
            weekly_pnl=drawdowns["weekly_pnl"],
            monthly_pnl=drawdowns["monthly_pnl"],
            daily_drawdown_pct=drawdowns["daily_pct"],
            weekly_drawdown_pct=drawdowns["weekly_pct"],
            monthly_drawdown_pct=drawdowns["monthly_pct"],
            open_positions_count=open_positions,
        )
        db.add(snapshot)
        db.commit()

    @staticmethod
    def calculate_max_trade_allocation(
        generation: Generation,
    ) -> Tuple[float, int]:
        """
        Calculate maximum capital for next trade based on treasury state.
        Returns (max_amount_usdt, max_leverage).
        """
        balance = generation.current_treasury

        # Base allocation: MAX_POSITION_SIZE_PCT of treasury
        max_allocation_pct = settings.MAX_POSITION_SIZE_PCT

        # In survival mode, halve the allocation
        if generation.status == GenerationStatus.SURVIVAL.value:
            max_allocation_pct = max_allocation_pct / 2
            logger.warning("SURVIVAL MODE: Position size halved")

        max_amount = balance * (max_allocation_pct / 100.0)

        # Leverage capping
        max_leverage = settings.MAX_LEVERAGE
        if generation.status == GenerationStatus.SURVIVAL.value:
            max_leverage = min(max_leverage, 3)  # Max 3x in survival

        return max_amount, max_leverage

    @staticmethod
    def kill_generation(db: Session, generation: Generation, reason: str = "Killed by owner"):
        """Manually terminate a generation."""
        generation.status = GenerationStatus.RETIRED.value
        generation.died_at = datetime.now(timezone.utc)
        generation.death_reason = reason
        db.commit()
        logger.info(f"Generation G-{generation.number:02d} KILLED: {reason}")

    @staticmethod
    def get_generation_summary(generation: Generation) -> Dict[str, Any]:
        """Build a summary of a generation's performance."""
        return {
            "generation": f"G-{generation.number:02d}",
            "status": generation.status,
            "initial_treasury": generation.initial_treasury,
            "current_treasury": generation.current_treasury,
            "peak_treasury": generation.peak_treasury,
            "total_pnl": generation.total_pnl,
            "total_trades": generation.total_trades,
            "win_rate": generation.win_rate,
            "max_drawdown_pct": generation.max_drawdown_pct,
            "death_threshold": generation.death_threshold,
            "created_at": generation.created_at.isoformat() if generation.created_at else None,
            "died_at": generation.died_at.isoformat() if generation.died_at else None,
            "death_reason": generation.death_reason,
        }
