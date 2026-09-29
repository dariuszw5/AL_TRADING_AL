"""Offline Brain v3.6 evaluation on supplied REAL, frozen candle files.

Example:
python -m scripts.run_brain_v36_research --input BTCUSDT=data/backtest/BTCUSDT_1m_5000.json --costs config/brain_v36_costs.example.json

No API fetching, live-state writing, broker access or optimizer in this command.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from src.data.data_provider import DataProvider
from src.data.historical_data import HistoricalData
from src.research.brain_v36 import RiskPlan, cost_for_symbol, walk_forward

ROOT = Path(__file__).resolve().parents[1]


def _input(text: str) -> tuple[str, Path]:
    if "=" not in text:
        raise ValueError("Use SYMBOL=path/to/frozen_candles.json or .csv")
    symbol, raw_path = text.split("=", 1)
    symbol = symbol.upper().strip()
    path = (ROOT / raw_path.strip()).resolve()
    if not symbol or path.suffix.lower() not in {".json", ".csv"} or not path.is_file():
        raise ValueError(f"Invalid historical input: {text}")
    if path.name in {"ai_paper.json", "trading.db", "ai_control.json"}:
        raise ValueError("Live account/control databases are not research candles")
    return symbol, path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Brain v3.6 frozen RESEARCH_ONLY")
    parser.add_argument("--input", action="append", required=True, metavar="SYMBOL=PATH")
    parser.add_argument("--costs", required=True, type=Path, help="Explicit cost assumptions in JSON")
    parser.add_argument("--horizons", type=int, nargs="+", default=[15, 30, 60])
    parser.add_argument("--initial-train", type=int, default=1200)
    parser.add_argument("--validation-size", type=int, default=400)
    parser.add_argument("--test-size", type=int, default=400)
    parser.add_argument("--output-dir", type=Path, default=Path("diagnostics/brain_v36"))
    args = parser.parse_args(argv)

    diagnostics = (ROOT / "diagnostics").resolve()
    target = (ROOT / args.output_dir).resolve()
    if not target.is_relative_to(diagnostics):
        parser.error("Reports MUST remain inside diagnostics; never write into data/live")
    cost_file = (ROOT / args.costs).resolve()
    profiles = json.loads(cost_file.read_text(encoding="utf-8-sig"))
    if not isinstance(profiles, dict):
        parser.error("Costs must be a JSON map of asset types or symbols")
    if len(args.horizons) != len(set(args.horizons)):
        parser.error("Do not repeat horizons to multiply-check the holdout")

    # Validate ALL inputs and cost assumptions before touching outputs.
    work = []
    for raw in args.input:
        symbol, path = _input(raw)
        costs, asset = cost_for_symbol(symbol, profiles)
        candles = (
            HistoricalData().load_csv(path)
            if path.suffix.lower() == ".csv"
            else DataProvider().load_candles(path)
        )
        work.append((symbol, path, costs, asset, candles))

    reports = []
    summary = []
    for symbol, path, costs, asset, candles in work:
        for horizon in args.horizons:
            risk = RiskPlan(horizon_minutes=horizon)
            result = walk_forward(
                candles,
                symbol=symbol, asset_type=asset["asset_type"],
                instrument_type=asset["instrument_type"], costs=costs, risk=risk,
                initial_train=args.initial_train,
                validation_size=args.validation_size,
                test_size=args.test_size,
            )
            result["dataset"] = str(path)
            reports.append(result)
            for row in result["results"]:
                summary.append({
                    "symbol": symbol,
                    "asset_type": asset["asset_type"],
                    "reference_only": asset["reference_only"],
                    "fold": row["fold"],
                    "strategy": row["strategy"],
                    "side": row["side"],
                    "horizon": horizon,
                    "round_trip_cost": costs.round_trip,
                    "cost_source": costs.source,
                    "train_samples": row["training_samples"],
                    "validation_trades": row["validation"]["trades"],
                    "validation_expectancy": row["validation"]["expectancy_net"],
                    "admitted_before_test": row["admitted_before_test"],
                    "test_trades": row["test"]["trades"] if row["test"] else None,
                    "test_expectancy": row["test"]["expectancy_net"] if row["test"] else None,
                    "test_profit_factor": row["test"]["profit_factor"] if row["test"] else None,
                    "test_max_drawdown": row["test"]["max_drawdown_fraction"] if row["test"] else None,
                })
            print(
                f"{symbol} {horizon}m | folds={len(result['folds'])} | "
                f"admitted={sum(v['admitted_before_test'] for v in result['results'])}/"
                f"{len(result['results'])} | {costs.source}"
            )

    target.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    detail_path = target / f"brain_v36_{stamp}.json"
    summary_path = target / f"brain_v36_{stamp}.csv"
    detail_path.write_text(
        json.dumps({"mode": "RESEARCH_ONLY", "runs": reports}, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    with summary_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)
    print(f"RESEARCH_ONLY_JSON={detail_path}")
    print(f"RESEARCH_ONLY_CSV={summary_path}")
    print("Production and the virtual PLN account were NOT accessed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
