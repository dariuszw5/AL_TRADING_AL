from src.agent.agent_loop import AgentLoop
from src.agent.agent_config import AgentConfig


def test_provider_exception():
    loop = AgentLoop(
        config=AgentConfig(),
        state_file=None
    )

    def failing_provider(**kwargs):
        raise RuntimeError("simulated API failure")

    loop.data_provider.get_candles = failing_provider

    result = loop.run_live_once()

    if result["status"] != "API_ERROR":
        raise AssertionError(
            f"Expected API_ERROR, got {result['status']}"
        )

    if result["signal"] != "HOLD":
        raise AssertionError(
            f"Expected HOLD, got {result['signal']}"
        )

    if result["result"] is not None:
        raise AssertionError(
            "Expected result=None during API failure."
        )

    print("API EXCEPTION HANDLING       : PASS")


if __name__ == "__main__":
    print("=" * 100)
    print("LIVE API EXCEPTION HANDLING AUDIT")
    print("=" * 100)

    test_provider_exception()

    print("-" * 100)
    print("RESULT: PASS")
    print("=" * 100)
