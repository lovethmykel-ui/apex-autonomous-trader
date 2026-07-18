"""
Apex Autonomous Trader — Prometheus Metrics
=============================================
Exposes core telemetry data for Grafana dashboards.
"""

from prometheus_client import Counter, Gauge, Histogram

# --- TREASURY & PERFORMANCE ---
AAT_TREASURY_BALANCE = Gauge(
    "aat_treasury_balance_usdt", 
    "Current active generation treasury balance in USDT"
)
AAT_DRAWDOWN_PCT = Gauge(
    "aat_drawdown_percent", 
    "Current active generation drawdown percentage"
)
AAT_WIN_RATE = Gauge(
    "aat_win_rate_percent", 
    "Win rate percentage for the active generation"
)
AAT_TOTAL_PNL = Gauge(
    "aat_total_pnl_usdt", 
    "Total P&L in USDT for the active generation"
)

# --- TRADING ACTIVITY ---
AAT_OPEN_POSITIONS = Gauge(
    "aat_open_positions_count", 
    "Number of currently open trading positions"
)
AAT_TRADES_EXECUTED = Counter(
    "aat_trades_executed_total", 
    "Total number of trades executed",
    ["side", "strategy"]
)
AAT_TRADE_PNL_DISTRIBUTION = Histogram(
    "aat_trade_pnl_distribution_pct", 
    "Distribution of P&L percentages for closed trades",
    buckets=[-10, -5, -2, -1, 0, 1, 2, 5, 10, 20]
)

# --- SYSTEM & EVOLUTION ---
AAT_ACTIVE_GENERATION = Gauge(
    "aat_active_generation_number", 
    "The generation number currently running"
)
AAT_MARKET_REGIME = Gauge(
    "aat_market_regime", 
    "Current market regime detected (encoded as int: 1=Bull, -1=Bear, 0=Range, etc.)"
)
AAT_SCAN_LATENCY = Histogram(
    "aat_scan_latency_seconds", 
    "Time taken for a full market scan loop"
)

def update_metrics_from_generation(gen_summary: dict, open_positions_count: int, market_regime_encoded: int):
    """Update all Prometheus Gauges from the current generation stats."""
    AAT_TREASURY_BALANCE.set(gen_summary.get("current_treasury", 0))
    AAT_DRAWDOWN_PCT.set(gen_summary.get("max_drawdown_pct", 0))
    AAT_WIN_RATE.set(gen_summary.get("win_rate", 0))
    AAT_TOTAL_PNL.set(gen_summary.get("total_pnl", 0))
    
    AAT_ACTIVE_GENERATION.set(gen_summary.get("generation", 0))
    AAT_OPEN_POSITIONS.set(open_positions_count)
    AAT_MARKET_REGIME.set(market_regime_encoded)
