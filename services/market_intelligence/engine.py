"""
Apex Autonomous Trader — Market Intelligence Engine
====================================================
Layer 1: Understand the market.

Combines all sub-analyzers into a unified market assessment.
Outputs: MarketRegime, confidence scores, trade opportunities.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from services.indicator_engine.engine import IndicatorEngine
from shared.db.models import MarketRegime

logger = logging.getLogger("market_intelligence")


class MarketIntelligence:
    """
    Orchestrates all market analysis sub-systems.
    Produces a unified MarketAssessment for the Decision Engine.
    """

    @classmethod
    def analyze(
        cls,
        candles_5m: List[Dict[str, Any]],
        candles_1h: List[Dict[str, Any]] = None,
        candles_4h: List[Dict[str, Any]] = None,
        funding_rate: float = 0.0,
        open_interest: float = 0.0,
        long_short_ratio: float = 0.5,
        symbol: str = "",
    ) -> Dict[str, Any]:
        """
        Run full market analysis pipeline.
        Returns a comprehensive MarketAssessment dict.
        """
        # Convert candles to DataFrames and compute indicators
        df_5m = IndicatorEngine.candles_to_dataframe(candles_5m)
        if len(df_5m) < 20:
            return cls._empty_assessment(symbol, "Insufficient data")

        df_5m = IndicatorEngine.calculate_all(df_5m)
        latest = IndicatorEngine.get_latest(df_5m)

        # ── Trend Analysis ──
        trend = cls._analyze_trend(latest, df_5m)

        # ── Momentum Analysis ──
        momentum = cls._analyze_momentum(latest)

        # ── Volume Analysis ──
        volume = cls._analyze_volume(latest, df_5m)

        # ── Volatility Analysis ──
        volatility = cls._analyze_volatility(latest, df_5m)

        # ── Derivatives Analysis ──
        derivatives = cls._analyze_derivatives(funding_rate, open_interest, long_short_ratio)

        # ── Market Regime Detection ──
        regime, regime_confidence = cls._detect_regime(trend, momentum, volatility)

        # ── Composite Scores ──
        long_score = cls._calculate_long_score(trend, momentum, volume, derivatives)
        short_score = cls._calculate_short_score(trend, momentum, volume, derivatives)

        return {
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "regime": regime,
            "regime_confidence": regime_confidence,
            "trend": trend,
            "momentum": momentum,
            "volume": volume,
            "volatility": volatility,
            "derivatives": derivatives,
            "long_score": long_score,
            "short_score": short_score,
            "indicators": latest,
            "has_data": True,
        }

    @classmethod
    def _analyze_trend(cls, latest: Dict, df) -> Dict[str, Any]:
        """Determine trend direction and strength."""
        ema_9 = latest.get("EMA_9")
        ema_20 = latest.get("EMA_20")
        ema_50 = latest.get("EMA_50")
        ema_200 = latest.get("EMA_200")
        adx = latest.get("ADX_14")
        close = latest.get("close", 0)

        # EMA alignment score
        bullish_alignment = 0
        bearish_alignment = 0

        if ema_9 and ema_20:
            if ema_9 > ema_20:
                bullish_alignment += 1
            else:
                bearish_alignment += 1

        if ema_20 and ema_50:
            if ema_20 > ema_50:
                bullish_alignment += 1
            else:
                bearish_alignment += 1

        if ema_50 and ema_200:
            if ema_50 > ema_200:
                bullish_alignment += 1
            else:
                bearish_alignment += 1

        if close and ema_200:
            if close > ema_200:
                bullish_alignment += 1
            else:
                bearish_alignment += 1

        # Direction
        if bullish_alignment > bearish_alignment:
            direction = "BULLISH"
        elif bearish_alignment > bullish_alignment:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        # Strength from ADX
        strength = "WEAK"
        adx_val = adx if adx else 0
        if adx_val > 40:
            strength = "VERY_STRONG"
        elif adx_val > 25:
            strength = "STRONG"
        elif adx_val > 20:
            strength = "MODERATE"

        # SuperTrend direction
        st_col = [c for c in df.columns if "SUPERTd" in str(c)]
        supertrend_bullish = False
        if st_col:
            st_val = latest.get(st_col[0])
            supertrend_bullish = st_val == 1 if st_val is not None else None

        return {
            "direction": direction,
            "strength": strength,
            "adx": adx_val,
            "bullish_alignment": bullish_alignment,
            "bearish_alignment": bearish_alignment,
            "supertrend_bullish": supertrend_bullish,
            "score": (bullish_alignment - bearish_alignment) / 4.0 * 100,  # -100 to 100
        }

    @classmethod
    def _analyze_momentum(cls, latest: Dict) -> Dict[str, Any]:
        """Analyze momentum indicators."""
        rsi = latest.get("RSI_14", 50)
        macd = latest.get("MACD_12_26_9", 0)
        macd_signal = latest.get("MACDs_12_26_9", 0)
        macd_hist = latest.get("MACDh_12_26_9", 0)
        willr = latest.get("WILLR_14", -50)
        roc_10 = latest.get("ROC_10", 0)

        # RSI zones
        rsi_val = rsi if rsi else 50
        if rsi_val > 70:
            rsi_zone = "OVERBOUGHT"
        elif rsi_val < 30:
            rsi_zone = "OVERSOLD"
        elif rsi_val > 60:
            rsi_zone = "BULLISH"
        elif rsi_val < 40:
            rsi_zone = "BEARISH"
        else:
            rsi_zone = "NEUTRAL"

        # MACD momentum
        macd_val = macd if macd else 0
        macd_sig = macd_signal if macd_signal else 0
        macd_bullish = macd_val > macd_sig
        macd_hist_val = macd_hist if macd_hist else 0
        macd_accelerating = abs(macd_hist_val) > 0

        # Composite momentum score (-100 to 100)
        score = 0
        score += (rsi_val - 50) * 1.5  # RSI contribution
        score += 20 if macd_bullish else -20
        score += min(20, max(-20, (roc_10 or 0) * 2))

        return {
            "rsi": rsi_val,
            "rsi_zone": rsi_zone,
            "macd": macd_val,
            "macd_signal": macd_sig,
            "macd_histogram": macd_hist_val,
            "macd_bullish": macd_bullish,
            "williams_r": willr if willr else -50,
            "roc_10": roc_10 if roc_10 else 0,
            "score": max(-100, min(100, score)),
        }

    @classmethod
    def _analyze_volume(cls, latest: Dict, df) -> Dict[str, Any]:
        """Analyze volume dynamics."""
        obv = latest.get("OBV", 0)
        cmf = latest.get("CMF_20", 0)
        current_vol = latest.get("volume", 0)

        # Volume relative to average
        avg_vol = df["volume"].rolling(20).mean().iloc[-1] if len(df) >= 20 else current_vol
        vol_ratio = (current_vol / avg_vol) if avg_vol > 0 else 1.0

        # Volume trend (OBV direction)
        obv_sma = df["OBV"].rolling(10).mean().iloc[-1] if "OBV" in df.columns and len(df) >= 10 else obv
        obv_bullish = (obv or 0) > (obv_sma if obv_sma else 0)

        # CMF interpretation
        cmf_val = cmf if cmf else 0
        money_flow = "INFLOW" if cmf_val > 0.05 else ("OUTFLOW" if cmf_val < -0.05 else "NEUTRAL")

        return {
            "current": current_vol if current_vol else 0,
            "avg_20": avg_vol if avg_vol else 0,
            "ratio": round(vol_ratio, 2),
            "is_above_avg": vol_ratio > 1.2,
            "is_spike": vol_ratio > 2.0,
            "obv_bullish": obv_bullish,
            "cmf": cmf_val,
            "money_flow": money_flow,
            "score": min(100, max(-100, (vol_ratio - 1.0) * 50 + (20 if obv_bullish else -20))),
        }

    @classmethod
    def _analyze_volatility(cls, latest: Dict, df) -> Dict[str, Any]:
        """Analyze volatility conditions."""
        atr = latest.get("ATR_14", 0)
        close = latest.get("close", 1)

        # ATR as percentage of price
        atr_val = atr if atr else 0
        atr_pct = (atr_val / close * 100) if close > 0 else 0

        # Bollinger Band width
        bb_upper = latest.get("BBU_20_2.0", close)
        bb_lower = latest.get("BBL_20_2.0", close)
        bb_mid = latest.get("BBM_20_2.0", close)

        bb_width = 0
        if bb_mid and bb_mid > 0:
            bb_width = ((bb_upper or close) - (bb_lower or close)) / bb_mid * 100

        # Squeeze detection (narrow BB)
        is_squeeze = bb_width < 3.0

        # Historical ATR percentile
        if "ATR_14" in df.columns and len(df) >= 50:
            atr_series = df["ATR_14"].dropna()
            if len(atr_series) > 0:
                atr_percentile = (atr_series < atr_val).sum() / len(atr_series) * 100
            else:
                atr_percentile = 50
        else:
            atr_percentile = 50

        # Regime
        if atr_percentile > 80:
            vol_regime = "HIGH"
        elif atr_percentile < 20:
            vol_regime = "LOW"
        else:
            vol_regime = "NORMAL"

        return {
            "atr": atr_val,
            "atr_pct": round(atr_pct, 3),
            "bb_width": round(bb_width, 2),
            "is_squeeze": is_squeeze,
            "atr_percentile": round(atr_percentile, 1),
            "regime": vol_regime,
        }

    @classmethod
    def _analyze_derivatives(
        cls,
        funding_rate: float,
        open_interest: float,
        long_short_ratio: float,
    ) -> Dict[str, Any]:
        """Analyze derivatives data (funding, OI, L/S ratio)."""
        # Funding rate interpretation
        fr = funding_rate or 0
        if fr > 0.01:
            funding_bias = "EXTREME_LONG"
        elif fr > 0.005:
            funding_bias = "LONG_HEAVY"
        elif fr < -0.01:
            funding_bias = "EXTREME_SHORT"
        elif fr < -0.005:
            funding_bias = "SHORT_HEAVY"
        else:
            funding_bias = "NEUTRAL"

        # Contrarian signal from extreme funding
        funding_contrarian = None
        if fr > 0.01:
            funding_contrarian = "SHORT"  # Too many longs, fade them
        elif fr < -0.01:
            funding_contrarian = "LONG"   # Too many shorts, fade them

        # L/S ratio interpretation
        ls = long_short_ratio or 0.5
        if ls > 0.65:
            crowd_position = "LONG_CROWDED"
        elif ls < 0.35:
            crowd_position = "SHORT_CROWDED"
        else:
            crowd_position = "BALANCED"

        return {
            "funding_rate": fr,
            "funding_bias": funding_bias,
            "funding_contrarian": funding_contrarian,
            "open_interest": open_interest or 0,
            "long_short_ratio": ls,
            "crowd_position": crowd_position,
        }

    @classmethod
    def _detect_regime(
        cls,
        trend: Dict,
        momentum: Dict,
        volatility: Dict,
    ) -> tuple:
        """Detect overall market regime."""
        trend_dir = trend["direction"]
        trend_str = trend["strength"]
        vol_regime = volatility["regime"]
        rsi = momentum["rsi"]

        # Strong uptrend
        if trend_dir == "BULLISH" and trend_str in ("STRONG", "VERY_STRONG"):
            return MarketRegime.BULL_TREND.value, 85

        # Strong downtrend
        if trend_dir == "BEARISH" and trend_str in ("STRONG", "VERY_STRONG"):
            return MarketRegime.BEAR_TREND.value, 85

        # Crash detection (bearish + high volatility + oversold)
        if trend_dir == "BEARISH" and vol_regime == "HIGH" and rsi < 30:
            return MarketRegime.CRASH.value, 90

        # Recovery (bullish + coming from oversold)
        if trend_dir == "BULLISH" and rsi > 40 and rsi < 60 and vol_regime == "HIGH":
            return MarketRegime.RECOVERY.value, 65

        # High volatility without clear trend
        if vol_regime == "HIGH" and trend_str in ("WEAK", "MODERATE"):
            return MarketRegime.HIGH_VOLATILITY.value, 70

        # Ranging (weak trend, normal volatility)
        if trend_str == "WEAK" and vol_regime in ("NORMAL", "LOW"):
            return MarketRegime.RANGING.value, 75

        # Default
        return MarketRegime.UNKNOWN.value, 50

    @classmethod
    def _calculate_long_score(cls, trend, momentum, volume, derivatives) -> float:
        """Composite LONG opportunity score (0-100)."""
        score = 50  # Start neutral

        # Trend contribution (±25)
        score += trend["score"] * 0.25

        # Momentum contribution (±20)
        score += momentum["score"] * 0.20

        # Volume contribution (±10)
        score += volume["score"] * 0.10

        # Derivatives contribution (±10)
        if derivatives["funding_contrarian"] == "LONG":
            score += 10
        elif derivatives["funding_contrarian"] == "SHORT":
            score -= 5

        if derivatives["crowd_position"] == "SHORT_CROWDED":
            score += 5

        return max(0, min(100, round(score, 1)))

    @classmethod
    def _calculate_short_score(cls, trend, momentum, volume, derivatives) -> float:
        """Composite SHORT opportunity score (0-100)."""
        score = 50

        score -= trend["score"] * 0.25
        score -= momentum["score"] * 0.20
        score -= volume["score"] * 0.10

        if derivatives["funding_contrarian"] == "SHORT":
            score += 10
        elif derivatives["funding_contrarian"] == "LONG":
            score -= 5

        if derivatives["crowd_position"] == "LONG_CROWDED":
            score += 5

        return max(0, min(100, round(score, 1)))

    @classmethod
    def _empty_assessment(cls, symbol: str, reason: str) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "regime": MarketRegime.UNKNOWN.value,
            "regime_confidence": 0,
            "long_score": 0,
            "short_score": 0,
            "has_data": False,
            "error": reason,
        }
