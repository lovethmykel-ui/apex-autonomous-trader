"""
Apex Autonomous Trader — Database Models
==========================================
Every table here serves the agent's mission:
  Survive. Learn. Evolve. Compound.

Tables are organized by the 6-layer architecture:
  - Core: Owner, ExchangeAccount
  - Layer 3 (Execution): Position, Order, Trade, Balance
  - Layer 4 (Treasury): TreasurySnapshot, Generation
  - Layer 5 (Memory): TradeMemory, MarketSnapshot
  - Layer 6 (Evolution): StrategyPerformance, EvolutionParams
  - System: SystemLog, Notification
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, JSON, Text, Enum, BigInteger, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from .base import Base


# ═══════════════════════════════════════════════════════════
#  ENUMS
# ═══════════════════════════════════════════════════════════

class GenerationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SURVIVAL = "SURVIVAL"      # Weekly drawdown breached
    DYING = "DYING"            # Monthly drawdown breached
    DEAD = "DEAD"              # Treasury below death threshold
    RETIRED = "RETIRED"        # Manually killed by owner


class TradeSide(str, enum.Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class OrderType(str, enum.Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    TRAILING_STOP = "TRAILING_STOP"


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class MarketRegime(str, enum.Enum):
    BULL_TREND = "BULL_TREND"
    BEAR_TREND = "BEAR_TREND"
    RANGING = "RANGING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    CRASH = "CRASH"
    RECOVERY = "RECOVERY"
    UNKNOWN = "UNKNOWN"


class TradingMode(str, enum.Enum):
    PAPER = "PAPER"
    LIVE = "LIVE"


# ═══════════════════════════════════════════════════════════
#  CORE — Owner & Exchange
# ═══════════════════════════════════════════════════════════

class Owner(Base):
    """The creator of the agent. Only one owner exists."""
    __tablename__ = "owners"

    id = Column(Integer, primary_key=True, index=True)
    telegram_chat_id = Column(String, unique=True, nullable=False)
    trading_mode = Column(String, default=TradingMode.PAPER.value)
    is_trading_paused = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    exchange_accounts = relationship("ExchangeAccount", back_populates="owner")


class ExchangeAccount(Base):
    """Bybit exchange credentials."""
    __tablename__ = "exchange_accounts"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False)
    exchange_name = Column(String, default="bybit")
    api_key = Column(String, nullable=False)
    api_secret = Column(String, nullable=False)
    is_testnet = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("Owner", back_populates="exchange_accounts")
    balances = relationship("Balance", back_populates="account", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="account", cascade="all, delete-orphan")


# ═══════════════════════════════════════════════════════════
#  LAYER 3 — Execution (Positions, Orders, Trades, Balances)
# ═══════════════════════════════════════════════════════════

class Balance(Base):
    """Current exchange balance per asset."""
    __tablename__ = "balances"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("exchange_accounts.id"), nullable=False)
    asset = Column(String, nullable=False, default="USDT")
    free = Column(Float, default=0.0)
    locked = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    account = relationship("ExchangeAccount", back_populates="balances")


class Position(Base):
    """Currently open positions on the exchange."""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("exchange_accounts.id"), nullable=False)
    generation_id = Column(Integer, ForeignKey("generations.id"), nullable=True)
    symbol = Column(String, nullable=False, index=True)
    side = Column(String, nullable=False)  # LONG or SHORT
    size = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, default=0.0)
    leverage = Column(Integer, default=5)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    trailing_stop = Column(Float, nullable=True)
    unrealized_pnl = Column(Float, default=0.0)
    strategy_used = Column(String, nullable=True)
    confidence_at_entry = Column(Float, default=0.0)
    opened_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    account = relationship("ExchangeAccount", back_populates="positions")
    generation = relationship("Generation", back_populates="positions")


class Order(Base):
    """Order records — every order placed on the exchange."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    generation_id = Column(Integer, ForeignKey("generations.id"), nullable=True)
    symbol = Column(String, nullable=False, index=True)
    order_type = Column(String, nullable=False)
    side = Column(String, nullable=False)
    price = Column(Float, nullable=True)
    amount = Column(Float, nullable=False)
    filled_amount = Column(Float, default=0.0)
    status = Column(String, nullable=False, default=OrderStatus.PENDING.value)
    bybit_order_id = Column(String, nullable=True)
    slippage = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    filled_at = Column(DateTime, nullable=True)

    generation = relationship("Generation", back_populates="orders")


class Trade(Base):
    """Executed trade fills."""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    generation_id = Column(Integer, ForeignKey("generations.id"), nullable=True)
    symbol = Column(String, nullable=False, index=True)
    side = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    fee = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    generation = relationship("Generation", back_populates="trades")


# ═══════════════════════════════════════════════════════════
#  LAYER 4 — Treasury (Generation, Snapshots)
# ═══════════════════════════════════════════════════════════

class Generation(Base):
    """
    Each generation is a lifecycle of the trading agent.
    When the treasury falls below the death threshold, the generation dies
    and a new one is born — inheriting all knowledge.
    """
    __tablename__ = "generations"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, nullable=False, unique=True)
    status = Column(String, default=GenerationStatus.ACTIVE.value)

    # Treasury state
    initial_treasury = Column(Float, nullable=False)
    current_treasury = Column(Float, nullable=False)
    peak_treasury = Column(Float, nullable=False)
    death_threshold = Column(Float, nullable=False)  # Absolute dollar amount

    # Performance
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    total_pnl = Column(Float, default=0.0)
    best_trade_pnl = Column(Float, default=0.0)
    worst_trade_pnl = Column(Float, default=0.0)
    max_drawdown_pct = Column(Float, default=0.0)

    # Lifecycle
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    died_at = Column(DateTime, nullable=True)
    death_reason = Column(String, nullable=True)

    # Relationships
    positions = relationship("Position", back_populates="generation")
    orders = relationship("Order", back_populates="generation")
    trades = relationship("Trade", back_populates="generation")
    trade_memories = relationship("TradeMemory", back_populates="generation")
    treasury_snapshots = relationship("TreasurySnapshot", back_populates="generation")
    strategy_performances = relationship("StrategyPerformance", back_populates="generation")
    evolution_params = relationship("EvolutionParams", back_populates="generation")

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100

    @property
    def is_alive(self) -> bool:
        return self.status in (
            GenerationStatus.ACTIVE.value,
            GenerationStatus.SURVIVAL.value,
        )


class TreasurySnapshot(Base):
    """
    Periodic snapshots of treasury state.
    Taken every trading cycle to track equity curve and drawdowns.
    """
    __tablename__ = "treasury_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    generation_id = Column(Integer, ForeignKey("generations.id"), nullable=False)
    balance = Column(Float, nullable=False)
    daily_pnl = Column(Float, default=0.0)
    weekly_pnl = Column(Float, default=0.0)
    monthly_pnl = Column(Float, default=0.0)
    daily_drawdown_pct = Column(Float, default=0.0)
    weekly_drawdown_pct = Column(Float, default=0.0)
    monthly_drawdown_pct = Column(Float, default=0.0)
    open_positions_count = Column(Integer, default=0)
    total_exposure = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    generation = relationship("Generation", back_populates="treasury_snapshots")


# ═══════════════════════════════════════════════════════════
#  LAYER 5 — Memory (Trade Memory, Market Snapshots)
# ═══════════════════════════════════════════════════════════

class TradeMemory(Base):
    """
    Permanent memory of every trade decision.
    No deletion. The agent remembers everything.
    Each trade receives a composite score (0-100).
    """
    __tablename__ = "trade_memories"

    id = Column(Integer, primary_key=True, index=True)
    generation_id = Column(Integer, ForeignKey("generations.id"), nullable=False)

    # Trade details
    symbol = Column(String, nullable=False, index=True)
    side = Column(String, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    size = Column(Float, nullable=False)
    leverage = Column(Integer, default=1)
    pnl = Column(Float, default=0.0)
    pnl_pct = Column(Float, default=0.0)
    fee_paid = Column(Float, default=0.0)
    slippage = Column(Float, default=0.0)
    duration_seconds = Column(Integer, default=0)

    # Scoring (0 to 100 each)
    entry_score = Column(Float, default=0.0)   # How close to optimal entry
    exit_score = Column(Float, default=0.0)    # Did we capture the move
    risk_score = Column(Float, default=0.0)    # Was risk properly managed
    timing_score = Column(Float, default=0.0)  # Right time in market cycle
    outcome_score = Column(Float, default=0.0) # Final P&L result
    overall_score = Column(Float, default=0.0) # Composite (0-100)

    # Context
    strategy_used = Column(String, nullable=True)
    market_regime = Column(String, nullable=True)
    confidence_at_entry = Column(Float, default=0.0)
    indicators_snapshot = Column(JSON, nullable=True)
    entry_reason = Column(Text, nullable=True)
    exit_reason = Column(Text, nullable=True)
    lessons_learned = Column(Text, nullable=True)

    # Timestamps
    opened_at = Column(DateTime, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    generation = relationship("Generation", back_populates="trade_memories")


class MarketSnapshot(Base):
    """
    Point-in-time capture of market conditions.
    Used for pattern recognition and regime analysis.
    """
    __tablename__ = "market_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    price = Column(Float, nullable=False)
    volume_24h = Column(Float, default=0.0)
    funding_rate = Column(Float, default=0.0)
    open_interest = Column(Float, default=0.0)
    long_short_ratio = Column(Float, default=0.0)
    regime = Column(String, default=MarketRegime.UNKNOWN.value)
    volatility = Column(Float, default=0.0)
    indicators = Column(JSON, nullable=True)  # Full indicator state
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


# ═══════════════════════════════════════════════════════════
#  LAYER 6 — Evolution (Strategy Performance, Parameters)
# ═══════════════════════════════════════════════════════════

class StrategyPerformance(Base):
    """
    Tracks how each strategy performs across generations.
    The evolution engine uses this to weight future decisions.
    """
    __tablename__ = "strategy_performances"

    id = Column(Integer, primary_key=True, index=True)
    generation_id = Column(Integer, ForeignKey("generations.id"), nullable=False)
    strategy_name = Column(String, nullable=False, index=True)

    # Stats
    total_trades = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    total_pnl = Column(Float, default=0.0)
    avg_pnl = Column(Float, default=0.0)
    best_trade_pnl = Column(Float, default=0.0)
    worst_trade_pnl = Column(Float, default=0.0)
    avg_duration_seconds = Column(Integer, default=0)
    sharpe_ratio = Column(Float, default=0.0)
    sortino_ratio = Column(Float, default=0.0)
    max_drawdown_pct = Column(Float, default=0.0)

    # Fitness
    fitness_score = Column(Float, default=0.0)  # Overall strategy fitness

    # Best market conditions
    best_regime = Column(String, nullable=True)
    worst_regime = Column(String, nullable=True)

    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    generation = relationship("Generation", back_populates="strategy_performances")

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return (self.wins / self.total_trades) * 100


class EvolutionParams(Base):
    """
    Strategy parameters that evolve between generations.
    Each new generation inherits optimized params from the last.
    """
    __tablename__ = "evolution_params"

    id = Column(Integer, primary_key=True, index=True)
    generation_id = Column(Integer, ForeignKey("generations.id"), nullable=False)
    strategy_name = Column(String, nullable=False, index=True)
    parameters = Column(JSON, nullable=False)  # Strategy-specific parameters
    fitness_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    generation = relationship("Generation", back_populates="evolution_params")


# ═══════════════════════════════════════════════════════════
#  SYSTEM — Logs, Notifications, Market Data Cache
# ═══════════════════════════════════════════════════════════

class SystemLog(Base):
    """System-level logging stored in DB for Telegram diagnostics."""
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String, nullable=False)  # INFO, WARNING, ERROR, CRITICAL
    component = Column(String, nullable=False, index=True)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class Notification(Base):
    """Notification queue for Telegram messages."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    sent_at = Column(DateTime, nullable=True)


# ═══════════════════════════════════════════════════════════
#  INDEXES for performance
# ═══════════════════════════════════════════════════════════

Index("ix_trade_memories_gen_symbol", TradeMemory.generation_id, TradeMemory.symbol)
Index("ix_trade_memories_strategy", TradeMemory.strategy_used)
Index("ix_treasury_snapshots_gen_ts", TreasurySnapshot.generation_id, TreasurySnapshot.timestamp)
Index("ix_market_snapshots_symbol_ts", MarketSnapshot.symbol, MarketSnapshot.timestamp)
Index("ix_strategy_perf_gen_name", StrategyPerformance.generation_id, StrategyPerformance.strategy_name)
Index("ix_system_logs_level_ts", SystemLog.level, SystemLog.created_at)
