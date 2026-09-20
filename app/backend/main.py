from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import time
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.data.assets import RESEARCH_ASSETS, SUPPORTED_ASSETS, asset_payload, get_asset
from src.data.data_provider import DataProvider
from src.data.fx_provider import FxRateProvider, PlnRate


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LIVE_STATE_DIR = Path(
    os.getenv(
        "AL_TRADING_DATA_DIR",
        str(PROJECT_ROOT / "data" / "live_state"),
    )
)
TRADE_HISTORY_FILE = LIVE_STATE_DIR / "paper_live_history.csv"
SNAPSHOTS_FILE = LIVE_STATE_DIR / "paper_live_snapshots.csv"
DAILY_FILE = LIVE_STATE_DIR / "paper_live_daily.csv"
USER_PORTFOLIO_FILE = LIVE_STATE_DIR / "user_portfolio.json"
AI_CONTROL_FILE = LIVE_STATE_DIR / "ai_control.json"
RESEARCH_STATE_FILE = LIVE_STATE_DIR / "research_state.json"

FX_PROVIDER = FxRateProvider(ttl_seconds=60.0)
MARKET_CACHE: dict[str, dict[str, Any]] = {}
ASSET_LIVE_CACHE: dict[str, Any] = {"timestamp": 0.0, "prices": {}}


class PortfolioAmount(BaseModel):
    amount: float = Field(gt=0, le=1_000_000)


app = FastAPI(
    title="AL TRADING AGENT API",
    version="1.1.0",
    description=(
        "Dashboard API for real market data and virtual paper trading. "
        "No endpoint places real exchange orders."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def asset_or_error(symbol: str):
    try:
        return get_asset(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def state_file_for(symbol: str) -> Path:
    asset = asset_or_error(symbol)
    return LIVE_STATE_DIR / f"paper_live_{asset.symbol}_1m.json"


def load_state(symbol: str = "BTCUSDT") -> dict[str, Any]:
    asset = asset_or_error(symbol)
    state_file = state_file_for(asset.symbol)

    if not state_file.exists():
        return {
            "available": False,
            "symbol": asset.symbol,
            "error": f"State file not found: {state_file}",
        }

    try:
        with state_file.open("r", encoding="utf-8-sig") as handle:
            state = json.load(handle)

        state["available"] = True
        state["symbol"] = asset.symbol
        return state
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "available": False,
            "symbol": asset.symbol,
            "error": str(exc),
        }


def load_research_state() -> dict[str, Any]:
    if not RESEARCH_STATE_FILE.exists():
        return {
            "available": False,
            "stale": True,
            "opportunities": [],
            "macro_events": [],
            "error": f"Research state not found: {RESEARCH_STATE_FILE}",
        }

    try:
        with RESEARCH_STATE_FILE.open("r", encoding="utf-8-sig") as handle:
            state = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "available": False,
            "stale": True,
            "opportunities": [],
            "macro_events": [],
            "error": str(exc),
        }

    updated_at_unix = float(state.get("updated_at_unix") or 0.0)
    age_seconds = max(0.0, time.time() - updated_at_unix) if updated_at_unix else None
    state["available"] = True
    state["age_seconds"] = age_seconds
    state["stale"] = age_seconds is None or age_seconds > 180.0
    return state


def load_ai_state_raw() -> dict[str, Any]:
    """Load the autonomous AI paper account state without HTTP decoration."""
    path = LIVE_STATE_DIR / "ai_paper.json"
    try:
        with path.open(encoding="utf-8-sig") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def dashboard_asset_universe() -> tuple:
    """Curated app/research assets plus current dynamic research opportunities."""
    result = []
    seen = set()

    for asset in (*SUPPORTED_ASSETS, *RESEARCH_ASSETS):
        if asset.symbol in seen:
            continue
        result.append(asset)
        seen.add(asset.symbol)

    research_state = load_research_state()
    for row in research_state.get("opportunities", []):
        symbol = str(row.get("symbol") or "").strip()
        if not symbol or symbol in seen:
            continue
        try:
            asset = get_asset(symbol, allow_dynamic_binance=True)
        except ValueError:
            continue
        result.append(asset)
        seen.add(asset.symbol)

    return tuple(result)


def position_payload(state: dict[str, Any]) -> dict[str, Any]:
    position = state.get("position")
    if not position:
        return {
            "side": None,
            "entry_price": None,
            "quantity": 0.0,
            "stop_loss": None,
            "take_profit": None,
            "entry_timestamp": None,
        }

    return {
        "side": position.get("side"),
        "entry_price": float(position.get("entry_price", 0.0)),
        "quantity": float(position.get("quantity", 0.0)),
        "stop_loss": float(position.get("stop_loss", 0.0)),
        "take_profit": float(position.get("take_profit", 0.0)),
        "entry_timestamp": position.get("entry_timestamp"),
    }


def _fx_payload(asset) -> tuple[PlnRate | None, dict[str, Any]]:
    try:
        rate = FX_PROVIDER.quote_to_pln(asset.quote)
        return rate, {
            "available": True,
            **rate.as_dict(),
            "reporting_only": True,
        }
    except Exception as exc:
        return None, {
            "available": False,
            "source_currency": asset.quote,
            "rate_to_pln": None,
            "path": None,
            "providers": [],
            "quality": "UNAVAILABLE",
            "error": str(exc),
            "reporting_only": True,
        }


def _to_pln(value: float | int | None, rate: PlnRate | None) -> float | None:
    if value is None or rate is None:
        return None
    return float(value) * rate.rate_to_pln


def _unrealized_profit(position: dict[str, Any], market_price: float) -> float:
    side = position.get("side")
    if not side:
        return 0.0
    entry = float(position.get("entry_price", 0.0))
    quantity = float(position.get("quantity", 0.0))
    if side == "SELL":
        return (entry - market_price) * quantity
    return (market_price - entry) * quantity


def normalize_trade(
    trade: dict[str, Any],
    index: int,
    *,
    quote_currency: str,
    rate: PlnRate | None,
) -> dict[str, Any]:
    profit = float(trade["profit"])
    fee = float(trade["fee"])
    return {
        "trade_number": index,
        "side": trade.get("side"),
        "entry_price": float(trade["entry_price"]),
        "exit_price": float(trade["exit_price"]),
        "quantity": float(trade["quantity"]),
        "stop_loss": float(trade["stop_loss"]),
        "take_profit": float(trade["take_profit"]),
        "entry_timestamp": int(trade["entry_timestamp"]),
        "exit_timestamp": int(trade["exit_timestamp"]),
        "exit_reason": trade.get("exit_reason"),
        "gross_profit": float(trade["gross_profit"]),
        "fee": fee,
        "profit": profit,
        "quote_currency": quote_currency,
        "profit_pln": _to_pln(profit, rate),
        "fee_pln": _to_pln(fee, rate),
        "pln_conversion_basis": "current_reference" if rate else None,
    }


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "name": "AL TRADING AGENT API",
        "version": "1.1.0",
        "status": "online",
        "paper_only": True,
        "real_exchange_orders": False,
    }


@app.get("/api/health")
def health(symbol: str = "BTCUSDT") -> dict[str, Any]:
    asset = asset_or_error(symbol)
    state = load_state(asset.symbol)
    return {
        "api": "OK",
        "symbol": asset.symbol,
        "state_available": state.get("available", False),
        "state_version": state.get("version"),
        "last_processed_timestamp": state.get("last_processed_timestamp"),
        "paper_live_position": position_payload(state),
    }


@app.get("/api/status")
def status(symbol: str = "BTCUSDT") -> dict[str, Any]:
    asset = asset_or_error(symbol)
    state = load_state(asset.symbol)
    if not state.get("available"):
        return state

    trades = state.get("trade_manager_history") or []
    balance = float(state.get("balance", 0.0))
    initial_balance = 1000.0
    net_profit = balance - initial_balance
    market_price = float(state.get("market_price") or 0.0)
    position = position_payload(state)
    unrealized = _unrealized_profit(position, market_price)

    wins = [trade for trade in trades if float(trade.get("profit", 0.0)) > 0]
    losses = [trade for trade in trades if float(trade.get("profit", 0.0)) < 0]
    gross_profit = sum(float(trade["profit"]) for trade in wins)
    gross_loss = abs(sum(float(trade["profit"]) for trade in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else None
    win_rate = (len(wins) / len(trades)) * 100.0 if trades else 0.0
    expectancy = net_profit / len(trades) if trades else 0.0

    rate, fx = _fx_payload(asset)

    return {
        "available": True,
        "strategy": {
            "symbol": asset.symbol,
            "asset_name": asset.name,
            "asset_type": asset.asset_type,
            "instrument_type": asset.instrument_type,
            "provider": asset.provider,
            "provider_symbol": asset.provider_symbol,
            "quote": asset.quote,
            "note": asset.note,
            "interval": "1m",
            "buy_rsi": 33.8,
            "sell_rsi": 68.5,
            "max_position_candles": 241,
            "min_difference": asset.min_difference,
            "rsi_method": "classic",
            "trading_fee": 0.0004,
        },
        "system": {
            "state_version": state.get("version"),
            "last_processed_timestamp": state.get("last_processed_timestamp"),
        },
        "position": position,
        "pln": fx,
        "account": {
            "position": position.get("side") or "FLAT",
            "position_candles": int(state.get("position_candles", 0)),
            "quote_currency": asset.quote,
            "balance": balance,
            "initial_balance": initial_balance,
            "net_profit": net_profit,
            "unrealized_profit": unrealized,
            "peak_balance": float(state.get("peak_balance", 0.0)),
            "max_drawdown": float(state.get("max_drawdown", 0.0)),
            "market_price": market_price,
            "daily_loss": float((state.get("risk_guard") or {}).get("daily_loss", 0.0)),
            "balance_pln": _to_pln(balance, rate),
            "initial_balance_pln": _to_pln(initial_balance, rate),
            "net_profit_pln": _to_pln(net_profit, rate),
            "unrealized_profit_pln": _to_pln(unrealized, rate),
            "peak_balance_pln": _to_pln(float(state.get("peak_balance", 0.0)), rate),
            "max_drawdown_pln": _to_pln(float(state.get("max_drawdown", 0.0)), rate),
            "market_price_pln": _to_pln(market_price, rate),
        },
        "performance": {
            "trades": len(trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "avg_win": gross_profit / len(wins) if wins else 0.0,
            "avg_loss": gross_loss / len(losses) if losses else 0.0,
            "expectancy": expectancy,
            "gross_profit_pln": _to_pln(gross_profit, rate),
            "gross_loss_pln": _to_pln(gross_loss, rate),
            "expectancy_pln": _to_pln(expectancy, rate),
        },
    }


@app.get("/api/trades")
def trades(symbol: str = "BTCUSDT") -> list[dict[str, Any]]:
    asset = asset_or_error(symbol)
    state = load_state(asset.symbol)
    if not state.get("available"):
        return []

    rate, _ = _fx_payload(asset)
    raw_trades = state.get("trade_manager_history") or []
    return [
        normalize_trade(
            trade,
            index,
            quote_currency=asset.quote,
            rate=rate,
        )
        for index, trade in enumerate(raw_trades, start=1)
    ]


@app.get("/api/equity")
def equity(symbol: str = "BTCUSDT") -> dict[str, Any]:
    asset = asset_or_error(symbol)
    state = load_state(asset.symbol)
    if not state.get("available"):
        return {"available": False, "points": []}

    rate, fx = _fx_payload(asset)
    curve = state.get("equity_curve") or []
    return {
        "available": True,
        "quote_currency": asset.quote,
        "pln": fx,
        "points": [
            {
                "index": index,
                "balance": float(value),
                "balance_pln": _to_pln(float(value), rate),
            }
            for index, value in enumerate(curve)
        ],
    }


@app.get("/api/daily")
def daily() -> list[dict[str, Any]]:
    if not DAILY_FILE.exists():
        return []

    try:
        import csv

        with DAILY_FILE.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except OSError:
        return []

    result: list[dict[str, Any]] = []
    for row in rows:
        try:
            result.append(
                {
                    "date": row.get("Date"),
                    "balance": float(row.get("Balance", 0.0)),
                    "net_profit": float(row.get("NetProfit", 0.0)),
                    "trades": int(row.get("Trades", 0)),
                    "wins": int(row.get("Wins", 0)),
                    "losses": int(row.get("Losses", 0)),
                    "win_rate": float(row.get("WinRate", 0.0)),
                    "profit_factor": float(row.get("ProfitFactor", 0.0)),
                    "avg_win": float(row.get("AvgWin", 0.0)),
                    "avg_loss": float(row.get("AvgLoss", 0.0)),
                    "expectancy": float(row.get("Expectancy", 0.0)),
                    "max_drawdown": float(row.get("MaxDrawdown", 0.0)),
                    "position": row.get("Position"),
                    "market_price": float(row.get("MarketPrice", 0.0)),
                }
            )
        except (TypeError, ValueError):
            continue
    return result


def load_market_candles(symbol: str = "BTCUSDT", limit: int = 120) -> dict[str, Any]:
    asset = asset_or_error(symbol)
    cache = MARKET_CACHE.setdefault(asset.symbol, {"timestamp": 0.0, "points": []})
    now = time.time()

    if cache["points"] and now - cache["timestamp"] < 5.0:
        points = cache["points"]
        cached = True
        error = None
    else:
        try:
            candles = DataProvider().get_candles(
                symbol=asset.symbol,
                interval="1m",
                limit=limit,
            )
            points = [
                {
                    "timestamp": int(candle.timestamp),
                    "open": float(candle.open),
                    "high": float(candle.high),
                    "low": float(candle.low),
                    "close": float(candle.close),
                    "volume": float(candle.volume),
                }
                for candle in candles
            ]
            cache["timestamp"] = now
            cache["points"] = points
            cached = False
            error = None
        except Exception as exc:
            if not cache["points"]:
                return {
                    "available": False,
                    "symbol": asset.symbol,
                    "provider": asset.provider,
                    "provider_symbol": asset.provider_symbol,
                    "interval": "1m",
                    "points": [],
                    "error": str(exc),
                }
            points = cache["points"]
            cached = True
            error = str(exc)

    latest_timestamp = int(points[-1]["timestamp"]) if points else None
    age_seconds = (
        max(0.0, now - latest_timestamp / 1000.0)
        if latest_timestamp is not None
        else None
    )
    stale = bool(error) or (age_seconds is not None and age_seconds > 180.0)
    rate, fx = _fx_payload(asset)

    return {
        "available": True,
        "symbol": asset.symbol,
        "provider": asset.provider,
        "provider_symbol": asset.provider_symbol,
        "instrument_type": asset.instrument_type,
        "quote_currency": asset.quote,
        "interval": "1m",
        "points": points,
        "cached": cached,
        "stale": stale,
        "latest_timestamp": latest_timestamp,
        "age_seconds": age_seconds,
        "error": error,
        "pln": fx,
        "last_close_pln": _to_pln(points[-1]["close"], rate) if points else None,
    }


def dashboard_live_prices() -> dict[str, dict[str, Any]]:
    """Fresh prices for display only; paper execution still uses closed candles."""
    global ASSET_LIVE_CACHE

    now = time.time()
    cached_prices = ASSET_LIVE_CACHE.get("prices") or {}
    cached_at = float(ASSET_LIVE_CACHE.get("timestamp") or 0.0)

    if cached_prices and now - cached_at < 15.0:
        return cached_prices

    def fetch(asset):
        try:
            market = load_market_candles(symbol=asset.symbol, limit=2)
            points = market.get("points") or []
            if not points:
                return asset.symbol, None
            latest = points[-1]
            return asset.symbol, {
                "price": float(latest["close"]),
                "timestamp": int(latest["timestamp"]),
                "stale": bool(market.get("stale", False)),
                "provider": asset.provider,
            }
        except Exception as exc:
            return asset.symbol, {"error": f"{type(exc).__name__}: {exc}"}

    workers = min(6, max(1, len(SUPPORTED_ASSETS)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(fetch, SUPPORTED_ASSETS))

    fresh_prices = {
        symbol: payload
        for symbol, payload in rows
        if payload is not None and payload.get("price") is not None
    }
    merged = dict(cached_prices)
    merged.update(fresh_prices)
    ASSET_LIVE_CACHE = {"timestamp": now, "prices": merged}
    return merged


@app.get("/api/assets")
def assets() -> list[dict[str, Any]]:
    result = []
    fx_by_quote: dict[str, tuple[PlnRate | None, dict[str, Any]]] = {}

    live_prices = dashboard_live_prices()
    ai_state = load_ai_state_raw()
    ai_positions = ai_state.get("positions") or {}
    ai_marks = ai_state.get("market_marks") or {}
    now_ms = int(time.time() * 1000)

    for asset in dashboard_asset_universe():
        legacy_state = (
            load_state(asset.symbol)
            if asset.symbol in {row.symbol for row in SUPPORTED_ASSETS}
            else {"available": False}
        )

        paper_market_price = float(legacy_state.get("market_price") or 0.0)
        live = live_prices.get(asset.symbol) or {}
        mark = ai_marks.get(asset.symbol) or {}

        if live.get("price") is not None:
            market_price = float(live["price"])
            market_timestamp = live.get("timestamp")
            market_stale = bool(live.get("stale", False))
            market_provider = live.get("provider", asset.provider)
            market_live = True
        elif mark.get("price") is not None:
            market_price = float(mark["price"])
            market_timestamp = mark.get("timestamp")
            age_ms = (
                now_ms - int(market_timestamp)
                if market_timestamp is not None
                else 10**12
            )
            freshness_ms = 180_000 if asset.asset_type == "crypto" else 1_800_000
            market_stale = age_ms > freshness_ms
            market_provider = asset.provider
            market_live = not market_stale
        else:
            market_price = paper_market_price
            market_timestamp = None
            market_stale = True
            market_provider = asset.provider
            market_live = False

        position = ai_positions.get(asset.symbol) or {}
        position_side = position.get("side") or "FLAT"
        ai_pnl_pln = float(position.get("unrealized_pnl") or 0.0)

        if asset.quote not in fx_by_quote:
            fx_by_quote[asset.quote] = _fx_payload(asset)
        rate, fx = fx_by_quote[asset.quote]

        result.append(
            {
                **asset_payload(asset),
                "state_available": legacy_state.get("available", False),
                "market_price": market_price,
                "market_price_pln": _to_pln(market_price, rate),
                "paper_market_price": paper_market_price,
                "market_timestamp": market_timestamp,
                "market_live": market_live,
                "market_stale": market_stale,
                "market_provider": market_provider,

                # Primary dashboard trading state = autonomous AI paper account.
                "position": position_side,
                "ai_position": position if position else None,
                "ai_pnl_pln": ai_pnl_pln,
                "ai_allocation_pln": float(position.get("allocation_pln") or 0.0),
                "net_profit_pln": ai_pnl_pln,

                # Legacy per-symbol paper worker remains visible only as metadata.
                "legacy_position": (
                    legacy_state.get("position", {}).get("side")
                    if legacy_state.get("position")
                    else "FLAT"
                ),
                "legacy_balance": float(legacy_state.get("balance") or 0.0),
                "pln": fx,
            }
        )

    return result


@app.get("/api/ai")
def ai_status() -> dict[str, Any]:
    state = load_ai_state_raw()
    try:
        last_cycle = int(state["last_cycle"])
        age = time.time() - last_cycle / 1000
        return {
            **state,
            "available": True,
            "stale": age > 180,
            "age_seconds": max(0, age),
        }
    except (ValueError, KeyError, TypeError):
        return {
            "available": False,
            "mode": "PAPER_ONLY",
            "reason": "Moduł AI nie zapisał jeszcze poprawnego cyklu",
        }


def user_portfolio_state() -> dict[str, Any]:
    default = {
        "version": 1,
        "currency": "PLN",
        "balance": 0.0,
        "total_deposited": 0.0,
        "total_withdrawn": 0.0,
        "transferred_to_ai": 0.0,
        "ai_transfers": [],
        "profit_transferred": 0.0,
        "profit_transfers": [],
        "result": 0.0,
        "available": True,
    }
    try:
        with USER_PORTFOLIO_FILE.open(encoding="utf-8-sig") as handle:
            state = {**default, **json.load(handle)}
        state["result"] = state.get("profit_transferred", 0.0)
        return state
    except (OSError, ValueError, TypeError, KeyError):
        return default


def save_user_portfolio(state: dict[str, Any]) -> dict[str, Any]:
    LIVE_STATE_DIR.mkdir(parents=True, exist_ok=True)
    temporary = USER_PORTFOLIO_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(USER_PORTFOLIO_FILE)
    return user_portfolio_state()


def ai_control_state() -> dict[str, Any]:
    default = {
        "version": 1,
        "paper_only": True,
        "funding_events": [],
    }
    try:
        with AI_CONTROL_FILE.open(encoding="utf-8-sig") as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            return default
        return {**default, **value}
    except (OSError, ValueError, TypeError):
        return default


def save_ai_control(state: dict[str, Any]) -> dict[str, Any]:
    LIVE_STATE_DIR.mkdir(parents=True, exist_ok=True)
    temporary = AI_CONTROL_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(AI_CONTROL_FILE)
    return ai_control_state()


@app.get("/api/user-portfolio")
def get_user_portfolio() -> dict[str, Any]:
    return user_portfolio_state()


@app.post("/api/user-portfolio/deposit")
def deposit_user_portfolio(request: PortfolioAmount) -> dict[str, Any]:
    state = user_portfolio_state()
    state["balance"] += request.amount
    state["total_deposited"] += request.amount
    return save_user_portfolio(state)


@app.post("/api/user-portfolio/withdraw")
def withdraw_user_portfolio(request: PortfolioAmount) -> dict[str, Any]:
    state = user_portfolio_state()
    if request.amount > state["balance"]:
        raise HTTPException(status_code=400, detail="Niewystarczające saldo portfela")
    state["balance"] -= request.amount
    state["total_withdrawn"] += request.amount
    return save_user_portfolio(state)


@app.post("/api/ai/fund")
def fund_ai_account(request: PortfolioAmount) -> dict[str, Any]:
    """Move virtual PLN from the user wallet to the autonomous paper account."""
    portfolio = user_portfolio_state()
    amount = float(request.amount)

    if amount > float(portfolio.get("balance") or 0.0):
        raise HTTPException(
            status_code=400,
            detail="Niewystarczające saldo portfela PLN",
        )

    event = {
        "id": str(uuid4()),
        "amount": amount,
        "currency": "PLN",
        "created_at_unix": time.time(),
        "paper_only": True,
    }

    original = dict(portfolio)
    portfolio["balance"] = float(portfolio.get("balance") or 0.0) - amount
    portfolio["transferred_to_ai"] = (
        float(portfolio.get("transferred_to_ai") or 0.0) + amount
    )
    portfolio["ai_transfers"] = (
        list(portfolio.get("ai_transfers") or []) + [event]
    )[-500:]

    save_user_portfolio(portfolio)

    try:
        control = ai_control_state()
        control["funding_events"] = (
            list(control.get("funding_events") or []) + [event]
        )[-500:]
        save_ai_control(control)
    except Exception:
        save_user_portfolio(original)
        raise

    return {
        "accepted": True,
        "paper_only": True,
        "transfer": event,
        "portfolio": user_portfolio_state(),
        "message": "Transfer przyjęty. AI zastosuje środki w najbliższym cyklu.",
    }


@app.get("/api/market")
def market(symbol: str = "BTCUSDT") -> dict[str, Any]:
    return load_market_candles(symbol=symbol, limit=120)


@app.get("/api/files")
def files(symbol: str = "BTCUSDT") -> dict[str, bool]:
    asset = asset_or_error(symbol)
    state_file = state_file_for(asset.symbol)
    return {
        "state": state_file.exists(),
        "trade_history": TRADE_HISTORY_FILE.exists(),
        "snapshots": SNAPSHOTS_FILE.exists(),
        "daily": DAILY_FILE.exists(),
    }


@app.get("/api/research")
def research() -> dict[str, Any]:
    return load_research_state()


@app.get("/api/research/opportunities")
def research_opportunities() -> dict[str, Any]:
    state = load_research_state()
    return {
        "available": state.get("available", False),
        "stale": state.get("stale", True),
        "updated_at": state.get("updated_at"),
        "universe_count": state.get("universe_count", 0),
        "opportunities": state.get("opportunities", []),
        "errors": state.get("errors", {}),
    }


@app.get("/api/research/macro")
def research_macro() -> dict[str, Any]:
    state = load_research_state()
    return {
        "available": state.get("available", False),
        "stale": state.get("stale", True),
        "updated_at": state.get("updated_at"),
        "events": state.get("macro_events", []),
    }
