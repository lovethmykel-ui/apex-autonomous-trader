"""
Apex Autonomous Trader — Technical Indicator Engine
=====================================================
Calculates institutional-grade technical indicators on OHLCV data.
Feeds data to the Market Intelligence Engine.
"""

import logging
import warnings
import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import Dict, Any, List, Optional

logger = logging.getLogger("indicator_engine")


class IndicatorEngine:
    """Core technical indicator calculation engine."""

    REQUIRED_COLS = {"open", "high", "low", "close", "volume"}

    @classmethod
    def validate(cls, df: pd.DataFrame) -> bool:
        df.columns = df.columns.str.lower()
        return cls.REQUIRED_COLS.issubset(df.columns)

    @classmethod
    def calculate_all(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate comprehensive indicator suite:
        EMA (9/20/50/200), RSI, StochRSI, MACD, Bollinger Bands,
        VWAP, ATR, ADX, SuperTrend, OBV, Ichimoku, Williams %R, CMF
        """
        if not cls.validate(df):
            raise ValueError("DataFrame must contain OHLCV columns")

        df = df.copy()

        # ── EMAs ──
        for period in [9, 20, 50, 200]:
            col = f"EMA_{period}"
            if len(df) >= period:
                df[col] = ta.ema(df["close"], length=period)

        # ── RSI ──
        df["RSI_14"] = ta.rsi(df["close"], length=14)

        # ── Stochastic RSI ──
        stochrsi = ta.stochrsi(df["close"], length=14)
        if stochrsi is not None:
            df = pd.concat([df, stochrsi], axis=1)

        # ── MACD ──
        macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
        if macd is not None:
            df = pd.concat([df, macd], axis=1)

        # ── Bollinger Bands ──
        bbands = ta.bbands(df["close"], length=20, std=2)
        if bbands is not None:
            df = pd.concat([df, bbands], axis=1)

        # ── VWAP ──
        try:
            vwap = ta.vwap(high=df["high"], low=df["low"], close=df["close"], volume=df["volume"])
            if vwap is not None:
                df["VWAP"] = vwap
        except Exception:
            typical = (df["high"] + df["low"] + df["close"]) / 3
            df["VWAP"] = (typical * df["volume"]).cumsum() / df["volume"].cumsum()

        # ── ATR ──
        df["ATR_14"] = ta.atr(high=df["high"], low=df["low"], close=df["close"], length=14)

        # ── ADX ──
        adx = ta.adx(high=df["high"], low=df["low"], close=df["close"], length=14)
        if adx is not None:
            df = pd.concat([df, adx], axis=1)

        # ── SuperTrend ──
        supertrend = ta.supertrend(high=df["high"], low=df["low"], close=df["close"], length=7, multiplier=3.0)
        if supertrend is not None:
            df = pd.concat([df, supertrend], axis=1)

        # ── OBV ──
        df["OBV"] = ta.obv(close=df["close"], volume=df["volume"])

        # ── Williams %R ──
        df["WILLR_14"] = ta.willr(high=df["high"], low=df["low"], close=df["close"], length=14)

        # ── CMF (Chaikin Money Flow) ──
        cmf = ta.cmf(high=df["high"], low=df["low"], close=df["close"], volume=df["volume"], length=20)
        if cmf is not None:
            df["CMF_20"] = cmf

        # ── Ichimoku ──
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                ichimoku_df, _ = ta.ichimoku(
                    high=df["high"], low=df["low"], close=df["close"],
                    tenkan=9, kijun=26, senkou=52
                )
                if ichimoku_df is not None:
                    df = pd.concat([df, ichimoku_df], axis=1)
            except Exception:
                pass

        # ── Rate of Change ──
        df["ROC_10"] = ta.roc(df["close"], length=10)
        df["ROC_20"] = ta.roc(df["close"], length=20)

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
