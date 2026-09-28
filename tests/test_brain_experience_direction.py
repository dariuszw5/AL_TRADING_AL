from src.agent.ai_manager import net_return
from src.research.experience import ExperienceMemory


def _experience(memory, *, side, index, exit_price):
    stamp = 1_800_000_000_000 + index * 2_000_000
    memory.observe(
        symbol="BTCUSDT",
        timestamp=stamp,
        close=100.0,
        features=[1.0, 0.5, 0.1, -0.2],
        strategy="trend",
        side=side,
        macro_tags=[],
        model_score=0.002,
    )
    return memory.resolve({
        "BTCUSDT": (stamp + memory.horizon_ms, exit_price)
    })


def test_short_experience_recognizes_downward_move_after_costs(tmp_path):
    memory = ExperienceMemory(tmp_path)
    for index in range(6):
        assert _experience(memory, side="SHORT", index=index, exit_price=99.0) == 1

    result = memory.adjustment(
        features=[1.0, 0.5, 0.1, -0.2],
        strategy="trend",
        side="SHORT",
        macro_tags=[],
    )
    assert result.samples == 6
    assert result.mean_return == net_return(100.0, 99.0, "SHORT")
    assert result.adjustment > 0.0


def test_long_does_not_reuse_short_experiences(tmp_path):
    memory = ExperienceMemory(tmp_path)
    for index in range(6):
        _experience(memory, side="SHORT", index=index, exit_price=99.0)

    result = memory.adjustment(
        features=[1.0, 0.5, 0.1, -0.2],
        strategy="trend",
        side="LONG",
        macro_tags=[],
    )
    assert result.samples == 0
    assert result.adjustment == 0.0


def test_directionless_v1_logs_cannot_pollute_v2_memory(tmp_path):
    memory = ExperienceMemory(tmp_path)
    memory.resolved.append({
        "event_type": "RESOLVED_EXPERIENCE",
        "symbol": "BTCUSDT",
        "strategy": "trend",
        "features": [1.0, 0.5, 0.1, -0.2],
        "macro_tags": [],
        "realized_forward_return": 0.50,
    })
    result = memory.adjustment(
        features=[1.0, 0.5, 0.1, -0.2],
        strategy="trend",
        side="SHORT",
        macro_tags=[],
    )
    assert result.samples == 0


def test_long_and_short_same_candle_are_distinct_experiences(tmp_path):
    memory = ExperienceMemory(tmp_path)
    common = dict(
        symbol="BTCUSDT",
        timestamp=1_800_000_000_000,
        close=100.0,
        features=[0.0, 1.0, 0.0, -1.0],
        strategy="trend",
        macro_tags=[],
        model_score=0.002,
    )
    memory.observe(**common, side="LONG")
    memory.observe(**common, side="SHORT")
    assert len(memory.pending["items"]) == 2
    assert memory.resolve({
        "BTCUSDT": (common["timestamp"] + memory.horizon_ms, 99.0)
    }) == 2
    resolved = memory.resolved.read_recent(limit=2)
    by_side = {row["side"]: row["realized_forward_return"] for row in resolved}
    assert by_side["SHORT"] > 0
    assert by_side["LONG"] < 0
