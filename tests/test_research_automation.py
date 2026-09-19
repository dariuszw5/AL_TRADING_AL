from pathlib import Path

from src.data.assets import RESEARCH_ASSETS, dynamic_binance_asset, get_asset
from src.research.experience import ExperienceMemory
from src.research.market_scanner import OpportunityScanner
from src.research.autonomous_agent import AutonomousResearchAgent


def test_dynamic_binance_assets_are_transient_and_valid():
    asset = dynamic_binance_asset("adausdt")
    assert asset.symbol == "ADAUSDT"
    assert asset.provider == "binance"
    assert asset.quote == "USDT"
    assert get_asset("ADAUSDT", allow_dynamic_binance=True).symbol == "ADAUSDT"


def test_research_universe_spans_multiple_market_classes():
    classes = {asset.asset_type for asset in RESEARCH_ASSETS}
    assert {"equity", "etf", "forex", "index", "commodity"} <= classes
    assert get_asset("MSFT").provider == "yahoo"
    assert get_asset("GBPUSD").provider_symbol == "GBPUSD=X"
    assert get_asset("SILVER_FUT_CONT").provider_symbol == "SI=F"


def test_balanced_top_prevents_one_class_from_dominating(tmp_path):
    scanner = OpportunityScanner(tmp_path)
    scanner.top_n = 10
    scanner.class_cap = 3

    rows = []
    for index in range(12):
        rows.append({
            "symbol": f"C{index}USDT",
            "asset_class": "crypto",
            "combined_score": 1.0 - index * 0.01,
            "validation_trades": 20,
            "eligible": True,
        })
    for asset_class in ("equity", "etf", "forex", "index", "commodity"):
        for index in range(3):
            rows.append({
                "symbol": f"{asset_class}_{index}",
                "asset_class": asset_class,
                "combined_score": 0.2 - index * 0.01,
                "validation_trades": 10,
                "eligible": True,
            })

    top = scanner._balanced_top(rows)
    classes = [row["asset_class"] for row in top]

    assert len(top) == 10
    assert classes.count("crypto") <= 3
    assert {"crypto", "equity", "etf", "forex", "index", "commodity"} <= set(classes)


def test_balanced_top_can_fallback_when_only_one_class_is_live(tmp_path):
    scanner = OpportunityScanner(tmp_path)
    scanner.top_n = 10
    scanner.class_cap = 3
    rows = [
        {
            "symbol": f"C{index}USDT",
            "asset_class": "crypto",
            "combined_score": 1.0 - index * 0.01,
            "validation_trades": 20,
            "eligible": True,
        }
        for index in range(12)
    ]
    top = scanner._balanced_top(rows)
    assert len(top) == 10
    assert all(row["asset_class"] == "crypto" for row in top)


def test_experience_memory_learns_only_after_horizon(tmp_path):
    memory = ExperienceMemory(tmp_path, horizon_minutes=10)
    memory.observe(
        symbol="BTCUSDT",
        timestamp=1_000_000,
        close=100.0,
        features=[1.0, 0.5, 0.1, -0.2],
        strategy="trend",
        macro_tags=["fed", "rates"],
        model_score=0.01,
    )
    assert memory.resolve({"BTCUSDT": (1_000_000 + 9 * 60_000, 102.0)}) == 0
    assert memory.resolve({"BTCUSDT": (1_000_000 + 10 * 60_000, 102.0)}) == 1

    for i in range(5):
        memory.observe(
            symbol="BTCUSDT",
            timestamp=2_000_000 + i * 700_000,
            close=100.0,
            features=[1.0 + i * 0.01, 0.5, 0.1, -0.2],
            strategy="trend",
            macro_tags=["fed", "rates"],
            model_score=0.01,
        )
        memory.resolve({
            "BTCUSDT": (
                2_000_000 + i * 700_000 + 10 * 60_000,
                101.0,
            )
        })
    adjustment = memory.adjustment(
        features=[1.0, 0.5, 0.1, -0.2],
        strategy="trend",
        macro_tags=["fed", "rates"],
    )
    assert adjustment.samples >= 5
    assert 0 < adjustment.adjustment <= 0.01


def test_scanner_discovers_and_orders_real_universe_shape(tmp_path, monkeypatch):
    scanner = OpportunityScanner(tmp_path)

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return [
                {
                    "symbol": "AAAUSDT",
                    "lastPrice": "10",
                    "priceChangePercent": "5",
                    "highPrice": "11",
                    "lowPrice": "9",
                    "quoteVolume": "50000000",
                },
                {
                    "symbol": "BBBUSDT",
                    "lastPrice": "20",
                    "priceChangePercent": "2",
                    "highPrice": "21",
                    "lowPrice": "19",
                    "quoteVolume": "80000000",
                },
                {
                    "symbol": "LOWUSDT",
                    "lastPrice": "1",
                    "priceChangePercent": "50",
                    "highPrice": "2",
                    "lowPrice": "0.5",
                    "quoteVolume": "1000",
                },
                {
                    "symbol": "BTCBTC",
                    "lastPrice": "1",
                    "priceChangePercent": "1",
                    "highPrice": "1.1",
                    "lowPrice": "0.9",
                    "quoteVolume": "999999999",
                },
            ]

    monkeypatch.setattr(
        "src.research.market_scanner.requests.get",
        lambda *a, **k: Response(),
    )
    rows = scanner.discover()
    assert {row.symbol for row in rows} == {"AAAUSDT", "BBBUSDT"}
    assert rows[0].market_score >= rows[1].market_score


def test_autonomous_agent_keeps_real_orders_disabled(tmp_path, monkeypatch):
    agent = AutonomousResearchAgent(tmp_path)
    monkeypatch.setattr(agent.macro, "collect", lambda: [])
    monkeypatch.setattr(agent.macro, "recent_tags", lambda: ["fed"])
    monkeypatch.setattr(agent.macro, "recent", lambda limit=30: [])
    monkeypatch.setattr(
        agent.scanner,
        "scan",
        lambda tags: {
            "universe_count": 100,
            "preselected_count": 30,
            "selected_by_class": {"crypto": 2, "equity": 2},
            "opportunities": [
                {
                    "symbol": "BTCUSDT",
                    "strategy": "trend",
                    "combined_score": 0.02,
                }
            ],
        },
    )
    monkeypatch.setattr(
        agent.ai,
        "run_once",
        lambda: {"mode": "PAPER_ONLY", "equity": 1000},
    )
    state = agent.run_once()
    assert state["paper_only"] is True
    assert state["real_orders"] is False
    assert state["universe_count"] == 100
    assert state["selected_by_class"] == {"crypto": 2, "equity": 2}
    assert state["opportunities"][0]["symbol"] == "BTCUSDT"
    assert (Path(tmp_path) / "research_state.json").exists()
