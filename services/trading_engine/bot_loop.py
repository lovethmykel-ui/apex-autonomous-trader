"""
Apex Autonomous Trader — Autonomous Trading Loop
==================================================
The core autonomous trading cycle.
This IS the trader. It doesn't assist — it acts.

Every cycle:
  1. Check treasury health
  2. Scan markets
  3. Run Market Intelligence on top candidates
  4. Run Decision Engine
  5. Execute trades if conviction met
  6. Record to Memory
  7. Update Evolution stats
  8. Take treasury snapshot
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from apps.api.core.config import settings
from apps.api.core import bybit as bybit_client
from apps.api.core.database import SessionLocal
from shared.db.models import (
    Owner, ExchangeAccount, Balance, Position,
    Generation, GenerationStatus, TradingMode
)
from services.treasury.manager import TreasuryManager
from services.market_intelligence.engine import MarketIntelligence
from services.decision_engine.engine import DecisionEngine
from services.risk_engine.calculator import RiskCalculator
from services.memory.engine import MemoryEngine
from services.evolution.engine import EvolutionEngine

logger = logging.getLogger("bot_loop")


# ═══════════════════════════════════════════════════════════
#  GLOBAL STATE
# ═══════════════════════════════════════════════════════════

_bot_running: bool = False
_bot_task: Optional[asyncio.Task] = None
_bot_status: Dict[str, Any] = {
    "running": False,
    "last_scan": None,
    "last_trade": None,
    "last_signal": None,
    "pairs_scanned": 0,
    "trades_today": 0,
    "cycle_count": 0,
    "errors": [],
}

_last_daily_report = None
_decision_engine = DecisionEngine()


# ═══════════════════════════════════════════════════════════
#  NOTIFICATION HELPER
# ═══════════════════════════════════════════════════════════

async def _notify(text: str):
    """Send notification via Telegram."""
    try:
        from services.telegram_bot.service import emit_notification
        await emit_notification(text)
    except Exception as e:
        logger.error(f"Notification failed: {e}")


# ═══════════════════════════════════════════════════════════
#  PUBLIC CONTROL API
# ═══════════════════════════════════════════════════════════

def get_status() -> Dict[str, Any]:
    return dict(_bot_status)


def start_bot() -> bool:
    global _bot_running, _bot_task, _bot_status
    if _bot_running:
        return False
    _bot_running = True
    _bot_status["running"] = True
    _bot_status["errors"] = []
    _bot_task = asyncio.create_task(_trading_loop())
    logger.info("🤖 Apex Autonomous Trader STARTED")
    asyncio.create_task(_notify(
        "🟢 <b>Apex Autonomous Trader Online</b>\n"
        "The agent is now scanning markets and executing trades autonomously."
    ))
    return True


def stop_bot() -> bool:
    global _bot_running, _bot_task, _bot_status
    _bot_running = False
    _bot_status["running"] = False
    if _bot_task and not _bot_task.done():
        _bot_task.cancel()
        logger.info("🛑 Apex Autonomous Trader STOPPED")
        asyncio.create_task(_notify(
            "🔴 <b>Apex Autonomous Trader Paused</b>\n"
            "Trading loops suspended. Existing positions remain open."
        ))
    return True


# ═══════════════════════════════════════════════════════════
#  CORE TRADING LOOP
# ═══════════════════════════════════════════════════════════

async def _trading_loop():
    global _bot_status

    logger.info(
        f"Trading loop active | Interval: {settings.TRADING_INTERVAL_SECONDS}s | "
        f"Max Risk: {settings.MAX_POSITION_SIZE_PCT}% | Max Leverage: {settings.MAX_LEVERAGE}x"
    )

    while _bot_running:
        try:
            await _run_cycle()

            # Daily report at midnight (WAT / UTC+1)
            global _last_daily_report
            wat = timezone(timedelta(hours=1))
            now = datetime.now(wat)
            if now.hour == 0 and _last_daily_report != now.date():
                await _send_daily_report()
                _last_daily_report = now.date()
                _bot_status["trades_today"] = 0

        except asyncio.CancelledError:
            logger.info("Trading loop cancelled")
            break
        except Exception as e:
            err = f"Cycle error: {e}"
            logger.error(err, exc_info=True)
            _bot_status["errors"] = (_bot_status.get("errors", []) + [err])[-10:]
            await _notify(
                f"⚠️ <b>System Error</b>\n"
                f"<code>{str(e)[:200]}</code>"
            )

        await asyncio.sleep(settings.TRADING_INTERVAL_SECONDS)


async def _run_cycle():
    """Single autonomous trading cycle."""
    global _bot_status
    _bot_status["cycle_count"] = _bot_status.get("cycle_count", 0) + 1

    db = SessionLocal()
    try:
        # ── 1. Get owner and account ──
        owner = db.query(Owner).first()
        if not owner:
            logger.warning("No owner configured — bot idle")
            return

        if owner.is_trading_paused:
            return

        account = db.query(ExchangeAccount).filter(
            ExchangeAccount.owner_id == owner.id,
            ExchangeAccount.is_active == True,
        ).first()

        if not account:
            logger.warning("No active exchange account — bot idle")
            return

        # ── 2. Get or create active generation ──
        generation = TreasuryManager.get_active_generation(db)

        if not generation:
            # First run or all generations dead — create one
            if owner.trading_mode == TradingMode.PAPER.value:
                treasury = _get_paper_balance(db, account)
            else:
                treasury = _get_live_balance(account)

            if treasury < 1:
                logger.warning(f"Insufficient treasury (${treasury:.2f}) — cannot spawn generation")
                return

            generation = TreasuryManager.create_generation(db, treasury)
            EvolutionEngine.initialize_generation(db, generation)
            await _notify(
                f"🧬 <b>Generation G-{generation.number:02d} Born</b>\n"
                f"Treasury: <code>${treasury:,.2f}</code>\n"
                f"Death Threshold: <code>${generation.death_threshold:,.2f}</code>"
            )

        # ── 3. Update treasury state ──
        if owner.trading_mode == TradingMode.PAPER.value:
            current_balance = _get_paper_balance(db, account)
        else:
            current_balance = _get_live_balance(account)

        treasury_status = TreasuryManager.update_treasury(db, generation, current_balance)

        # Send alerts
        for alert in treasury_status.get("alerts", []):
            severity_emoji = {"CRITICAL": "🚨", "HIGH": "⚠️", "LOW": "ℹ️"}.get(alert["severity"], "📢")
            await _notify(f"{severity_emoji} <b>{alert['type']}</b>\n{alert['message']}")

        # Check if generation died
        if treasury_status["status"] == "DEAD":
            await _notify(
                f"💀 <b>Generation G-{generation.number:02d} DEAD</b>\n"
                f"Treasury fell to <code>${current_balance:,.2f}</code>\n"
                f"Reason: {generation.death_reason}\n\n"
                f"Use /spawn to create the next generation."
            )
            return

        # Can we trade?
        if not treasury_status["can_trade"]:
            logger.info(f"Trading halted: {treasury_status['status']}")
            return

        # ── 4. Scan market ──
        loop = asyncio.get_event_loop()
        top_pairs = await loop.run_in_executor(
            None,
            bybit_client.scan_market,
            settings.TOP_PAIRS_TO_SCAN,
            settings.MIN_24H_VOLUME_USDT,
        )

        _bot_status["pairs_scanned"] = len(top_pairs)
        _bot_status["last_scan"] = datetime.now(timezone.utc).isoformat()

        if not top_pairs:
            logger.warning("Market scan returned no pairs")
            return

        # ── 5. Get strategy weights from evolution ──
        weights = EvolutionEngine.get_strategy_weights(db, generation.id)
        _decision_engine.strategy_weights = weights

        # ── 6. Analyze and decide on each candidate ──
        max_alloc, max_lev = TreasuryManager.calculate_max_trade_allocation(generation)
        best_decision = None

        for pair in top_pairs[:10]:
            symbol = pair["symbol"]

            # Skip if already have position
            existing = db.query(Position).filter(
                Position.generation_id == generation.id,
                Position.symbol == symbol,
            ).first()
            if existing:
                continue

            # Fetch candles
            candles = await loop.run_in_executor(
                None, bybit_client.get_candles, symbol, "5", 200
            )
            if len(candles) < 30:
                continue

            # Get derivatives data
            funding = await loop.run_in_executor(None, bybit_client.get_funding_rate, symbol)
            oi = await loop.run_in_executor(None, bybit_client.get_open_interest, symbol)

            # Run Market Intelligence
            assessment = MarketIntelligence.analyze(
                candles_5m=candles,
                funding_rate=funding.get("funding_rate", 0) if funding else 0,
                open_interest=oi.get("open_interest", 0) if oi else 0,
                long_short_ratio=pair.get("long_short_ratio", 0.5),
                symbol=symbol,
            )

            if not assessment.get("has_data"):
                continue

            # Run Decision Engine
            decision = _decision_engine.decide(
                market_assessment=assessment,
                treasury_balance=current_balance,
                max_leverage=max_lev,
                generation_status=generation.status,
            )

            _bot_status["last_signal"] = {
                "symbol": symbol,
                "side": decision.side,
                "confidence": decision.confidence,
                "strategy": decision.strategy_used,
                "regime": assessment.get("regime", "UNKNOWN"),
                "at": datetime.now(timezone.utc).isoformat(),
            }

            if decision.should_trade:
                if not best_decision or decision.confidence > best_decision.confidence:
                    best_decision = decision

        # ── 7. Execute the best trade ──
        if best_decision:
            await _execute_trade(db, account, generation, best_decision, current_balance)

        # ── 8. Take treasury snapshot ──
        TreasuryManager.take_snapshot(db, generation)

        # ── 9. Update evolution stats ──
        EvolutionEngine.update_strategy_performance(db, generation)

    finally:
        db.close()


async def _execute_trade(
    db,
    account: ExchangeAccount,
    generation: Generation,
    decision,
    treasury_balance: float,
):
    """Execute a trade and record it."""
    global _bot_status
    symbol = decision.symbol
    side = decision.side

    # Get instrument info for proper rounding
    loop = asyncio.get_event_loop()
    inst = await loop.run_in_executor(None, bybit_client.get_instrument_info, symbol)

    # Calculate quantity
    risk_calc = RiskCalculator.calculate_position_size(
        treasury_balance=treasury_balance,
        risk_pct=decision.position_size_pct,
        entry_price=decision.entry_price,
        stop_loss_price=decision.stop_loss,
        leverage=decision.leverage,
    )

    if risk_calc.get("error"):
        logger.error(f"Position sizing error: {risk_calc['error']}")
        return

    qty = risk_calc["size"]
    if inst:
        qty = bybit_client.round_qty(qty, inst["qty_step"])
        if qty < inst["min_qty"]:
            logger.info(f"Calculated qty {qty} below minimum {inst['min_qty']} for {symbol}")
            return

    # Get owner for trading mode check
    owner = db.query(Owner).first()
    bybit_side = "Buy" if side == "LONG" else "Sell"

    if owner and owner.trading_mode == TradingMode.PAPER.value:
        # Paper trading — simulate
        result = {"order_id": f"paper_{int(datetime.now(timezone.utc).timestamp())}"}

        # Deduct from paper balance
        trade_value = qty * decision.entry_price
        bal = db.query(Balance).filter(
            Balance.account_id == account.id,
            Balance.asset == "USDT"
        ).first()
        if bal:
            margin_required = trade_value / decision.leverage
            bal.free -= margin_required
            db.commit()

        # Create position
        pos = Position(
            account_id=account.id,
            generation_id=generation.id,
            symbol=symbol,
            side=side,
            size=qty,
            entry_price=decision.entry_price,
            current_price=decision.entry_price,
            leverage=decision.leverage,
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit,
            strategy_used=decision.strategy_used,
            confidence_at_entry=decision.confidence,
        )
        db.add(pos)
        db.commit()
    else:
        # Live trading
        await loop.run_in_executor(
            None,
            bybit_client.set_leverage,
            account.api_key, account.api_secret,
            symbol, decision.leverage,
        )

        result = await loop.run_in_executor(
            None,
            bybit_client.place_order,
            account.api_key, account.api_secret,
            symbol, bybit_side, qty,
            "Market", None,
            decision.stop_loss, decision.take_profit,
        )

    if "error" in result:
        logger.error(f"Trade execution failed: {result['error']}")
        await _notify(
            f"❌ <b>Trade Failed</b>\n"
            f"Symbol: <code>{symbol}</code>\n"
            f"Error: <code>{result['error']}</code>"
        )
        return

    # Record in Memory
    MemoryEngine.record_trade_open(
        db=db,
        generation=generation,
        symbol=symbol,
        side=side,
        entry_price=decision.entry_price,
        size=qty,
        leverage=decision.leverage,
        strategy=decision.strategy_used,
        confidence=decision.confidence,
        market_regime=_bot_status.get("last_signal", {}).get("regime"),
        reason=decision.reasoning,
    )

    # Update generation stats
    generation.total_trades += 1
    db.commit()

    # Update bot status
    _bot_status["last_trade"] = {
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "price": decision.entry_price,
        "sl": decision.stop_loss,
        "tp": decision.take_profit,
        "leverage": decision.leverage,
        "confidence": decision.confidence,
        "strategy": decision.strategy_used,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    _bot_status["trades_today"] = _bot_status.get("trades_today", 0) + 1

    # Notify
    risk_pct = risk_calc.get("risk_pct_applied", decision.position_size_pct)
    await _notify(
        f"🚀 <b>{side} {symbol}</b>\n\n"
        f"Entry: <code>${decision.entry_price:,.4f}</code>\n"
        f"Leverage: <code>{decision.leverage}x</code>\n"
        f"Size: <code>{qty}</code>\n"
        f"Risk: <code>{risk_pct:.1f}%</code>\n"
        f"Confidence: <code>{decision.confidence:.0f}%</code>\n"
        f"Strategy: <code>{decision.strategy_used}</code>\n"
        f"SL: <code>${decision.stop_loss:,.4f}</code>\n"
        f"TP: <code>${decision.take_profit:,.4f}</code>\n"
        f"R:R: <code>{decision.risk_reward:.1f}</code>\n\n"
        f"Treasury: <code>${generation.current_treasury:,.2f}</code>\n"
        f"Generation: <b>G-{generation.number:02d}</b>"
    )

    logger.info(
        f"✅ Trade executed: {side} {qty} {symbol} @ ${decision.entry_price:,.4f} | "
        f"Strategy: {decision.strategy_used} | Confidence: {decision.confidence:.0f}%"
    )


# ═══════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════

def _get_paper_balance(db, account) -> float:
    bal = db.query(Balance).filter(
        Balance.account_id == account.id,
        Balance.asset == "USDT"
    ).first()
    return (bal.free + bal.locked) if bal else 0.0


def _get_live_balance(account) -> float:
    try:
        balances = bybit_client.get_balance(account.api_key, account.api_secret)
        usdt = balances.get("USDT", {})
        return usdt.get("total", 0.0)
    except Exception as e:
        logger.error(f"Failed to fetch live balance: {e}")
        return 0.0


async def _send_daily_report():
    """Send daily performance summary via Telegram."""
    db = SessionLocal()
    try:
        generation = TreasuryManager.get_active_generation(db)
        if not generation:
            return

        drawdowns = TreasuryManager.calculate_drawdowns(db, generation)
        strategy_stats = MemoryEngine.get_best_strategies(db, generation.id)

        # Build strategy summary
        strat_lines = []
        for name, stats in sorted(strategy_stats.items(), key=lambda x: x[1]["total_pnl"], reverse=True):
            emoji = "🟢" if stats["total_pnl"] > 0 else "🔴"
            strat_lines.append(
                f"  {emoji} {name}: {stats['trades']} trades, "
                f"{stats['win_rate']:.0f}% WR, ${stats['total_pnl']:+,.2f}"
            )

        strat_text = "\n".join(strat_lines) if strat_lines else "  No trades yet"

        await _notify(
            f"📊 <b>Daily Performance Report</b>\n\n"
            f"Generation: <b>G-{generation.number:02d}</b>\n"
            f"Status: <b>{generation.status}</b>\n\n"
            f"Treasury: <code>${generation.current_treasury:,.2f}</code>\n"
            f"Daily P&L: <code>${drawdowns['daily_pnl']:+,.2f}</code>\n"
            f"Weekly P&L: <code>${drawdowns['weekly_pnl']:+,.2f}</code>\n\n"
            f"Total Trades: <code>{generation.total_trades}</code>\n"
            f"Win Rate: <code>{generation.win_rate:.1f}%</code>\n"
            f"All-time P&L: <code>${generation.total_pnl:+,.2f}</code>\n\n"
            f"<b>Strategy Performance:</b>\n{strat_text}\n\n"
            f"Drawdowns:\n"
            f"  Daily: <code>{drawdowns['daily_pct']:.1f}%</code> / {settings.MAX_DAILY_DRAWDOWN_PCT}%\n"
            f"  Weekly: <code>{drawdowns['weekly_pct']:.1f}%</code> / {settings.MAX_WEEKLY_DRAWDOWN_PCT}%\n"
            f"  Monthly: <code>{drawdowns['monthly_pct']:.1f}%</code> / {settings.MAX_MONTHLY_DRAWDOWN_PCT}%"
        )
    finally:
        db.close()
