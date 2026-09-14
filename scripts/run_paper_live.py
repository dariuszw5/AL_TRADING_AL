from time import sleep

from src.agent.shadow_research import ShadowResearchRunner
from src.data.assets import SUPPORTED_ASSETS


runner = ShadowResearchRunner()

print()
print("=" * 100)
print("AL TRADING AGENT | RESEARCH-ONLY MARKET OBSERVATION")
print("=" * 100)
print()
print("REAL MARKET DATA - NO PAPER ORDERS - NO REAL ORDERS")
print("Execution enabled: False")
print("Assets:")

for asset in SUPPORTED_ASSETS:
    print(
        f"- {asset.symbol:<8} {asset.name:<18} "
        f"({asset.asset_type}, {asset.provider})"
    )

print("=" * 100)

while True:
    state = runner.run_once()
    ready = sum(
        result.get("recommendation") == "OBSERVE_SIGNAL"
        for result in state["assets"].values()
    )
    print(
        f"RESEARCH CYCLE {state['last_cycle']} | "
        f"assets={len(state['assets'])} observe_signals={ready} | NO EXECUTION",
        flush=True,
    )

    # One-minute candles do not need a tight polling loop, and this keeps
    # requests to the public providers within a modest rate.
    sleep(60)
