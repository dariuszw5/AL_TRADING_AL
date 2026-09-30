"""Offline Phase 9B+ development runner. TEST and OUTER HOLDOUT stay sealed."""
from __future__ import annotations
import argparse, json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from src.data.candle import Candle
from src.research.brain_v36.costs import cost_for_symbol
from src.research.brain_v36.engine import features as brain_features
from src.research.brain_v36.phase9b import (
    STRATEGIES, KnnSample, ShadowCostModel, ShadowDecision, US_EQUITY_SESSION,
    conservative_outcome, knn_prediction, shadow_decision, strategy_signal,
)


def _load(path: Path):
    raw=json.loads(path.read_text(encoding="utf-8-sig"))
    return [Candle(timestamp=int(x["timestamp"]), open=float(x["open"]), high=float(x["high"]),
                   low=float(x["low"]), close=float(x["close"]), volume=float(x.get("volume",0) or 0)) for x in raw]


def _profiles(path: Path):
    raw=json.loads(path.read_text(encoding="utf-8-sig"))
    return raw.get("profiles", raw)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--costs", default="config/brain_v36_costs.multiasset_SCENARIO.json")
    p.add_argument("--reserve-internal-test", type=int, default=160)
    p.add_argument("--reserve-outer-holdout", type=int, default=160)
    p.add_argument("--equity", type=float, default=1000.0)
    p.add_argument("--overnight-financing-per-day", type=float, default=0.0,
                   help="Explicit research fraction/day; default 0.0, never inferred from provider OHLC")
    p.add_argument("--out", default="diagnostics/brain_v36/phase9b")
    a=p.parse_args()
    manifest=json.loads(Path(a.manifest).read_text(encoding="utf-8-sig"))
    profiles=_profiles(Path(a.costs))
    rows=[]
    bar_minutes=int(manifest.get("bar_minutes",5))
    for item in manifest.get("instruments",[]):
        if item.get("status") != "FROZEN": continue
        path=Path(item["path"])
        if not path.is_file():
            rows.append({"symbol":item["symbol"],"status":"SNAPSHOT_MISSING"}); continue
        bars=_load(path)
        reserve=a.reserve_internal_test+a.reserve_outer_holdout
        if len(bars) <= reserve+220:
            rows.append({"symbol":item["symbol"],"status":"INSUFFICIENT_DEVELOPMENT_HISTORY"}); continue
        visible=bars[:-reserve]
        base_cost, meta=cost_for_symbol(item["symbol"], profiles)
        cost=ShadowCostModel(base_cost.commission_per_side, base_cost.spread_round_trip,
                             base_cost.slippage_per_side, a.overnight_financing_per_day,
                             base_cost.source)
        session=None if item.get("asset_type")=="crypto" else US_EQUITY_SESSION if item.get("asset_type") in {"equity","etf","index"} else None
        for strategy in STRATEGIES:
            samples=[]; pending=[]; decisions=outcomes=knn_rejected=0; net=[]
            for i in range(201, len(visible)-13):
                if pending:
                    matured=[x for x in pending if x.exit_index < i]
                    if matured:
                        samples.extend(matured)
                        pending=[x for x in pending if x.exit_index >= i]
                raw_sig=strategy_signal(strategy, visible, i, bar_minutes)
                if raw_sig is None:
                    continue
                try:
                    x=tuple(float(v) for v in brain_features(visible, i))
                except ValueError:
                    continue
                pred=knn_prediction(x, samples)
                d=shadow_decision(symbol=item["symbol"],asset_type=item.get("asset_type","unknown"),candles=visible,i=i,
                                  strategy=strategy,cost=cost,bar_minutes=bar_minutes,session=session,equity=a.equity,
                                  knn=pred,require_knn=True)
                if d.rejection_reason in {"KNN_INSUFFICIENT_HISTORY","KNN_REJECTED","KNN_NOT_AVAILABLE"}:
                    knn_rejected += 1
                if d.action == "SHADOW_DECISION":
                    decisions+=1
                    o=conservative_outcome(visible,d,cost=cost,bar_minutes=bar_minutes,max_holding_bars=12)
                    if o:
                        outcomes+=1; net.append(o["net_return"])
                raw_d=ShadowDecision("SHADOW_DECISION", item["symbol"], strategy, raw_sig["side"], i,
                                     visible[i].timestamp, "TRAINING_RAW", "N/A", cost.round_trip,
                                     raw_sig["rationale"], None, raw_sig["signal_price"], raw_sig["stop"], raw_sig["target"], 0.0)
                raw_o=conservative_outcome(visible,raw_d,cost=cost,bar_minutes=bar_minutes,max_holding_bars=12)
                if raw_o:
                    pending.append(KnnSample(x, raw_o["net_return"], raw_o["exit_index"]))
            rows.append({"symbol":item["symbol"],"asset_type":item.get("asset_type"),"strategy":strategy,
                         "status":"DEVELOPMENT_ONLY_COMPLETED","shadow_decisions":decisions,"priced_outcomes":outcomes,
                         "knn_rejected":knn_rejected,"knn_training_samples":len(samples),
                         "mean_net_return":mean(net) if net else None,
                         "cost_source":cost.source,"round_trip_cost":cost.round_trip,
                         "reference_only":meta.get("reference_only",False),
                         "internal_test":"NOT_EVALUATED","outer_holdout":"NOT_PASSED_TO_EVALUATOR"})
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    target=out/"phase9b_development_report.json"
    target.write_text(json.dumps({"mode":"RESEARCH_ONLY","pipeline":"REGIME->SESSION/LIQUIDITY/EVENT->STRATEGY->KNN->COST->RISK->SHADOW_DECISION",
                                  "rows":rows,"internal_test":"NOT_EVALUATED",
                                  "outer_holdout":"NOT_PASSED_TO_EVALUATOR"},indent=2),encoding="utf-8")
    print(f"REPORT={target.resolve()}")
    print("PHASE9B DEVELOPMENT COMPLETE; TEST/HOLDOUT SEALED; NO ORDERS")

if __name__ == "__main__": main()
