"""
Apex Autonomous Trader — Decision Engine
==========================================
Layer 2: Decide whether a trade should occur.

Orchestrates all trading strategies, applies market regime filters,
and produces final TradeDecisions.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

from apps.api.core.config import settings
from services.risk_engine.calculator import RiskCalculator

logger = logging.getLogger("decision_engine")


@dataclass
class TradeSignal:
    """Output from a single strategy."""
    strategy: str
    side: str           # "LONG", "SHORT", or "WAIT"
    confidence: float   # 0-100
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    reasoning: str = ""


@dataclass
class TradeDecision:
    """Final decision from the Decision Engine."""
    should_trade: bool
    side: str               # "LONG", "SHORT", or "WAIT"
    symbol: str
    confidence: float       # 0-100
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    leverage: int = 5
    position_size_pct: float = 2.0
    strategy_used: str = ""
    reasoning: str = ""
    risk_reward: float = 0.0
    signals: List[TradeSignal] = field(default_factory=list)


class DecisionEngine:
    """
    Orchestrates all strategies and produces final trade decisions.
    Applies market regime filtering and strategy weighting.
    """

    def __init__(self, strategy_weights: Dict[str, float] = None):
        self.strategy_weights = strategy_weights or {
            "trend_following": 1.0,
            "momentum": 0.8,
            "breakout": 0.7,
            "mean_reversion": 0.6,
            "funding_rate": 0.5,
        }

    def decide(
        self,
        market_assessment: Dict[str, Any],
        treasury_balance: float,
        max_leverage: int = None,
        generation_status: str = "ACTIVE",
    ) -> TradeDecision:
        """
        Main decision pipeline:
        1. Collect signals from all strategies
        2. Filter by market regime
        3. Weight and aggregate
        4. Calculate risk parameters
        5. Produce final decision
        """
        symbol = market_assessment.get("symbol", "")
        indicators = market_assessment.get("indicators", {})
        regime = market_assessment.get("regime", "UNKNOWN")
        long_score = market_assessment.get("long_score", 0)
        short_score = market_assessment.get("short_score", 0)

        if not market_assessment.get("has_data"):
            return TradeDecision(
                should_trade=False, side="WAIT", symbol=symbol,
                confidence=0, reasoning="Insufficient market data"
            )

        # ── Collect strategy signals ──
        signals = []
        signals.append(self._trend_following(indicators, market_assessment))
        signals.append(self._momentum_strategy(indicators, market_assessment))
        signals.append(self._breakout_strategy(indicators, market_assessment))
        signals.append(self._mean_reversion(indicators, market_assessment))
        signals.append(self._funding_rate_strategy(market_assessment))

        # ── Filter by regime ──
        filtered = self._apply_regime_filter(signals, regime)

        # ── Aggregate signals ──
        if not filtered:
            return TradeDecision(
                should_trade=False, side="WAIT", symbol=symbol,
                confidence=0, reasoning="No strategies passed regime filter",
                signals=signals,
            )

        weighted_long = 0.0
        weighted_short = 0.0
        total_weight = 0.0

        for sig in filtered:
            weight = self.strategy_weights.get(sig.strategy, 0.5)
            if sig.side == "LONG":
                weighted_long += sig.confidence * weight
            elif sig.side == "SHORT":
                weighted_short += sig.confidence * weight
            total_weight += weight

        if total_weight == 0:
            return TradeDecision(
                should_trade=False, side="WAIT", symbol=symbol,
                confidence=0, reasoning="Zero weight", signals=signals
            )

        # Determine direction
        if weighted_long > weighted_short:
            side = "LONG"
            confidence = (weighted_long / (total_weight * 100)) * 100
        elif weighted_short > weighted_long:
            side = "SHORT"
            confidence = (weighted_short / (total_weight * 100)) * 100
        else:
            return TradeDecision(
                should_trade=False, side="WAIT", symbol=symbol,
                confidence=0, reasoning="Signals are balanced — no edge",
                signals=signals,
            )

        # ── Threshold check ──
        threshold = settings.SIGNAL_CONVICTION_THRESHOLD * 100
        if confidence < threshold:
            return TradeDecision(
                should_trade=False, side="WAIT", symbol=symbol,
                confidence=round(confidence, 1),
                reasoning=f"Confidence {confidence:.1f}% below threshold {threshold:.0f}%",
                signals=signals,
            )

        # ── Calculate risk parameters ──
        current_price = indicators.get("close", 0)
        atr = indicators.get("ATR_14", 0)

        if current_price <= 0 or not atr or atr <= 0:
            return TradeDecision(
                should_trade=False, side="WAIT", symbol=symbol,
                confidence=round(confidence, 1),
                reasoning="Cannot calculate risk: missing price or ATR",
                signals=signals,
            )

        stop_loss = RiskCalculator.calculate_stop_loss(side, current_price, atr, multiplier=1.5)
        take_profit = RiskCalculator.calculate_take_profit(side, current_price, stop_loss, risk_reward_ratio=2.0)
        risk_reward = RiskCalculator.calculate_risk_reward(current_price, stop_loss, take_profit)

        # Leverage
        lev = max_leverage or settings.DEFAULT_LEVERAGE
        if generation_status == "SURVIVAL":
            lev = min(lev, 3)
        leverage = RiskCalculator.validate_leverage(lev)

        # Position size (reduced in survival)
        pos_size_pct = settings.MAX_POSITION_SIZE_PCT
        if generation_status == "SURVIVAL":
            pos_size_pct = pos_size_pct / 2

        # Best strategy attribution
        best = max(filtered, key=lambda s: s.confidence)

        return TradeDecision(
            should_trade=True,
            side=side,
            symbol=symbol,
            confidence=round(confidence, 1),
            entry_price=current_price,
            stop_loss=round(stop_loss, 4),
            take_profit=round(take_profit, 4),
            leverage=leverage,
            position_size_pct=pos_size_pct,
            strategy_used=best.strategy,
            reasoning=best.reasoning,
            risk_reward=risk_reward,
            signals=signals,
        )

    # ─── STRATEGIES ───────────────────────────────────────

    def _trend_following(self, ind: Dict, assessment: Dict) -> TradeSignal:
        """EMA alignment + ADX confirmation + SuperTrend."""
        trend = assessment.get("trend", {})
        direction = trend.get("direction", "NEUTRAL")
        strength = trend.get("strength", "WEAK")
        adx = trend.get("adx", 0)
        supertrend = trend.get("supertrend_bullish")

        confidence = 0
        side = "WAIT"

        if direction == "BULLISH" and strength in ("STRONG", "VERY_STRONG"):
            side = "LONG"
            confidence = 60 + min(30, adx)
            if supertrend:
                confidence += 10
        elif direction == "BEARISH" and strength in ("STRONG", "VERY_STRONG"):
            side = "SHORT"
            confidence = 60 + min(30, adx)
            if supertrend is False:
                confidence += 10

        return TradeSignal(
            strategy="trend_following",
            side=side,
            confidence=min(100, confidence),
            reasoning=f"Trend: {direction} ({strength}), ADX={adx:.0f}",
        )

    def _momentum_strategy(self, ind: Dict, assessment: Dict) -> TradeSignal:
        """RSI + MACD acceleration."""
        mom = assessment.get("momentum", {})
        rsi = mom.get("rsi", 50)
        rsi_zone = mom.get("rsi_zone", "NEUTRAL")
        macd_bullish = mom.get("macd_bullish", False)
        roc = mom.get("roc_10", 0)

        confidence = 0
        side = "WAIT"

        if rsi > 55 and macd_bullish and roc > 0:
            side = "LONG"
            confidence = 50 + min(30, abs(rsi - 50)) + min(20, abs(roc) * 5)
        elif rsi < 45 and not macd_bullish and roc < 0:
            side = "SHORT"
            confidence = 50 + min(30, abs(50 - rsi)) + min(20, abs(roc) * 5)

        return TradeSignal(
            strategy="momentum",
            side=side,
            confidence=min(100, confidence),
            reasoning=f"RSI={rsi:.0f} ({rsi_zone}), MACD {'↑' if macd_bullish else '↓'}, ROC={roc:.1f}%",
        )

    def _breakout_strategy(self, ind: Dict, assessment: Dict) -> TradeSignal:
        """Bollinger Band squeeze → expansion."""
        vol = assessment.get("volatility", {})
        is_squeeze = vol.get("is_squeeze", False)
        bb_width = vol.get("bb_width", 0)
        trend_dir = assessment.get("trend", {}).get("direction", "NEUTRAL")
        close = ind.get("close", 0)
        bb_upper = ind.get("BBU_20_2.0", close)
        bb_lower = ind.get("BBL_20_2.0", close)

        confidence = 0
        side = "WAIT"

        if close and bb_upper and close > bb_upper and not is_squeeze:
            side = "LONG"
            confidence = 65
            if trend_dir == "BULLISH":
                confidence += 15
        elif close and bb_lower and close < bb_lower and not is_squeeze:
            side = "SHORT"
            confidence = 65
            if trend_dir == "BEARISH":
                confidence += 15

        return TradeSignal(
            strategy="breakout",
            side=side,
            confidence=min(100, confidence),
            reasoning=f"BB Width={bb_width:.1f}, Squeeze={'Yes' if is_squeeze else 'No'}",
        )

    def _mean_reversion(self, ind: Dict, assessment: Dict) -> TradeSignal:
        """RSI oversold/overbought at key levels + BB reversion."""
        mom = assessment.get("momentum", {})
        rsi = mom.get("rsi", 50)
        close = ind.get("close", 0)
        vwap = ind.get("VWAP", close)
        bb_lower = ind.get("BBL_20_2.0", close)
        bb_upper = ind.get("BBU_20_2.0", close)

        confidence = 0
        side = "WAIT"

        # Only in RANGING regime
        regime = assessment.get("regime", "UNKNOWN")
        if regime not in ("RANGING", "UNKNOWN"):
            return TradeSignal(strategy="mean_reversion", side="WAIT", confidence=0,
                             reasoning=f"Regime {regime} not suitable for mean reversion")

        if rsi < 25 and close and bb_lower and close <= bb_lower:
            side = "LONG"
            confidence = 70 + (25 - rsi)
        elif rsi > 75 and close and bb_upper and close >= bb_upper:
            side = "SHORT"
            confidence = 70 + (rsi - 75)

        return TradeSignal(
            strategy="mean_reversion",
            side=side,
            confidence=min(100, confidence),
            reasoning=f"RSI={rsi:.0f}, Price vs VWAP: {'above' if close > (vwap or 0) else 'below'}",
        )

    def _funding_rate_strategy(self, assessment: Dict) -> TradeSignal:
        """Trade against extreme funding rates."""
        deriv = assessment.get("derivatives", {})
        contrarian = deriv.get("funding_contrarian")
        funding_rate = deriv.get("funding_rate", 0)
        crowd = deriv.get("crowd_position", "BALANCED")

        if not contrarian:
            return TradeSignal(strategy="funding_rate", side="WAIT", confidence=0,
                             reasoning=f"Funding rate {funding_rate:.4f} not extreme")

        confidence = 60
        if crowd in ("LONG_CROWDED", "SHORT_CROWDED"):
            confidence += 15
        if abs(funding_rate) > 0.02:
            confidence += 15

        return TradeSignal(
            strategy="funding_rate",
            side=contrarian,
            confidence=min(100, confidence),
            reasoning=f"Funding={funding_rate:.4f}, Crowd={crowd}, Contrarian={contrarian}",
        )

    def _apply_regime_filter(self, signals: List[TradeSignal], regime: str) -> List[TradeSignal]:
        """Filter out strategies that don't work in the current regime."""
        # Regime → allowed strategies
        regime_filter = {
            "BULL_TREND": {"trend_following", "momentum", "breakout", "funding_rate"},
            "BEAR_TREND": {"trend_following", "momentum", "breakout", "funding_rate"},
            "RANGING": {"mean_reversion", "funding_rate", "breakout"},
            "HIGH_VOLATILITY": {"momentum", "funding_rate"},
            "CRASH": {"funding_rate"},  # Only contrarian in crashes
            "RECOVERY": {"trend_following", "momentum"},
            "UNKNOWN": {"trend_following", "momentum", "mean_reversion", "funding_rate", "breakout"},
        }

        allowed = regime_filter.get(regime, set())
        filtered = [s for s in signals if s.strategy in allowed and s.side != "WAIT"]
        return filtered
