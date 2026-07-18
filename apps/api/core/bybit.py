"""
Apex Autonomous Trader — Bybit API Client
==========================================
Handles all communication with the Bybit exchange.
Supports both testnet and mainnet.
Implements clock synchronization to avoid timestamp errors.
"""

import time
import logging
import requests
from typing import Optional, List, Dict, Any, Tuple
from pybit.unified_trading import HTTP
from pybit import _helpers

from apps.api.core.config import settings

logger = logging.getLogger("bybit_client")


# ═══════════════════════════════════════════════════════════
#  CLOCK SYNC — Align local time with Bybit server
# ═══════════════════════════════════════════════════════════

_time_offset = 0.0
_last_sync_time = 0.0


def sync_bybit_time():
    """Synchronize local clock with Bybit server time."""
    global _time_offset, _last_sync_time
    if time.time() - _last_sync_time < 300:
        return
    try:
        subdomain = "api-testnet" if settings.BYBIT_TESTNET else "api"
        url = f"https://{subdomain}.bybit.com/v5/market/time"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("retCode") == 0:
                server_time_ms = int(data.get("time", 0))
                if server_time_ms > 0:
                    local_time_ms = int(time.time() * 1000)
                    _time_offset = (server_time_ms - local_time_ms) / 1000.0
                    _last_sync_time = time.time()
                    logger.info(f"Bybit time synced. Offset: {_time_offset:.3f}s")
    except Exception as e:
        logger.warning(f"Bybit time sync failed: {e}")


def _patched_generate_timestamp():
    sync_bybit_time()
    return int((time.time() + _time_offset) * 1000)


# Apply clock patch to pybit
_helpers.generate_timestamp = _patched_generate_timestamp


# ═══════════════════════════════════════════════════════════
#  CLIENT FACTORY
# ═══════════════════════════════════════════════════════════

def get_client(api_key: str = None, api_secret: str = None) -> HTTP:
    """Authenticated Bybit HTTP session."""
    return HTTP(
        testnet=settings.BYBIT_TESTNET,
        api_key=api_key,
        api_secret=api_secret,
        recv_window=15000,
    )


def get_public_client() -> HTTP:
    """Unauthenticated client for public market data."""
    return HTTP(testnet=settings.BYBIT_TESTNET)


# ═══════════════════════════════════════════════════════════
#  CONNECTION TEST
# ═══════════════════════════════════════════════════════════

def test_connection(api_key: str, api_secret: str) -> Tuple[bool, Any]:
    """Test if API credentials are valid."""
    try:
        session = get_client(api_key, api_secret)
        response = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
        return True, response
    except Exception as e:
        return False, str(e)


# ═══════════════════════════════════════════════════════════
#  BALANCE
# ═══════════════════════════════════════════════════════════

def get_balance(api_key: str, api_secret: str) -> Dict[str, Any]:
    """
    Fetch UNIFIED account balance from Bybit.
    Returns: {coin: {free, locked, total}}
    """
    session = get_client(api_key, api_secret)
    response = session.get_wallet_balance(accountType="UNIFIED")

    balances = {}
    account_list = response.get("result", {}).get("list", [])
    for account in account_list:
        for coin_data in account.get("coin", []):
            coin = coin_data.get("coin", "")
            equity = float(coin_data.get("equity", 0) or 0)
            available = float(coin_data.get("availableToWithdraw", 0) or 0)
            locked = equity - available
            if equity > 0:
                balances[coin] = {
                    "free": available,
                    "locked": max(0, locked),
                    "total": equity,
                }
    return balances


# ═══════════════════════════════════════════════════════════
#  POSITIONS
# ═══════════════════════════════════════════════════════════

def get_positions(api_key: str, api_secret: str) -> List[Dict[str, Any]]:
    """Fetch all open positions."""
    session = get_client(api_key, api_secret)
    response = session.get_positions(category="linear", settleCoin="USDT")

    positions = []
    for pos in response.get("result", {}).get("list", []):
        size = float(pos.get("size", 0) or 0)
        if size > 0:
            positions.append({
                "symbol": pos.get("symbol", ""),
                "side": pos.get("side", ""),
                "size": size,
                "entry_price": float(pos.get("avgPrice", 0) or 0),
                "mark_price": float(pos.get("markPrice", 0) or 0),
                "leverage": int(float(pos.get("leverage", 1) or 1)),
                "unrealized_pnl": float(pos.get("unrealisedPnl", 0) or 0),
                "liq_price": float(pos.get("liqPrice", 0) or 0),
                "take_profit": float(pos.get("takeProfit", 0) or 0),
                "stop_loss": float(pos.get("stopLoss", 0) or 0),
            })
    return positions


# ═══════════════════════════════════════════════════════════
#  MARKET DATA
# ═══════════════════════════════════════════════════════════

def get_price(symbol: str) -> Optional[float]:
    """Get current price for a symbol."""
    try:
        session = get_public_client()
        response = session.get_tickers(category="linear", symbol=symbol)
        tickers = response.get("result", {}).get("list", [])
        if tickers:
            return float(tickers[0].get("lastPrice", 0))
    except Exception as e:
        logger.error(f"Failed to get price for {symbol}: {e}")
    return None


def get_candles(
    symbol: str,
    interval: str = "5",
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """
    Fetch kline/candlestick data.
    interval: "1" | "3" | "5" | "15" | "30" | "60" | "120" | "240" | "D" | "W"
    """
    try:
        session = get_public_client()
        response = session.get_kline(
            category="linear",
            symbol=symbol,
            interval=interval,
            limit=limit,
        )
        candles = []
        for c in reversed(response.get("result", {}).get("list", [])):
            candles.append({
                "timestamp": int(c[0]),
                "open": float(c[1]),
                "high": float(c[2]),
                "low": float(c[3]),
                "close": float(c[4]),
                "volume": float(c[5]),
                "turnover": float(c[6]) if len(c) > 6 else 0.0,
            })
        return candles
    except Exception as e:
        logger.error(f"Failed to get candles for {symbol}: {e}")
        return []


def get_funding_rate(symbol: str) -> Optional[Dict[str, Any]]:
    """Get current and predicted funding rate for a symbol."""
    try:
        session = get_public_client()
        response = session.get_tickers(category="linear", symbol=symbol)
        tickers = response.get("result", {}).get("list", [])
        if tickers:
            t = tickers[0]
            return {
                "symbol": symbol,
                "funding_rate": float(t.get("fundingRate", 0) or 0),
                "next_funding_time": t.get("nextFundingTime", ""),
            }
    except Exception as e:
        logger.error(f"Failed to get funding rate for {symbol}: {e}")
    return None


def get_open_interest(symbol: str) -> Optional[Dict[str, Any]]:
    """Get open interest for a symbol."""
    try:
        session = get_public_client()
        response = session.get_open_interest(
            category="linear",
            symbol=symbol,
            intervalTime="5min",
            limit=1,
        )
        oi_list = response.get("result", {}).get("list", [])
        if oi_list:
            return {
                "symbol": symbol,
                "open_interest": float(oi_list[0].get("openInterest", 0) or 0),
                "timestamp": int(oi_list[0].get("timestamp", 0) or 0),
            }
    except Exception as e:
        logger.error(f"Failed to get OI for {symbol}: {e}")
    return None


def get_long_short_ratio(symbol: str) -> Optional[Dict[str, Any]]:
    """Get long/short ratio."""
    try:
        session = get_public_client()
        response = session.get_long_short_ratio(
            category="linear",
            symbol=symbol,
            period="5min",
            limit=1,
        )
        ls_list = response.get("result", {}).get("list", [])
        if ls_list:
            return {
                "symbol": symbol,
                "buy_ratio": float(ls_list[0].get("buyRatio", 0.5) or 0.5),
                "sell_ratio": float(ls_list[0].get("sellRatio", 0.5) or 0.5),
                "timestamp": int(ls_list[0].get("timestamp", 0) or 0),
            }
    except Exception as e:
        logger.error(f"Failed to get L/S ratio for {symbol}: {e}")
    return None


# ═══════════════════════════════════════════════════════════
#  MARKET SCAN
# ═══════════════════════════════════════════════════════════

def scan_market(
    top_n: int = 20,
    min_volume_usdt: float = 5_000_000,
) -> List[Dict[str, Any]]:
    """
    Scan all USDT perpetual pairs and return the top N by volume.
    Filters by minimum 24h volume.
    """
    try:
        session = get_public_client()
        response = session.get_tickers(category="linear")
        all_tickers = response.get("result", {}).get("list", [])

        pairs = []
        for t in all_tickers:
            symbol = t.get("symbol", "")
            if not symbol.endswith("USDT"):
                continue

            volume_24h = float(t.get("turnover24h", 0) or 0)
            if volume_24h < min_volume_usdt:
                continue

            last_price = float(t.get("lastPrice", 0) or 0)
            high_24h = float(t.get("highPrice24h", 0) or 0)
            low_24h = float(t.get("lowPrice24h", 0) or 0)
            price_change = float(t.get("price24hPcnt", 0) or 0) * 100

            # Calculate simple volatility metric
            volatility = 0.0
            if low_24h > 0:
                volatility = ((high_24h - low_24h) / low_24h) * 100

            pairs.append({
                "symbol": symbol,
                "last_price": last_price,
                "volume_24h": volume_24h,
                "high_24h": high_24h,
                "low_24h": low_24h,
                "price_change": price_change,
                "volatility": volatility,
                "funding_rate": float(t.get("fundingRate", 0) or 0),
            })

        # Sort by 24h volume descending
        pairs.sort(key=lambda x: x["volume_24h"], reverse=True)
        return pairs[:top_n]

    except Exception as e:
        logger.error(f"Market scan failed: {e}")
        return []


# ═══════════════════════════════════════════════════════════
#  ORDER EXECUTION
# ═══════════════════════════════════════════════════════════

def set_leverage(
    api_key: str,
    api_secret: str,
    symbol: str,
    leverage: int,
) -> bool:
    """Set leverage for a symbol."""
    try:
        session = get_client(api_key, api_secret)
        session.set_leverage(
            category="linear",
            symbol=symbol,
            buyLeverage=str(leverage),
            sellLeverage=str(leverage),
        )
        return True
    except Exception as e:
        # Error 110043 means leverage not modified (already set) — this is fine
        if "110043" in str(e):
            return True
        logger.error(f"Failed to set leverage for {symbol}: {e}")
        return False


def place_order(
    api_key: str,
    api_secret: str,
    symbol: str,
    side: str,
    qty: float,
    order_type: str = "Market",
    price: float = None,
    stop_loss: float = None,
    take_profit: float = None,
) -> Dict[str, Any]:
    """
    Place an order on Bybit.
    side: "Buy" or "Sell"
    order_type: "Market" or "Limit"
    """
    try:
        session = get_client(api_key, api_secret)

        order_params = {
            "category": "linear",
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "qty": str(qty),
        }

        if order_type == "Limit" and price:
            order_params["price"] = str(price)

        if stop_loss:
            order_params["stopLoss"] = str(round(stop_loss, 4))
        if take_profit:
            order_params["takeProfit"] = str(round(take_profit, 4))

        response = session.place_order(**order_params)
        result = response.get("result", {})

        return {
            "order_id": result.get("orderId", ""),
            "order_link_id": result.get("orderLinkId", ""),
        }

    except Exception as e:
        logger.error(f"Order placement failed: {e}")
        return {"error": str(e)}


def cancel_order(
    api_key: str,
    api_secret: str,
    symbol: str,
    order_id: str,
) -> Dict[str, Any]:
    """Cancel an open order."""
    try:
        session = get_client(api_key, api_secret)
        response = session.cancel_order(
            category="linear",
            symbol=symbol,
            orderId=order_id,
        )
        return {"status": "cancelled", "order_id": order_id}
    except Exception as e:
        logger.error(f"Cancel order failed: {e}")
        return {"error": str(e)}


def get_instrument_info(symbol: str) -> Optional[Dict[str, Any]]:
    """Get instrument specifications (min qty, tick size, etc.)."""
    try:
        session = get_public_client()
        response = session.get_instruments_info(
            category="linear",
            symbol=symbol,
        )
        instruments = response.get("result", {}).get("list", [])
        if instruments:
            inst = instruments[0]
            lot_filter = inst.get("lotSizeFilter", {})
            price_filter = inst.get("priceFilter", {})
            return {
                "symbol": symbol,
                "min_qty": float(lot_filter.get("minOrderQty", 0.001)),
                "max_qty": float(lot_filter.get("maxOrderQty", 100)),
                "qty_step": float(lot_filter.get("qtyStep", 0.001)),
                "min_price": float(price_filter.get("minPrice", 0.01)),
                "max_price": float(price_filter.get("maxPrice", 999999)),
                "tick_size": float(price_filter.get("tickSize", 0.01)),
                "max_leverage": float(inst.get("leverageFilter", {}).get("maxLeverage", 100)),
            }
    except Exception as e:
        logger.error(f"Failed to get instrument info for {symbol}: {e}")
    return None


def round_qty(qty: float, qty_step: float) -> float:
    """Round quantity to the nearest valid step size."""
    if qty_step <= 0:
        return round(qty, 6)
    precision = len(str(qty_step).rstrip('0').split('.')[-1]) if '.' in str(qty_step) else 0
    return round(round(qty / qty_step) * qty_step, precision)


def round_price(price: float, tick_size: float) -> float:
    """Round price to the nearest valid tick size."""
    if tick_size <= 0:
        return round(price, 4)
    precision = len(str(tick_size).rstrip('0').split('.')[-1]) if '.' in str(tick_size) else 0
    return round(round(price / tick_size) * tick_size, precision)
