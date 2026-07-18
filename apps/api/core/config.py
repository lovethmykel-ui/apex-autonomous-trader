"""
Apex Autonomous Trader — Core Configuration
=============================================
Central configuration loaded from environment variables.
Every dollar in the treasury represents life.
"""

import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # --- Identity ---
    PROJECT_NAME: str = "Apex Autonomous Trader"
    VERSION: str = "1.0.0"

    # --- Database ---
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://apex_user:apex_password@localhost:5432/apex_trader"
    )

    # --- Redis ---
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # --- Security ---
    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE_THIS_IN_PRODUCTION")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # --- Bybit Exchange ---
    BYBIT_API_KEY: str = os.getenv("BYBIT_API_KEY", "")
    BYBIT_API_SECRET: str = os.getenv("BYBIT_API_SECRET", "")
    BYBIT_TESTNET: bool = os.getenv("BYBIT_TESTNET", "true").lower() == "true"

    # --- Treasury & Risk Management ---
    MAX_POSITION_SIZE_PCT: float = float(os.getenv("MAX_POSITION_SIZE_PCT", "2.0"))
    MAX_DAILY_DRAWDOWN_PCT: float = float(os.getenv("MAX_DAILY_DRAWDOWN_PCT", "5.0"))
    MAX_WEEKLY_DRAWDOWN_PCT: float = float(os.getenv("MAX_WEEKLY_DRAWDOWN_PCT", "15.0"))
    MAX_MONTHLY_DRAWDOWN_PCT: float = float(os.getenv("MAX_MONTHLY_DRAWDOWN_PCT", "25.0"))
    DEFAULT_LEVERAGE: int = int(os.getenv("DEFAULT_LEVERAGE", "5"))
    MAX_LEVERAGE: int = int(os.getenv("MAX_LEVERAGE", "10"))
    EMERGENCY_LEVERAGE_CAP: int = int(os.getenv("EMERGENCY_LEVERAGE_CAP", "20"))
    GENERATION_DEATH_THRESHOLD_PCT: float = float(
        os.getenv("GENERATION_DEATH_THRESHOLD_PCT", "40.0")
    )

    # --- Trading Engine ---
    TRADING_INTERVAL_SECONDS: int = int(os.getenv("TRADING_INTERVAL_SECONDS", "60"))
    TOP_PAIRS_TO_SCAN: int = int(os.getenv("TOP_PAIRS_TO_SCAN", "20"))
    MIN_24H_VOLUME_USDT: float = float(os.getenv("MIN_24H_VOLUME_USDT", "5000000"))
    SIGNAL_CONVICTION_THRESHOLD: float = float(
        os.getenv("SIGNAL_CONVICTION_THRESHOLD", "0.70")
    )

    # --- Telegram ---
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_AUTHORIZED_CHAT_ID: str = os.getenv("TELEGRAM_AUTHORIZED_CHAT_ID", "")

    # --- Optional: AI Advisory ---
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
