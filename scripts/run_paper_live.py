from time import sleep

from src.agent.multi_asset_runner import MultiAssetPaperLive
from src.data.assets import SUPPORTED_ASSETS
from src.agent.ai_manager import AIPaperManager


runner = MultiAssetPaperLive()
ai_manager = AIPaperManager('data/live_state/ai_paper.json')

print()
print("=" * 100)
print("AL TRADING AGENT | MULTI-ASSET PAPER-LIVE")
print("=" * 100)
print()
print("PAPER TRADING ONLY - NO REAL ORDERS")
print("Assets:")

for asset in SUPPORTED_ASSETS:
    print(
        f"- {asset.asset_id:<14} {asset.display_name:<32} "
        f"({asset.asset_type}, {asset.provider})"
    )

print()
print("Each asset has an isolated balance and state file.")
print("Waiting for the next closed candle...")
print("=" * 100)

while True:
    results = runner.run_once()
    try:
        ai_state = ai_manager.run_once()
        print('AI PAPER:', ai_state['decision'], flush=True)
    except Exception as exc:
        # Do not execute another AI decision from this failed cycle.
        print(f'AI PAPER cycle failed: {exc}', flush=True)

    for symbol, result in results.items():
        print(
            f"{symbol:<8} status={result.get('status'):<20} "
            f"signal={result.get('signal')} "
            f"position={result.get('position')}"
        )

        if result.get("error"):
            print(f"{symbol:<8} API error: {result['error']}")

    # One-minute candles do not need a tight polling loop, and this keeps
    # requests to the public providers within a modest rate.
    sleep(60)
