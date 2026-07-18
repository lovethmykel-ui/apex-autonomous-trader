"""
Apex Autonomous Trader — Risk Calculator
==========================================
Hard rules. No exceptions.
"""

import logging
from typing import Dict, Any, Tuple
from apps.api.core.config import settings

logger = logging.getLogger("risk_engine")


class RiskCalculator:
    """
    Institutional-grade risk management calculations.
    Every trade must pass through this module.
    """

    @staticmethod
    def calculate_position_size(
        treasury_balance: float,
        risk_pct: float,
        entry_price: float,
        stop_loss_price: float,
        leverage: int = 1,
    ) -> Dict[str, Any]:
        """
        Calculate position size based on risk amount.

        Risk Amount = Treasury * (Risk % / 100)
        Risk Per Unit = |Entry - Stop Loss|
        Position Size = Risk Amount / Risk Per Unit
        """
        if treasury_balance <= 0 or risk_pct <= 0:
            return {"size": 0.0, "error": "Invalid balance or risk percentage"}

        if entry_price <= 0 or stop_loss_price <= 0:
            return {"size": 0.0, "error": "Invalid price"}

        if entry_price == stop_loss_price:
            return {"size": 0.0, "error": "Entry and Stop Loss cannot be equal"}

        # Enforce max position size
        effective_risk_pct = min(risk_pct, settings.MAX_POSITION_SIZE_PCT)

        risk_amount = treasury_balance * (effective_risk_pct / 100.0)
        risk_per_unit = abs(entry_price - stop_loss_price)
        position_size = risk_amount / risk_per_unit

        total_exposure = position_size * entry_price
        required_margin = total_exposure / leverage
        leverage_required = total_exposure / treasury_balance

        return {
            "size": round(position_size, 6),
            "risk_amount": round(risk_amount, 2),
            "risk_per_unit": round(risk_per_unit, 4),
            "total_exposure": round(total_exposure, 2),
            "required_margin": round(required_margin, 2),
            "leverage_used": round(leverage_required, 2),
            "risk_pct_applied": effective_risk_pct,
        }

    @staticmethod
    def calculate_kelly_fraction(
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        half_kelly: bool = True,
    ) -> Dict[str, Any]:
        """
        Kelly Criterion for optimal position sizing.
        f* = W - ((1 - W) / R)
        Institutional practice: Always use half-Kelly.
        """
        if win_rate < 0 or win_rate > 1:
            return {"kelly_fraction": 0.0, "error": "Win rate must be between 0 and 1"}
        if avg_loss <= 0:
            return {"kelly_fraction": 0.0, "error": "Average loss must be positive"}
        if avg_win < 0:
            return {"kelly_fraction": 0.0, "error": "Average win must be non-negative"}

        R = avg_win / avg_loss
        kelly = win_rate - ((1 - win_rate) / R)
        recommended = (kelly / 2.0) if half_kelly else kelly
        recommended = max(0.0, recommended)

        return {
            "full_kelly": round(kelly, 4),
            "recommended_risk_pct": round(recommended * 100, 2),
            "win_loss_ratio": round(R, 2),
        }

    @staticmethod
    def calculate_stop_loss(
        side: str,
        entry_price: float,
        atr: float,
        multiplier: float = 1.5,
    ) -> float:
        """
        ATR-based stop loss calculation.
        LONG: entry - (ATR * multiplier)
        SHORT: entry + (ATR * multiplier)
        """
        distance = atr * multiplier
        if side.upper() == "LONG":
            return entry_price - distance
        else:
            return entry_price + distance

    @staticmethod
    def calculate_take_profit(
        side: str,
        entry_price: float,
        stop_loss_price: float,
        risk_reward_ratio: float = 2.0,
    ) -> float:
        """
        Calculate take profit based on risk-reward ratio.
        TP distance = SL distance * RR ratio
        """
        sl_distance = abs(entry_price - stop_loss_price)
        tp_distance = sl_distance * risk_reward_ratio

        if side.upper() == "LONG":
            return entry_price + tp_distance
        else:
            return entry_price - tp_distance

    @staticmethod
    def calculate_trailing_stop(
        side: str,
        current_price: float,
        peak_price: float,
        trough_price: float,
        trailing_pct: float = 2.0,
    ) -> float:
        """Calculate trailing stop price."""
        factor = trailing_pct / 100.0

        if side.upper() == "LONG":
            return peak_price * (1 - factor)
        else:
            return trough_price * (1 + factor)

    @staticmethod
    def validate_leverage(requested: int, max_allowed: int = None) -> int:
        """Enforce leverage limits."""
        if max_allowed is None:
            max_allowed = settings.MAX_LEVERAGE

        # Never exceed emergency cap
        capped = min(requested, max_allowed, settings.EMERGENCY_LEVERAGE_CAP)
        capped = max(1, capped)

        if capped != requested:
            logger.warning(
                f"Leverage capped: requested {requested}x → applied {capped}x"
            )
        return capped

    @staticmethod
    def calculate_risk_reward(
        entry_price: float,
        stop_loss: float,
        take_profit: float,
    ) -> float:
        """Calculate risk/reward ratio."""
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        if risk <= 0:
            return 0.0
        return round(reward / risk, 2)

    @staticmethod
    def should_trade(
        daily_drawdown_pct: float,
        weekly_drawdown_pct: float,
        monthly_drawdown_pct: float,
        generation_status: str,
    ) -> Tuple[bool, str]:
        """
        Final gate check before any trade.
        Returns (allowed, reason).
        """
        if generation_status == "DEAD":
            return False, "Generation is DEAD"

        if generation_status == "RETIRED":
            return False, "Generation is RETIRED"

        if generation_status == "DYING":
            return False, "Generation is DYING — no new trades"

        if daily_drawdown_pct >= settings.MAX_DAILY_DRAWDOWN_PCT:
            return False, f"Daily drawdown limit reached ({daily_drawdown_pct:.1f}%)"

        if weekly_drawdown_pct >= settings.MAX_WEEKLY_DRAWDOWN_PCT:
            return False, f"Weekly drawdown limit reached ({weekly_drawdown_pct:.1f}%)"

        if monthly_drawdown_pct >= settings.MAX_MONTHLY_DRAWDOWN_PCT:
            return False, f"Monthly drawdown limit reached ({monthly_drawdown_pct:.1f}%)"

        return True, "OK"
