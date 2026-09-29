"""Catalog-wide real market data collection and sealed validation. NO LIVE ORDERS.

python -m scripts.run_brain_v36_all_assets --api-base-url https://... \
    --costs config/brain_v36_costs.multiasset_SCENARIO.json --bar-minutes 5

Creates frozen per-symbol real OHLC snapshots and an immutable manifest in
diagnostics/brain_v36/multiasset/. All fixed assets plus the current scanner's
dynamic-USDT symbols are accounted for, including failed/unavailable feeds.
Reference-only index, spot-FX and continuous-futures proxies are labeled.
The final N bars of each real dataset are NEVER passed to the evaluator.
Test performance is never evaluated; no production/AI modules are imported.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from time import time
from urllib.parse import urlsplit

import requests

from src.research.brain_v36.costs import cost_for_symbol
from src.research.brain_v36.engine import RiskPlan, walk_forward
from src.research.brain_v36.snapshots import real_candles, snapshot_record, load_snapshot
from src.research.brain_v36.universe import universe, live_crypto_symbols, class_coverage

ROOT = Path(__file__).resolve().parents[1]
OUT = (ROOT / "diagnostics" / "brain_v36" / "multiasset").resolve()
SNAPSHOTS = OUT / "snapshots"


def _api_read(base_url: str) -> tuple[tuple[str, ...], dict]:
    if not base_url.startswith("https://"):
        raise ValueError("Scanner API URL MUST use HTTPS")
    base = base_url.rstrip("/")
    parsed = urlsplit(base)
    if (parsed.scheme != "https" or not parsed.hostname
            or parsed.path or parsed.query or parsed.fragment):
        raise ValueError("Provide the HTTPS API origin, without a path or query")
    response = requests.get(base + "/api/ai", timeout=35)
    response.raise_for_status()
    ai = response.json()
    if not isinstance(ai, dict):
        raise ValueError("AI scanner response must be a JSON object")
    if not isinstance(ai.get("ranking"), list):
        raise ValueError("Missing full AI ranking; dynamic universe cannot be verified")
    research = {}
    try:
        rs = requests.get(base + "/api/research", timeout=35)
        rs.raise_for_status()
        research = rs.json()
    except (requests.RequestException, ValueError):
        # ai.ranking alone still yields all candidates exposed by the AI API.
        research = {}
    if not isinstance(research, dict):
        research = {}
    return live_crypto_symbols(ai, research), {
        "ai_ranking_rows": len(ai.get("ranking") or []),
        "research_opportunities": len(research.get("opportunities") or []),
        "discovery": "LIVE_API_RANKING_AND_AVAILABLE_RESEARCH_OPPORTUNITIES",
    }


def collect(
    *, api_base_url: str, bar_minutes: int, limit: int,
    stamp: str, max_workers: int = 3,
) -> Path:
    started_ms = int(time() * 1000)
    dynamic_failure = None
    discovery = {}
    try:
        dynamic, discovery = _api_read(api_base_url)
    except (requests.RequestException, ValueError, TypeError) as error:
        dynamic, dynamic_failure = (), f"{type(error).__name__}: {error}"
    catalog = universe(dynamic)
    collection_dir = SNAPSHOTS / stamp
    if collection_dir.exists():
        raise FileExistsError(f"Refusing to overwrite snapshot run: {collection_dir}")

    def one(asset):
        try:
            bars = real_candles(
                asset, bar_minutes=bar_minutes, limit=limit,
                as_of_ms=started_ms,
            )
            path = collection_dir / (asset.symbol + f"_{bar_minutes}m.json")
            return snapshot_record(
                asset, bars, path=path, bar_minutes=bar_minutes,
                as_of_ms=started_ms,
            )
        except (requests.RequestException, ValueError, KeyError, TypeError,
                IndexError, OSError, FileExistsError) as error:
            return {
                **asset.as_dict(),
                "status": "DATA_UNAVAILABLE",
                "reason": f"{type(error).__name__}: {str(error)[:320]}",
                "count": 0,
                "bar_minutes": bar_minutes,
                "as_of_ms": started_ms,
            }

    entries = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(one, asset): asset.symbol for asset in catalog}
        for future in as_completed(futures):
            row = future.result()
            entries[row["symbol"]] = row
            print(
                f"DATA {row['asset_type']:10s} {row['symbol']:22s} "
                f"{row['status']:17s} bars={row['count']}"
            )

    manifest = {
        "mode": "RESEARCH_ONLY",
        "source": "actual Binance/Yahoo provider OHLC and current AI scanner ranking",
        "as_of_ms": started_ms,
        "bar_minutes": bar_minutes,
        "requested_limit": limit,
        "dynamic_discovery": {
            **discovery, "status": (
                "COMPLETE_API_READ" if dynamic_failure is None
                else "DYNAMIC_DISCOVERY_FAILED_PARTIAL_UNIVERSE"
            ),
            "error": dynamic_failure,
            "dynamic_symbols": list(dynamic),
        },
        "catalog_class_counts": class_coverage(catalog),
        "instruments": [entries[asset.symbol] for asset in catalog],
        "warning": (
            "Partial feeds are reported, never backfilled. Reference OHLC "
            "is not an executable bid/ask quote. No paper account accessed."
        ),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    location = OUT / f"universe_{stamp}.json"
    with location.open("x", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2, allow_nan=False)
    print(f"MANIFEST={location}")
    return location


def evaluate(
    manifest_path: Path, *, costs_path: Path,
    initial_train: int, validation_size: int, internal_test_size: int,
    outer_holdout: int, horizons: tuple[int, ...],
    stamp: str,
) -> tuple[Path, Path, dict]:
    manifest_path = manifest_path.resolve()
    if not manifest_path.is_relative_to(OUT) or not manifest_path.is_file():
        raise ValueError("Only the isolated multiasset research manifest is accepted")
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8-sig"))
    if manifest.get("mode") != "RESEARCH_ONLY":
        raise ValueError("Not a research universe manifest")
    config = json.loads(costs_path.read_text(encoding="utf-8-sig"))
    if not isinstance(config, dict):
        raise ValueError("Explicit per-class/symbol cost map required")
    if outer_holdout < max(horizons) // manifest["bar_minutes"] + 20:
        raise ValueError("The final reserved OOS block is too short")
    rows = []
    coverage = []
    for entry in manifest["instruments"]:
        info = {k: entry[k] for k in (
            "symbol", "asset_type", "instrument_type",
            "reference_only", "provider", "origin",
        )}
        info.update({
            "data_status": entry["status"], "snapshot_bars": entry["count"],
            "snapshot_session_gaps": entry.get("session_gaps"),
            "data_sha256": entry.get("sha256"),
            "dynamic_discovery_status": manifest["dynamic_discovery"]["status"],
            "evaluation_status": None, "detail": None,
            "sealed_outer_holdout_bars": outer_holdout,
            "assumption_source": None,
            "validated_rows": 0, "admitted_rows": 0,
        })
        if entry["status"] != "FROZEN":
            info["evaluation_status"] = "SKIPPED_DATA_UNAVAILABLE"
            info["detail"] = entry.get("reason")
            coverage.append(info)
            continue
        try:
            candles = load_snapshot(entry, base=SNAPSHOTS)
            profile, metadata = cost_for_symbol(entry["symbol"], config)
            if (metadata["asset_type"] != entry["asset_type"]
                    or metadata["instrument_type"] != entry["instrument_type"]):
                raise ValueError("Snapshot asset metadata differs from cost resolver")
            info["assumption_source"] = profile.source
            for horizon in horizons:
                risk = RiskPlan(
                    horizon_minutes=horizon,
                    bar_minutes=manifest["bar_minutes"],
                )
                required = (
                    initial_train + validation_size + internal_test_size
                    + 2 * risk.horizon_bars + outer_holdout
                )
                if len(candles) < required:
                    raise ValueError(
                        f"Insufficient data for {horizon}m: have {len(candles)}, "
                        f"need >= {required} bars including the reserved outer OOS"
                    )
                # Crucial: reserved final holdout is NOT even passed to the
                # research evaluator. All internal rolling test blocks stay
                # unevaluated (diagnostics-only expanding train/validation).
                development_only = candles[:-outer_holdout]
                report = walk_forward(
                    development_only, symbol=entry["symbol"],
                    asset_type=entry["asset_type"],
                    instrument_type=entry["instrument_type"],
                    costs=profile, risk=risk,
                    initial_train=initial_train,
                    validation_size=validation_size,
                    test_size=internal_test_size,
                    evaluate_test=False,
                )
                if report.get("evaluate_test") is not False or any(
                    r.get("test") is not None or r.get("test_scan") is not None
                    for r in report["results"]
                ):
                    raise AssertionError("Holdout violation: TEST was evaluated")
                for item in report["results"]:
                    rows.append({
                        **{k: info[k] for k in (
                            "symbol", "asset_type", "instrument_type",
                            "reference_only", "provider", "data_sha256",
                        )},
                        "horizon_minutes": horizon,
                        "bar_minutes": manifest["bar_minutes"],
                        "fold": item["fold"],
                        "train_samples": item["training_samples"],
                        "raw_validation_signals": item["unfiltered_validation_scan"]["signals"],
                        "raw_validation_trades": item["unfiltered_validation"]["trades"],
                        "raw_validation_unpriceable_gaps": item["unfiltered_validation_scan"]["unpriceable_gaps"],
                        "raw_validation_mean_net": item["unfiltered_validation"]["expectancy_net"],
                        "filtered_validation_signals": item["validation_scan"]["signals"],
                        "filtered_rejected_nonpositive": item["validation_scan"]["rejected_nonpositive"],
                        "filtered_rejected_uncertainty": item["validation_scan"]["rejected_uncertainty"],
                        "filtered_validation_unpriceable_gaps": item["validation_scan"]["unpriceable_gaps"],
                        "filtered_validation_trades": item["validation"]["trades"],
                        "filtered_validation_mean_net": item["validation"]["expectancy_net"],
                        "admitted_before_test": item["admitted_before_test"],
                        "round_trip_assumption": profile.round_trip,
                        "assumption_source": profile.source,
                        "outer_holdout_status": "RESERVED_NOT_PASSED_TO_EVALUATOR",
                        "test": None,
                    })
                info["validated_rows"] += len(report["results"])
                info["admitted_rows"] += sum(v["admitted_before_test"] for v in report["results"])
            info["evaluation_status"] = "VALIDATION_ONLY_COMPLETED"
        except (ValueError, KeyError, TypeError, IndexError, OSError) as error:
            info["evaluation_status"] = (
                "SKIPPED_INSUFFICIENT_OR_INVALID_HISTORY"
                if "Insufficient data" in str(error) or "contiguous" in str(error)
                else "SKIPPED_COST_OR_DATA_ERROR"
            )
            info["detail"] = f"{type(error).__name__}: {str(error)[:320]}"
            # If some horizons were successful, keep them but mark the asset
            # explicitly PARTIAL, never claim a full 3-horizon evaluation.
            if info["validated_rows"]:
                info["evaluation_status"] = "PARTIAL_HORIZON_COVERAGE"
        coverage.append(info)
        print(
            f"VALIDATE {info['asset_type']:10s} {info['symbol']:22s} "
            f"{info['evaluation_status']:40s} rows={info['validated_rows']}"
        )

    status = Counter(v["evaluation_status"] for v in coverage)
    result = {
        "mode": "RESEARCH_ONLY", "operation": "MULTI_ASSET_SEALED_VALIDATION",
        "source_manifest": str(manifest_path),
        "source_manifest_sha256": sha256(manifest_bytes).hexdigest(),
        "cost_config": str(costs_path.resolve()),
        "bar_minutes": manifest["bar_minutes"],
        "horizons_minutes": list(horizons),
        "split_parameters_bars": {
            "initial_train": initial_train, "validation_size": validation_size,
            "rolling_internal_test_size_unevaluated": internal_test_size,
            "outer_holdout_size_reserved": outer_holdout,
        },
        "outer_holdout": "NOT_PASSED_TO_EVALUATOR",
        "rolling_internal_test": "NOT_EVALUATED",
        "dynamic_discovery": manifest["dynamic_discovery"],
        "coverage_by_class": class_coverage(universe(
            manifest["dynamic_discovery"].get("dynamic_symbols", [])
        )),
        "status_counts": dict(status),
        "instruments": coverage,
        "results": rows,
        "interpretation": (
            "Only VALIDATION diagnostics. Explicit unverified cost scenarios "
            "are not broker quotes. Do not infer realizable returns or treat "
            "overlapping folds as independent. Reference indices, FX spot and "
            "continuous futures cannot be traded directly from these quotes."
        ),
    }
    output = OUT / f"multiasset_v36_{stamp}.json"
    report_csv = OUT / f"multiasset_v36_{stamp}.csv"
    with output.open("x", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2, allow_nan=False)
    fields = [
        "symbol", "asset_type", "instrument_type", "reference_only",
        "provider", "origin", "data_status", "snapshot_bars",
        "snapshot_session_gaps", "data_sha256", "dynamic_discovery_status", "evaluation_status",
        "detail", "sealed_outer_holdout_bars", "assumption_source",
        "validated_rows", "admitted_rows",
    ]
    coverage_csv = OUT / f"multiasset_coverage_{stamp}.csv"
    import csv
    with coverage_csv.open("x", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(coverage)
    if rows:
        with report_csv.open("x", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    else:
        report_csv = None
    print(f"INSTRUMENTS={len(coverage)} VALIDATED_ALL_HORIZONS={status.get('VALIDATION_ONLY_COMPLETED', 0)}")
    print(f"PARTIAL_OR_MISSING={len(coverage) - status.get('VALIDATION_ONLY_COMPLETED', 0)}")
    print(f"DYNAMIC_DISCOVERY={manifest['dynamic_discovery']['status']}")
    for klass in sorted({row["asset_type"] for row in coverage}):
        part = [row for row in coverage if row["asset_type"] == klass]
        full = sum(row["evaluation_status"] == "VALIDATION_ONLY_COMPLETED" for row in part)
        print(f"CLASS {klass:10s} fully-validated={full}/{len(part)} (unverified cost scenario)")
    is_complete = (
        status.get("VALIDATION_ONLY_COMPLETED", 0) == len(coverage)
        and manifest["dynamic_discovery"]["status"] == "COMPLETE_API_READ"
    )
    print(f"COVERAGE_STATUS={'COMPLETE' if is_complete else 'INCOMPLETE_INSPECT_COVERAGE_CSV'}")
    print(f"COVERAGE={coverage_csv}")
    print(f"RESULTS={output}")
    if report_csv:
        print(f"VALIDATION_CSV={report_csv}")
    print("OUTER_HOLDOUT_NOT_PASSED_TO_EVALUATOR; NO ACCOUNT WRITES")
    return output, coverage_csv, result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Research-only ALL asset classes and current dynamic scanner snapshot")
    parser.add_argument("--api-base-url", default=None, help="HTTPS API URL for current dynamic USDT scanner symbols")
    parser.add_argument("--manifest", type=Path, default=None, help="Reuse frozen manifest instead of fetching real quotes")
    parser.add_argument("--costs", type=Path, required=True)
    parser.add_argument("--bar-minutes", type=int, default=5, choices=(1, 5))
    parser.add_argument("--limit", type=int, default=3000)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--initial-train", type=int, default=480)
    parser.add_argument("--validation-size", type=int, default=320)
    parser.add_argument("--internal-test-size", type=int, default=160)
    parser.add_argument("--outer-holdout", type=int, default=160)
    parser.add_argument("--horizons", nargs="+", type=int, default=(15, 30, 60))
    parser.add_argument("--snapshot-only", action="store_true")
    args = parser.parse_args(argv)
    if args.manifest and args.api_base_url:
        parser.error("Choose either existing --manifest or new --api-base-url")
    if not args.manifest and not args.api_base_url:
        parser.error("Current dynamic symbols require --api-base-url, or reuse --manifest")
    if (not 1 <= args.max_workers <= 5 or
            not 100 <= args.limit <= 5000 or
            any(h < 1 or h % args.bar_minutes for h in args.horizons) or
            len(set(args.horizons)) != len(args.horizons)):
        parser.error("Invalid workers/history limit/horizons")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest = (ROOT / args.manifest).resolve() if args.manifest else collect(
        api_base_url=args.api_base_url,
        bar_minutes=args.bar_minutes,
        limit=args.limit,
        stamp=stamp,
        max_workers=args.max_workers,
    )
    if args.snapshot_only:
        print("Snapshot-only: no model/TEST evaluated.")
        return 0
    _, _, report = evaluate(
        manifest, costs_path=(ROOT / args.costs).resolve(),
        initial_train=args.initial_train,
        validation_size=args.validation_size,
        internal_test_size=args.internal_test_size,
        outer_holdout=args.outer_holdout,
        horizons=tuple(args.horizons),
        stamp=stamp,
    )
    # Missing rows are reported explicitly. This is not a claim of complete
    # coverage, and partial availability is not a silent test-pass.
    print("RESEARCH VALIDATION COMPLETE; inspect coverage CSV for unavailable markets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
