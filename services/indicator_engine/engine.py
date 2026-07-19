"""
Apex Autonomous Trader — Technical Indicator Engine
=====================================================
Calculates institutional-grade technical indicators on OHLCV data.
Feeds data to the Market Intelligence Engine.

Uses pure numpy/pandas implementations — no pandas_ta/numba dependency.
"""

import logging
import warnings
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

logger = logging.getLogger("indicator_engine")


class IndicatorEngine:
    """Core technical indicator calculation engine (pure numpy/pandas)."""

    REQUIRED_COLS = {"open", "high", "low", "close", "volume"}

    @classmethod
    def validate(cls, df: pd.DataFrame) -> bool:
        df.columns = df.columns.str.lower()
        return cls.REQUIRED_COLS.issubset(df.columns)

    # ═══════════════════════════════════════════════════════════
    #  PURE INDICATOR IMPLEMENTATIONS
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _ema(series: pd.Series, length: int) -> pd.Series:
        return series.ewm(span=length, adjust=False).mean()

    @staticmethod
    def _sma(series: pd.Series, length: int) -> pd.Series:
        return series.rolling(window=length).mean()

    @staticmethod
    def _rsi(close: pd.Series, length: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1.0 / length, min_periods=length, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / length, min_periods=length, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return 100.0 - (100.0 / (1.0 + rs))

    @staticmethod
    def _stochrsi(close: pd.Series, length: int = 14, rsi_length: int = 14, k: int = 3, d: int = 3) -> pd.DataFrame:
        rsi = IndicatorEngine._rsi(close, rsi_length)
        rsi_min = rsi.rolling(window=length).min()
        rsi_max = rsi.rolling(window=length).max()
        stochrsi = (rsi - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan)
        stochrsi_k = stochrsi.rolling(window=k).mean() * 100
        stochrsi_d = stochrsi_k.rolling(window=d).mean()
        return pd.DataFrame({
            f"STOCHRSIk_{length}_{rsi_length}_{k}_{d}": stochrsi_k,
            f"STOCHRSId_{length}_{rsi_length}_{k}_{d}": stochrsi_d,
        })

    @staticmethod
    def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return pd.DataFrame({
            f"MACD_{fast}_{slow}_{signal}": macd_line,
            f"MACDs_{fast}_{slow}_{signal}": signal_line,
            f"MACDh_{fast}_{slow}_{signal}": histogram,
        })

    @staticmethod
    def _bbands(close: pd.Series, length: int = 20, std: float = 2.0) -> pd.DataFrame:
        mid = close.rolling(window=length).mean()
        std_dev = close.rolling(window=length).std()
        upper = mid + std * std_dev
        lower = mid - std * std_dev
        bandwidth = (upper - lower) / mid
        pctb = (close - lower) / (upper - lower).replace(0, np.nan)
        return pd.DataFrame({
            f"BBL_{length}_{std}": lower,
            f"BBM_{length}_{std}": mid,
            f"BBU_{length}_{std}": upper,
            f"BBB_{length}_{std}": bandwidth,
            f"BBP_{length}_{std}": pctb,
        })

    @staticmethod
    def _atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        return tr.ewm(alpha=1.0 / length, min_periods=length, adjust=False).mean()

    @staticmethod
    def _adx(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.DataFrame:
        prev_high = high.shift(1)
        prev_low = low.shift(1)
        plus_dm = (high - prev_high).clip(lower=0)
        minus_dm = (prev_low - low).clip(lower=0)
        # Zero out where opposite is larger
        plus_dm[minus_dm > plus_dm] = 0
        minus_dm[plus_dm > minus_dm] = 0
        atr = IndicatorEngine._atr(high, low, close, length)
        plus_di = 100 * (plus_dm.ewm(alpha=1.0 / length, min_periods=length, adjust=False).mean() / atr.replace(0, np.nan))
        minus_di = 100 * (minus_dm.ewm(alpha=1.0 / length, min_periods=length, adjust=False).mean() / atr.replace(0, np.nan))
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
        adx = dx.ewm(alpha=1.0 / length, min_periods=length, adjust=False).mean()
        return pd.DataFrame({
            f"ADX_{length}": adx,
            f"DMP_{length}": plus_di,
            f"DMN_{length}": minus_di,
        })

    @staticmethod
    def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        sign = np.sign(close.diff()).fillna(0)
        return (sign * volume).cumsum()

    @staticmethod
    def _willr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
        highest = high.rolling(window=length).max()
        lowest = low.rolling(window=length).min()
        return -100 * (highest - close) / (highest - lowest).replace(0, np.nan)

    @staticmethod
    def _cmf(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, length: int = 20) -> pd.Series:
        mfv = ((close - low) - (high - close)) / (high - low).replace(0, np.nan) * volume
        return mfv.rolling(window=length).sum() / volume.rolling(window=length).sum().replace(0, np.nan)

    @staticmethod
    def _roc(close: pd.Series, length: int = 10) -> pd.Series:
        prev = close.shift(length)
        return 100 * (close - prev) / prev.replace(0, np.nan)

    @staticmethod
    def _supertrend(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 7, multiplier: float = 3.0) -> pd.DataFrame:
        atr = IndicatorEngine._atr(high, low, close, length)
        hl2 = (high + low) / 2
        upper_band = hl2 + multiplier * atr
        lower_band = hl2 - multiplier * atr

        supertrend = pd.Series(np.nan, index=close.index)
        direction = pd.Series(1, index=close.index)

        for i in range(1, len(close)):
            if close.iloc[i] > upper_band.iloc[i - 1]:
                direction.iloc[i] = 1
            elif close.iloc[i] < lower_band.iloc[i - 1]:
                direction.iloc[i] = -1
            else:
                direction.iloc[i] = direction.iloc[i - 1]

            if direction.iloc[i] == 1:
                lower_band.iloc[i] = max(lower_band.iloc[i], lower_band.iloc[i - 1]) if direction.iloc[i - 1] == 1 else lower_band.iloc[i]
                supertrend.iloc[i] = lower_band.iloc[i]
            else:
                upper_band.iloc[i] = min(upper_band.iloc[i], upper_band.iloc[i - 1]) if direction.iloc[i - 1] == -1 else upper_band.iloc[i]
                supertrend.iloc[i] = upper_band.iloc[i]

        return pd.DataFrame({
            f"SUPERT_{length}_{multiplier}": supertrend,
            f"SUPERTd_{length}_{multiplier}": direction,
        })

    # ═══════════════════════════════════════════════════════════
    #  MAIN CALCULATION
    # ═══════════════════════════════════════════════════════════

    @classmethod
    def calculate_all(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate comprehensive indicator suite:
        EMA (9/20/50/200), RSI, StochRSI, MACD, Bollinger Bands,
        VWAP, ATR, ADX, SuperTrend, OBV, Williams %R, CMF, ROC
        """
        if not cls.validate(df):
            raise ValueError("DataFrame must contain OHLCV columns")

        df = df.copy()

        # ── EMAs ──
        for period in [9, 20, 50, 200]:
            if len(df) >= period:
                df[f"EMA_{period}"] = cls._ema(df["close"], period)

        # ── RSI ──
        df["RSI_14"] = cls._rsi(df["close"], 14)

        # ── Stochastic RSI ──
        stochrsi = cls._stochrsi(df["close"], 14)
        df = pd.concat([df, stochrsi], axis=1)

        # ── MACD ──
        macd = cls._macd(df["close"], 12, 26, 9)
        df = pd.concat([df, macd], axis=1)

        # ── Bollinger Bands ──
        bbands = cls._bbands(df["close"], 20, 2)
        df = pd.concat([df, bbands], axis=1)

        # ── VWAP ──
        typical = (df["high"] + df["low"] + df["close"]) / 3
        df["VWAP"] = (typical * df["volume"]).cumsum() / df["volume"].cumsum().replace(0, np.nan)

        # ── ATR ──
        df["ATR_14"] = cls._atr(df["high"], df["low"], df["close"], 14)

        # ── ADX ──
        adx = cls._adx(df["high"], df["low"], df["close"], 14)
        df = pd.concat([df, adx], axis=1)

        # ── SuperTrend ──
        try:
            supertrend = cls._supertrend(df["high"], df["low"], df["close"], 7, 3.0)
            df = pd.concat([df, supertrend], axis=1)
        except Exception as e:
            logger.warning(f"SuperTrend calculation skipped: {e}")

        # ── OBV ──
        df["OBV"] = cls._obv(df["close"], df["volume"])

        # ── Williams %R ──
        df["WILLR_14"] = cls._willr(df["high"], df["low"], df["close"], 14)

        # ── CMF ──
        df["CMF_20"] = cls._cmf(df["high"], df["low"], df["close"], df["volume"], 20)

        # ── Rate of Change ──
        df["ROC_10"] = cls._roc(df["close"], 10)
        df["ROC_20"] = cls._roc(df["close"], 20)

        return df

    @classmethod
    def get_latest(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """Get most recent indicator values as a clean dictionary."""
        if "RSI_14" not in df.columns:
            df = cls.calculate_all(df)

        latest = df.iloc[-1].to_dict()
        return {k: (None if pd.isna(v) else v) for k, v in latest.items()}

    @classmethod
    def candles_to_dataframe(cls, candles: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert raw candle dicts to a pandas DataFrame."""
        df = pd.DataFrame(candles)
        df.columns = df.columns.str.lower()
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
