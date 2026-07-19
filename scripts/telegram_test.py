"""
Apex Autonomous Trader — Standalone Telegram Bot Test
======================================================
Run this script DIRECTLY to test the Telegram integration
without needing the full backend (FastAPI, SQLAlchemy, etc).

Usage:
    python scripts/telegram_test.py

It will:
  1. Read TELEGRAM_BOT_TOKEN from .env
  2. Start polling for messages
  3. Auto-capture your chat_id on first /start command
  4. Write TELEGRAM_AUTHORIZED_CHAT_ID to .env
  5. Respond to all bot commands
"""

import os
import sys
import json
import ssl
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

# Fix Windows console encoding
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Resolve project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

# ─── Load .env manually (no dependencies needed) ───
def load_env():
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                val = val.strip().strip('"').strip("'")
                env[key.strip()] = val
    return env

def save_chat_id_to_env(chat_id: str):
    """Write TELEGRAM_AUTHORIZED_CHAT_ID into .env file."""
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    updated = False
    for i, line in enumerate(lines):
        if line.strip().startswith("TELEGRAM_AUTHORIZED_CHAT_ID"):
            lines[i] = f'TELEGRAM_AUTHORIZED_CHAT_ID="{chat_id}"'
            updated = True
            break
    if not updated:
        lines.append(f'TELEGRAM_AUTHORIZED_CHAT_ID="{chat_id}"')
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  ✅ Saved CHAT_ID={chat_id} to .env")


# ─── Telegram API helpers (zero dependencies) ───
# Bypass SSL cert issues on Windows
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def tg_request(token: str, method: str, params: dict = None):
    """Call the Telegram Bot API."""
    url = f"https://api.telegram.org/bot{token}/{method}"
    if params:
        data = json.dumps(params).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    else:
        req = urllib.request.Request(url)
    try:
        resp = urllib.request.urlopen(req, timeout=40, context=ctx)
        return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  ❌ HTTP {e.code}: {body}")
        return None
    except Exception as e:
        print(f"  ❌ Network error: {e}")
        return None


def send_message(token: str, chat_id: str, text: str):
    return tg_request(token, "sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    })


# ─── Command handlers ───
HELP_TEXT = (
    "🛠 <b>Apex Command Center</b>\n\n"
    "<b>System Control</b>\n"
    "/start — Initialize and register\n"
    "/start_trading — Wake the agent up\n"
    "/stop_trading — Put the agent to sleep\n"
    "/status — View current status\n\n"
    "<b>Treasury & Life Cycle</b>\n"
    "/spawn [amount] — Spawn a new generation\n"
    "/kill — Terminate current generation\n"
    "/report — Performance report\n"
    "/memory — View trade memories\n\n"
    "<b>Settings</b>\n"
    "/mode [paper|live] — Switch trading mode\n"
    "/help — Show this message\n"
)

def handle_command(token: str, chat_id: str, text: str, authorized_id: str):
    """Handle a command and return response text."""
    cmd = text.split()[0].lower()

    if cmd == "/start":
        return (
            "👋 <b>Welcome to Apex Autonomous Trader</b>\n\n"
            f"Your Chat ID: <code>{chat_id}</code>\n"
            "✅ You are now registered as the owner.\n\n"
            "I am your AI trading organism. I operate autonomously, "
            "protect capital, and learn from experience.\n\n"
            "Send /help to see available commands."
        )
    elif cmd == "/help":
        return HELP_TEXT
    elif cmd == "/status":
        return (
            "📊 <b>System Status</b>\n\n"
            "<b>Engine:</b> 💤 SLEEPING (backend not running)\n"
            "<b>Mode:</b> 🟡 PAPER\n\n"
            "⚠️ The full backend is not running yet.\n"
            "This is a standalone Telegram test.\n"
            "Deploy the backend to enable live trading."
        )
    elif cmd == "/spawn":
        parts = text.split()
        if len(parts) < 2:
            return "Usage: /spawn [amount_in_usdt]\nExample: /spawn 1000"
        try:
            amount = float(parts[1])
            return (
                f"🧬 <b>Generation Spawn Request</b>\n\n"
                f"Requested Treasury: <code>${amount:,.2f}</code>\n\n"
                "⚠️ Backend not running — this is a test response.\n"
                "Deploy the full system to execute spawns."
            )
        except ValueError:
            return "Amount must be a number."
    elif cmd == "/kill":
        return (
            "💀 <b>Kill Command Received</b>\n\n"
            "⚠️ Backend not running — this is a test response.\n"
            "Deploy the full system to terminate generations."
        )
    elif cmd == "/start_trading":
        return "🏃 <b>Start Trading</b> command received.\n⚠️ Backend not running."
    elif cmd == "/stop_trading":
        return "💤 <b>Stop Trading</b> command received.\n⚠️ Backend not running."
    elif cmd == "/mode":
        parts = text.split()
        if len(parts) < 2 or parts[1].lower() not in ("paper", "live"):
            return "Usage: /mode [paper|live]"
        mode = parts[1].upper()
        emoji = "🟢" if mode == "LIVE" else "🟡"
        return f"{emoji} Mode would be set to <b>{mode}</b>.\n⚠️ Backend not running."
    elif cmd == "/report":
        return (
            "📊 <b>Performance Report</b>\n\n"
            "⚠️ Backend not running — no live data available.\n"
            "Deploy the full system to generate reports."
        )
    elif cmd == "/memory":
        return (
            "🧠 <b>Trade Memories</b>\n\n"
            "⚠️ Backend not running — no memories stored.\n"
            "Deploy the full system to access the memory engine."
        )
    else:
        return f"❓ Unknown command: {cmd}\nType /help for options."


# ─── Main polling loop ───
def main():
    env = load_env()
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    authorized_id = env.get("TELEGRAM_AUTHORIZED_CHAT_ID", "")

    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env")
        sys.exit(1)

    print("=" * 60)
    print("  APEX AUTONOMOUS TRADER — Telegram Bot Test")
    print("=" * 60)
    print(f"  Token: {token[:12]}...{token[-6:]}")
    print(f"  Authorized Chat ID: {authorized_id or '(not set — will capture on /start)'}")
    print()

    # Verify bot identity
    me = tg_request(token, "getMe")
    if not me or not me.get("ok"):
        print("❌ Failed to connect to Telegram. Check your token.")
        sys.exit(1)
    bot_info = me["result"]
    print(f"  ✅ Connected as @{bot_info['username']} ({bot_info['first_name']})")
    print(f"  📡 Listening for messages... (Ctrl+C to stop)")
    print("-" * 60)

    last_update_id = 0

    while True:
        try:
            result = tg_request(token, "getUpdates", {
                "offset": last_update_id + 1,
                "timeout": 30,
            })

            if not result or not result.get("ok"):
                time.sleep(5)
                continue

            for update in result.get("result", []):
                last_update_id = update["update_id"]
                msg = update.get("message")
                if not msg:
                    continue

                chat_id = str(msg["chat"]["id"])
                text = msg.get("text", "").strip()
                user = msg.get("from", {})
                username = user.get("username", "unknown")

                print(f"  📩 [{username}] (chat_id={chat_id}): {text}")

                if not text.startswith("/"):
                    continue

                # Auto-capture chat ID on first /start
                if not authorized_id and text.startswith("/start"):
                    authorized_id = chat_id
                    save_chat_id_to_env(chat_id)
                    print(f"  🔑 Authorized chat ID captured: {chat_id}")

                # Security: only respond to authorized user
                if authorized_id and chat_id != authorized_id:
                    send_message(token, chat_id, "⚠️ Unauthorized access.")
                    print(f"  ⛔ Blocked unauthorized user: {chat_id}")
                    continue

                # Handle the command
                response = handle_command(token, chat_id, text, authorized_id)
                result_msg = send_message(token, chat_id, response)
                if result_msg and result_msg.get("ok"):
                    print(f"  ✅ Reply sent to {chat_id}")
                else:
                    print(f"  ❌ Failed to send reply")

        except KeyboardInterrupt:
            print("\n  🛑 Bot stopped.")
            break
        except Exception as e:
            print(f"  ❌ Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
