import os
from time import sleep

from src.agent.multi_asset_runner import MultiAssetPaperLive
from src.data.assets import SUPPORTED_ASSETS


runner = MultiAssetPaperLive()

# The optional experimental AI module is deliberately NOT part of the core
# paper-live path. Enable it explicitly if you want to run that experiment.
ai_manager = None
if os.getenv("AL_TRADING_ENABLE_AI", "0") == "1":
    from src.agent.ai_manager import AIPaperManager

    ai_manager = AIPaperManager("data/live_state/ai_paper.json")

print()
print("=" * 100)
print("AL TRADING AGENT | MULTI-ASSET PAPER-LIVE")
print("=" * 100)
print()
print("REAL MARKET DATA + VIRTUAL MONEY ONLY - NO REAL ORDERS")
print("Assets:")

for asset in SUPPORTED_ASSETS:
    detail = f"{asset.asset_type}, {asset.provider}"
    if asset.instrument_type == "continuous_future_proxy":
        detail += ", futures proxy"
    print(f"- {asset.symbol:<14} {asset.name:<28} ({detail})")

print()
print("Each asset has an isolated virtual balance and state file.")
print("PLN conversion is reporting-only and is served by the API/dashboard.")
print("Optional AI module:", "ON" if ai_manager is not None else "OFF")
print("Waiting for the next closed candle...")
print("=" * 100)

while True:
    results = runner.run_once()

    if ai_manager is not None:
        try:
            ai_state = ai_manager.run_once()
            print("AI PAPER:", ai_state["decision"], flush=True)
        except Exception as exc:
            print(f"AI PAPER cycle failed: {exc}", flush=True)

    for symbol, result in results.items():
        print(
            f"{symbol:<14} status={result.get('status'):<20} "
            f"signal={result.get('signal')} "
            f"position={result.get('position')}"
        )
        if result.get("error"):
            print(f"{symbol:<14} API error: {result['error']}")

    sleep(60)
