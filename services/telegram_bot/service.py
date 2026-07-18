"""
Apex Autonomous Trader — Telegram Command Center
==================================================
The primary interface for the owner to monitor and control the agent.
Accepts commands only from TELEGRAM_AUTHORIZED_CHAT_ID.
"""

import asyncio
import logging
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from apps.api.core.config import settings
from apps.api.core.database import SessionLocal
from shared.db.models import Owner, Generation, TradingMode, ExchangeAccount
from services.treasury.manager import TreasuryManager
from services.trading_engine.bot_loop import start_bot, stop_bot, get_status

logger = logging.getLogger("telegram_bot")

_bot_running = False
_bot_task: Optional[asyncio.Task] = None
_last_update_id = 0


# ═══════════════════════════════════════════════════════════
#  HTTP CLIENT
# ═══════════════════════════════════════════════════════════

async def _send_message(chat_id: str, text: str, parse_mode: str = "HTML"):
    """Send a message to a specific chat."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return
        
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10)
            if resp.status_code != 200:
                logger.error(f"Telegram send failed: {resp.text}")
    except Exception as e:
        logger.error(f"Telegram network error: {e}")


async def emit_notification(text: str):
    """Send a notification to the authorized owner."""
    if not settings.TELEGRAM_AUTHORIZED_CHAT_ID:
        logger.warning(f"Telegram notification skipped (no authorized chat ID): {text}")
        return
        
    await _send_message(settings.TELEGRAM_AUTHORIZED_CHAT_ID, text)


# ═══════════════════════════════════════════════════════════
#  POLLING LOOP
# ═══════════════════════════════════════════════════════════

async def _poll_telegram():
    global _last_update_id, _bot_running
    
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram polling disabled — no token provided.")
        return
        
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getUpdates"
    
    logger.info("Telegram polling started")
    
    while _bot_running:
        try:
            async with httpx.AsyncClient() as client:
                params = {"offset": _last_update_id + 1, "timeout": 30}
                resp = await client.get(url, params=params, timeout=35)
                
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("ok"):
                        updates = data.get("result", [])
                        for update in updates:
                            _last_update_id = update["update_id"]
                            if "message" in update:
                                await _handle_message(update["message"])
                else:
                    logger.error(f"Telegram poll error: {resp.status_code}")
                    await asyncio.sleep(5)
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Telegram polling exception: {e}")
            await asyncio.sleep(5)
            
        await asyncio.sleep(1)


# ═══════════════════════════════════════════════════════════
#  COMMAND HANDLER
# ═══════════════════════════════════════════════════════════

async def _handle_message(message: Dict[str, Any]):
    """Process incoming messages."""
    chat_id = str(message.get("chat", {}).get("id", ""))
    text = message.get("text", "").strip()
    
    if not text.startswith("/"):
        return
        
    # Security Check
    if chat_id != settings.TELEGRAM_AUTHORIZED_CHAT_ID:
        logger.warning(f"Unauthorized command from {chat_id}: {text}")
        await _send_message(chat_id, "⚠️ Unauthorized access.")
        return
        
    command_parts = text.split(" ")
    cmd = command_parts[0].lower()
    args = command_parts[1:]
    
    logger.info(f"Telegram command: {text}")
    
    db = SessionLocal()
    try:
        if cmd == "/start":
            await _cmd_start(db)
        elif cmd == "/status":
            await _cmd_status(db)
        elif cmd == "/spawn":
            await _cmd_spawn(db, args)
        elif cmd == "/kill":
            await _cmd_kill(db)
        elif cmd == "/start_trading":
            await _cmd_start_trading()
        elif cmd == "/stop_trading":
            await _cmd_stop_trading()
        elif cmd == "/mode":
            await _cmd_mode(db, args)
        elif cmd == "/report":
            await _cmd_report(db)
        elif cmd == "/memory":
            await _cmd_memory(db)
        elif cmd == "/help":
            await _cmd_help()
        else:
            await emit_notification(f"❓ Unknown command: {cmd}\nType /help for options.")
    except Exception as e:
        logger.error(f"Command execution error: {e}", exc_info=True)
        await emit_notification(f"⚠️ <b>Error processing command</b>\n<code>{e}</code>")
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
#  COMMAND IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════

async def _cmd_start(db):
    """Register owner and initialize."""
    owner = db.query(Owner).first()
    if not owner:
        owner = Owner(telegram_chat_id=settings.TELEGRAM_AUTHORIZED_CHAT_ID)
        db.add(owner)
        db.commit()
        
    await emit_notification(
        "👋 <b>Welcome to Apex Autonomous Trader</b>\n\n"
        "I am your AI trading organism. I operate autonomously, protect capital, and learn from experience.\n\n"
        "Send /help to see available commands."
    )


async def _cmd_help():
    """List commands."""
    help_text = (
        "🛠 <b>Apex Command Center</b>\n\n"
        "<b>System Control</b>\n"
        "/start_trading — Wake the agent up\n"
        "/stop_trading — Put the agent to sleep\n"
        "/status — View current status\n\n"
        "<b>Treasury & Life Cycle</b>\n"
        "/spawn [amount] — Spawn a new generation\n"
        "/kill — Manually terminate current generation\n"
        "/report — Generate performance report\n"
        "/memory — View recent trade memories\n\n"
        "<b>Settings</b>\n"
        "/mode [paper|live] — Switch trading mode\n"
    )
    await emit_notification(help_text)


async def _cmd_status(db):
    """View overall status."""
    owner = db.query(Owner).first()
    gen = TreasuryManager.get_active_generation(db)
    bot = get_status()
    
    if not owner:
        await emit_notification("Owner not configured. Send /start.")
        return
        
    mode_text = "🟢 LIVE" if owner.trading_mode == TradingMode.LIVE.value else "🟡 PAPER"
    state_text = "🏃 RUNNING" if bot["running"] else "💤 SLEEPING"
    
    gen_text = "No active generation. Send /spawn to create one."
    if gen:
        gen_text = (
            f"<b>Generation:</b> G-{gen.number:02d} ({gen.status})\n"
            f"<b>Treasury:</b> ${gen.current_treasury:,.2f} / ${gen.initial_treasury:,.2f}\n"
            f"<b>Trades:</b> {gen.total_trades} | <b>Win Rate:</b> {gen.win_rate:.1f}%"
        )
        
    status_msg = (
        f"📊 <b>System Status</b>\n\n"
        f"<b>Engine:</b> {state_text}\n"
        f"<b>Mode:</b> {mode_text}\n\n"
        f"{gen_text}\n\n"
        f"<b>Last Scan:</b> {bot.get('last_scan', 'Never')}\n"
        f"<b>Scanned Pairs:</b> {bot.get('pairs_scanned', 0)}\n"
        f"<b>Trades Today:</b> {bot.get('trades_today', 0)}"
    )
    
    await emit_notification(status_msg)


async def _cmd_spawn(db, args):
    """Spawn a new generation with an initial treasury."""
    owner = db.query(Owner).first()
    if not owner:
        await emit_notification("Please /start first.")
        return
        
    if len(args) != 1:
        await emit_notification("Usage: /spawn [amount_in_usdt]\nExample: /spawn 1000")
        return
        
    try:
        amount = float(args[0])
    except ValueError:
        await emit_notification("Amount must be a number.")
        return
        
    active = TreasuryManager.get_active_generation(db)
    if active:
        await emit_notification(
            f"⚠️ <b>Generation G-{active.number:02d} is still active.</b>\n"
            "You must /kill it before spawning a new one."
        )
        return
        
    from services.evolution.engine import EvolutionEngine
    gen = TreasuryManager.create_generation(db, amount)
    EvolutionEngine.initialize_generation(db, gen)
    
    await emit_notification(
        f"🧬 <b>Generation G-{gen.number:02d} Born</b>\n\n"
        f"Initial Treasury: <code>${amount:,.2f}</code>\n"
        f"Death Threshold: <code>${gen.death_threshold:,.2f}</code>\n\n"
        f"The agent inherits optimized parameters from previous generations."
    )


async def _cmd_kill(db):
    """Terminate current generation."""
    gen = TreasuryManager.get_active_generation(db)
    if not gen:
        await emit_notification("No active generation to kill.")
        return
        
    TreasuryManager.kill_generation(db, gen, "Manually terminated by owner")
    
    await emit_notification(
        f"💀 <b>Generation G-{gen.number:02d} Terminated</b>\n\n"
        f"Final Treasury: <code>${gen.current_treasury:,.2f}</code>\n"
        f"Total P&L: <code>${gen.total_pnl:,.2f}</code>\n"
        f"All open positions will be managed until closed, but no new trades will be opened."
    )


async def _cmd_start_trading():
    """Start autonomous loop."""
    success = start_bot()
    if not success:
        await emit_notification("⚠️ Agent is already running.")


async def _cmd_stop_trading():
    """Stop autonomous loop."""
    success = stop_bot()
    if not success:
        await emit_notification("⚠️ Agent is already sleeping.")


async def _cmd_mode(db, args):
    """Switch between Paper and Live trading."""
    if len(args) != 1 or args[0].lower() not in ["paper", "live"]:
        await emit_notification("Usage: /mode [paper|live]")
        return
        
    owner = db.query(Owner).first()
    if not owner:
        return
        
    mode = args[0].upper()
    owner.trading_mode = mode
    db.commit()
    
    emoji = "🟢" if mode == "LIVE" else "🟡"
    await emit_notification(f"{emoji} Trading mode set to <b>{mode}</b>")


async def _cmd_report(db):
    """Detailed performance report."""
    from services.trading_engine.bot_loop import _send_daily_report
    # Send daily report directly
    await emit_notification("Generating full performance report...")
    # Trigger the report logic
    from apps.api.core.config import settings
    # For now, just call the helper from bot_loop if we import it properly.
    # We will just write a custom quick report here.
    
    gen = TreasuryManager.get_active_generation(db)
    if not gen:
        await emit_notification("No active generation.")
        return
        
    summary = TreasuryManager.get_generation_summary(gen)
    
    msg = (
        f"📊 <b>Generation {summary['generation']} Report</b>\n\n"
        f"<b>Status:</b> {summary['status']}\n"
        f"<b>Treasury:</b> ${summary['current_treasury']:,.2f}\n"
        f"<b>Total P&L:</b> ${summary['total_pnl']:+,.2f}\n"
        f"<b>Trades:</b> {summary['total_trades']}\n"
        f"<b>Win Rate:</b> {summary['win_rate']:.1f}%\n"
        f"<b>Max Drawdown:</b> {summary['max_drawdown_pct']:.1f}%"
    )
    await emit_notification(msg)


async def _cmd_memory(db):
    """Show recent trade memories and scores."""
    from services.memory.engine import MemoryEngine
    gen = TreasuryManager.get_active_generation(db)
    if not gen:
        await emit_notification("No active generation.")
        return
        
    memories = MemoryEngine.get_trade_history(db, generation_id=gen.id, limit=5)
    
    if not memories:
        await emit_notification("No completed trades in memory yet.")
        return
        
    msg = f"🧠 <b>Recent Memory Records</b>\n\n"
    for m in memories:
        emoji = "✅" if m.pnl and m.pnl > 0 else "❌"
        msg += (
            f"{emoji} <b>{m.symbol}</b> ({m.side})\n"
            f"Strategy: {m.strategy_used}\n"
            f"P&L: ${m.pnl:+,.2f} ({m.pnl_pct:+.1f}%)\n"
            f"Score: {m.overall_score}/100\n"
            f"<i>{m.lessons_learned}</i>\n\n"
        )
        
    await emit_notification(msg)


# ═══════════════════════════════════════════════════════════
#  LIFECYCLE HOOKS
# ═══════════════════════════════════════════════════════════

def start_telegram_bot():
    """Start the polling loop task."""
    global _bot_running, _bot_task
    if _bot_running:
        return
    _bot_running = True
    _bot_task = asyncio.create_task(_poll_telegram())
    logger.info("Telegram service started")


def stop_telegram_bot():
    """Stop the polling loop."""
    global _bot_running, _bot_task
    _bot_running = False
    if _bot_task and not _bot_task.done():
        _bot_task.cancel()
    logger.info("Telegram service stopped")
