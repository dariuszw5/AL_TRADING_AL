import json

from fastapi.testclient import TestClient

from app.backend import main
from src.data.candle import Candle
from src.data.fx_provider import PlnRate


def fake_rate(currency):
    return PlnRate(
        source_currency=currency,
        rate_to_pln=4.0 if currency == "USD" else 3.8,
        path="USD→PLN" if currency == "USD" else "USDT→USD→PLN",
        providers=("TEST",),
        quality="TEST",
        observed_at_unix=1.0,
    )


def test_assets_endpoint_matches_supported_registry(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "LIVE_STATE_DIR", tmp_path)
    monkeypatch.setattr(main.FX_PROVIDER, "quote_to_pln", fake_rate)
    client = TestClient(main.app)

    response = client.get("/api/assets")
    assert response.status_code == 200
    payload = response.json()
    symbols = {row["symbol"] for row in payload}
    assert symbols == {
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "BNBUSDT",
        "XRPUSDT",
        "GOLD_FUT_CONT",
        "WTI_FUT_CONT",
        "EURUSD",
        "AAPL",
    }
    gold = next(row for row in payload if row["symbol"] == "GOLD_FUT_CONT")
    assert gold["provider_symbol"] == "GC=F"
    assert gold["instrument_type"] == "continuous_future_proxy"


def test_market_endpoint_reports_provider_freshness_and_pln(monkeypatch):
    now_ms = 1_800_000_000_000
    candles = [
        Candle(now_ms - 120_000, 100, 101, 99, 100.5, 10),
        Candle(now_ms - 60_000, 100.5, 102, 100, 101.0, 12),
    ]
    monkeypatch.setattr(main.time, "time", lambda: now_ms / 1000)
    monkeypatch.setattr(main.FX_PROVIDER, "quote_to_pln", fake_rate)
    monkeypatch.setattr(
        main.DataProvider,
        "get_candles",
        lambda self, symbol, interval, limit: candles,
    )
    main.MARKET_CACHE.clear()

    result = main.market("BTCUSDT")
    assert result["available"] is True
    assert result["provider"] == "binance"
    assert result["quote_currency"] == "USDT"
    assert result["age_seconds"] == 60.0
    assert result["stale"] is False
    assert result["last_close_pln"] == 101.0 * 3.8


def test_legacy_gold_alias_resolves_to_canonical_state(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "LIVE_STATE_DIR", tmp_path)
    monkeypatch.setattr(main.FX_PROVIDER, "quote_to_pln", fake_rate)
    state = {
        "version": 3,
        "balance": 1000,
        "peak_balance": 1000,
        "max_drawdown": 0,
        "market_price": 2500,
        "position_candles": 0,
        "position": None,
        "trade_manager_history": [],
        "risk_guard": {"daily_loss": 0},
        "equity_curve": [1000],
    }
    (tmp_path / "paper_live_GOLD_FUT_CONT_1m.json").write_text(
        json.dumps(state), encoding="utf-8"
    )

    result = main.status("XAUUSD")
    assert result["strategy"]["symbol"] == "GOLD_FUT_CONT"
    assert result["strategy"]["provider_symbol"] == "GC=F"
    assert result["account"]["market_price_pln"] == 10_000.0


def test_dashboard_snapshot_returns_critical_local_state(monkeypatch):
    monkeypatch.setattr(
        main,
        "load_research_state",
        lambda: {"available": True, "opportunities": [{"symbol": "BTCUSDT"}]},
    )
    monkeypatch.setattr(
        main,
        "ai_status",
        lambda: {"available": True, "decision": {"action": "CASH"}, "equity": 976.83},
    )
    monkeypatch.setattr(
        main,
        "user_portfolio_state",
        lambda: {"available": True, "balance": 12.34},
    )

    client = TestClient(main.app)
    response = client.get("/api/dashboard-snapshot")

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["research"]["opportunities"][0]["symbol"] == "BTCUSDT"
    assert payload["ai"]["decision"]["action"] == "CASH"
    assert payload["ai"]["equity"] == 976.83
    assert payload["user_portfolio"]["balance"] == 12.34
