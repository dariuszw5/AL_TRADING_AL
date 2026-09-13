from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.data.assets import SUPPORTED_ASSETS, asset_payload, get_asset
from src.data.data_provider import DataProvider


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LIVE_STATE_DIR = PROJECT_ROOT / "data" / "live_state"
STATE_FILE = LIVE_STATE_DIR / "paper_live_BTCUSDT_1m.json"
TRADE_HISTORY_FILE = LIVE_STATE_DIR / "paper_live_history.csv"
SNAPSHOTS_FILE = LIVE_STATE_DIR / "paper_live_snapshots.csv"
DAILY_FILE = LIVE_STATE_DIR / "paper_live_daily.csv"


app = FastAPI(
    title="AL TRADING AGENT API",
    version="1.0.0",
    description="Read-only API for the AL TRADING AGENT dashboard.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
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
    state_file = state_file_for(symbol)

    if not state_file.exists():
        return {
            "available": False,
            "symbol": symbol.upper(),
            "error": f"State file not found: {state_file}",
        }

    try:
        with state_file.open("r", encoding="utf-8") as handle:
            state = json.load(handle)

        state["available"] = True
        state["symbol"] = symbol.upper()
        return state

    except (OSError, json.JSONDecodeError) as exc:
        return {
            "available": False,
            "symbol": symbol.upper(),
            "error": str(exc),
        }


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


def normalize_trade(trade: dict[str, Any], index: int) -> dict[str, Any]:
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
        "fee": float(trade["fee"]),
        "profit": float(trade["profit"]),
    }


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "name": "AL TRADING AGENT API",
        "version": "1.0.0",
        "status": "online",
        "read_only": True,
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

    wins = [
        trade for trade in trades
        if float(trade.get("profit", 0.0)) > 0
    ]
    losses = [
        trade for trade in trades
        if float(trade.get("profit", 0.0)) < 0
    ]

    gross_profit = sum(float(trade["profit"]) for trade in wins)
    gross_loss = abs(sum(float(trade["profit"]) for trade in losses))

    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else None
    )

    win_rate = (
        (len(wins) / len(trades)) * 100.0
        if trades
        else 0.0
    )

    expectancy = (
        net_profit / len(trades)
        if trades
        else 0.0
    )

    return {
        "available": True,
        "strategy": {
            "symbol": asset.symbol,
            "asset_name": asset.name,
            "asset_type": asset.asset_type,
            "provider": asset.provider,
            "quote": asset.quote,
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
            "last_processed_timestamp": state.get(
                "last_processed_timestamp"
            ),
        },
        "position": position_payload(state),
        "account": {
            "position": (
                state.get("position", {}).get("side")
                if state.get("position")
                else "FLAT"
            ),
            "position_candles": int(state.get("position_candles", 0)),
            "balance": balance,
            "initial_balance": initial_balance,
            "net_profit": net_profit,
            "peak_balance": float(state.get("peak_balance", 0.0)),
            "max_drawdown": float(state.get("max_drawdown", 0.0)),
            "market_price": float(state.get("market_price", 0.0)),
            "daily_loss": float(
                (state.get("risk_guard") or {}).get(
                    "daily_loss",
                    0.0,
                )
            ),
        },
        "performance": {
            "trades": len(trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "avg_win": (
                gross_profit / len(wins)
                if wins
                else 0.0
            ),
            "avg_loss": (
                gross_loss / len(losses)
                if losses
                else 0.0
            ),
            "expectancy": expectancy,
        },
    }


@app.get("/api/trades")
def trades(symbol: str = "BTCUSDT") -> list[dict[str, Any]]:
    asset = asset_or_error(symbol)
    state = load_state(asset.symbol)

    if not state.get("available"):
        return []

    raw_trades = state.get("trade_manager_history") or []

    return [
        normalize_trade(trade, index)
        for index, trade in enumerate(raw_trades, start=1)
    ]


@app.get("/api/equity")
def equity(symbol: str = "BTCUSDT") -> dict[str, Any]:
    asset = asset_or_error(symbol)
    state = load_state(asset.symbol)

    if not state.get("available"):
        return {
            "available": False,
            "points": [],
        }

    curve = state.get("equity_curve") or []

    return {
        "available": True,
        "points": [
            {
                "index": index,
                "balance": float(value),
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

        with DAILY_FILE.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
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
                    "profit_factor": float(
                        row.get("ProfitFactor", 0.0)
                    ),
                    "avg_win": float(row.get("AvgWin", 0.0)),
                    "avg_loss": float(row.get("AvgLoss", 0.0)),
                    "expectancy": float(
                        row.get("Expectancy", 0.0)
                    ),
                    "max_drawdown": float(
                        row.get("MaxDrawdown", 0.0)
                    ),
                    "position": row.get("Position"),
                    "market_price": float(
                        row.get("MarketPrice", 0.0)
                    ),
                }
            )
        except (TypeError, ValueError):
            continue

    return result


# Short-lived per-symbol cache prevents the dashboard from requesting a public
# provider on every refresh.
MARKET_CACHE: dict[str, dict[str, Any]] = {}


def load_market_candles(
    symbol: str = "BTCUSDT",
    limit: int = 120,
) -> dict[str, Any]:
    import time

    asset = asset_or_error(symbol)
    cache = MARKET_CACHE.setdefault(
        asset.symbol,
        {"timestamp": 0.0, "points": []},
    )
    now = time.time()

    if cache["points"] and now - cache["timestamp"] < 5.0:
        return {
            "available": True,
            "symbol": asset.symbol,
            "interval": "1m",
            "points": cache["points"],
            "cached": True,
        }

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

        return {
            "available": True,
            "symbol": asset.symbol,
            "interval": "1m",
            "points": points,
            "cached": False,
        }

    except Exception as exc:
        if cache["points"]:
            return {
                "available": True,
                "symbol": asset.symbol,
                "interval": "1m",
                "points": cache["points"],
                "cached": True,
                "stale": True,
                "error": str(exc),
            }

        return {
            "available": False,
            "symbol": asset.symbol,
            "interval": "1m",
            "points": [],
            "error": str(exc),
        }


@app.get("/api/assets")
def assets() -> list[dict[str, Any]]:
    result = []

    for asset in SUPPORTED_ASSETS:
        state = load_state(asset.symbol)
        result.append(
            {
                **asset_payload(asset),
                "state_available": state.get("available", False),
                "market_price": float(state.get("market_price", 0.0)),
                "position": (
                    state.get("position", {}).get("side")
                    if state.get("position")
                    else "FLAT"
                ),
            }
        )

    return result


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

