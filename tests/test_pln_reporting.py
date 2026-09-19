import json

import pytest

from app.backend import main
from src.data.assets import get_asset
from src.data.fx_provider import FxRateProvider, PlnRate


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_usdt_to_pln_uses_real_two_leg_path(monkeypatch):
    def fake_get(url, **kwargs):
        if "coinbase" in url:
            return FakeResponse({"price": "0.95"})
        if "nbp.pl" in url:
            return FakeResponse(
                {"rates": [{"mid": 4.0, "effectiveDate": "2026-09-19"}]}
            )
        raise AssertionError(url)

    monkeypatch.setattr("requests.get", fake_get)
    provider = FxRateProvider(ttl_seconds=60)
    rate = provider.quote_to_pln("USDT")

    assert rate.path == "USDT→USD→PLN"
    assert rate.rate_to_pln == pytest.approx(3.8)
    assert rate.rate_to_pln != 4.0
    assert rate.providers == ("COINBASE_EXCHANGE", "NBP_TABLE_A")


def test_usd_to_pln_uses_nbp_reference(monkeypatch):
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FakeResponse(
            {"rates": [{"mid": 3.91, "effectiveDate": "2026-09-19"}]}
        ),
    )
    provider = FxRateProvider()
    rate = provider.quote_to_pln("USD")
    assert rate.rate_to_pln == pytest.approx(3.91)
    assert rate.quality == "DAILY_REFERENCE"


def test_no_unknown_currency_fallback():
    with pytest.raises(ValueError, match="No real PLN conversion path"):
        FxRateProvider().quote_to_pln("XYZ")


def test_backend_status_reports_native_and_pln_without_changing_state(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(main, "LIVE_STATE_DIR", tmp_path)
    monkeypatch.setattr(
        main.FX_PROVIDER,
        "quote_to_pln",
        lambda currency: PlnRate(
            source_currency=currency,
            rate_to_pln=4.0,
            path="USDT→USD→PLN",
            providers=("TEST_REAL_PATH",),
            quality="TEST",
            observed_at_unix=1.0,
        ),
    )

    state = {
        "version": 3,
        "balance": 1010.0,
        "peak_balance": 1020.0,
        "max_drawdown": 5.0,
        "market_price": 100.0,
        "position_candles": 2,
        "position": {
            "side": "BUY",
            "entry_price": 90.0,
            "quantity": 2.0,
            "stop_loss": 85.0,
            "take_profit": 110.0,
            "entry_timestamp": 1,
        },
        "trade_manager_history": [],
        "risk_guard": {"daily_loss": 0.0},
        "equity_curve": [1000.0, 1010.0],
    }
    path = tmp_path / "paper_live_BTCUSDT_1m.json"
    path.write_text(json.dumps(state), encoding="utf-8")

    result = main.status("BTCUSDT")

    assert result["account"]["balance"] == 1010.0
    assert result["account"]["balance_pln"] == 4040.0
    assert result["account"]["net_profit"] == 10.0
    assert result["account"]["net_profit_pln"] == 40.0
    assert result["account"]["unrealized_profit"] == 20.0
    assert result["account"]["unrealized_profit_pln"] == 80.0
    assert result["pln"]["reporting_only"] is True
    assert json.loads(path.read_text(encoding="utf-8")) == state


def test_gold_and_wti_are_named_as_futures_proxies():
    gold = get_asset("XAUUSD")
    wti = get_asset("WTIUSD")
    assert gold.symbol == "GOLD_FUT_CONT"
    assert gold.provider_symbol == "GC=F"
    assert gold.instrument_type == "continuous_future_proxy"
    assert wti.symbol == "WTI_FUT_CONT"
    assert wti.provider_symbol == "CL=F"
