"""Audit saved sealed v3.6 validation, with no fresh data or holdout evaluation.

python -m scripts.audit_brain_v36_costs

Automatically uses only brain_v36_YYYYMMDDTHHMMSSZ.json input reports,
not a prior cost audit. Saves results under diagnostics/brain_v36.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from src.research.brain_v36.cost_audit import analyze_sealed_validation

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "diagnostics" / "brain_v36"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Sealed-validation v3.6 cost audit")
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.report is None:
        candidates = sorted(
            REPORT_DIR.glob("brain_v36_????????T??????Z.json"),
            key=lambda item: item.name,
        )
        if not candidates:
            parser.error("No dated Brain v3.6 JSON report found")
        report_path = candidates[-1]
    else:
        report_path = (ROOT / args.report).resolve()

    if (not report_path.is_relative_to(REPORT_DIR.resolve())
            or not report_path.is_file()
            or not report_path.name.startswith("brain_v36_")):
        parser.error("Only saved Brain v3.6 diagnostics JSON may be read")

    payload_bytes = report_path.read_bytes()
    payload = json.loads(payload_bytes.decode("utf-8-sig"))
    rows = analyze_sealed_validation(payload)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    csv_path = REPORT_DIR / f"v36_cost_audit_{stamp}.csv"
    json_path = REPORT_DIR / f"v36_cost_audit_{stamp}.json"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    audit = {
        "mode": "RESEARCH_ONLY",
        "test_sealed": True,
        "source_report": str(report_path),
        "source_sha256": sha256(payload_bytes).hexdigest(),
        "notes": [
            "The 0.18% example is an UNCALIBRATED historical assumption, not measured executable cost.",
            "Zero-cost gross is a mathematical upper bound, NOT a tradable scenario.",
            "Validation windows overlap across expanding folds. Do not aggregate rows as independent trades.",
            "Filtered and unfiltered sequences have different non-overlap schedules; not a paired performance test.",
            "No TEST trade, PnL, or test statistics were read.",
        ],
        "rows": rows,
    }
    json_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False,
                                    allow_nan=False), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"SOURCE: {report_path.name}")
    print(f"FOLD-STRATEGY-SIDE ROWS: {len(rows)} (overlapping windows NOT independent)")
    for horizon in sorted({row["horizon_minutes"] for row in rows}):
        part = [v for v in rows if v["horizon_minutes"] == horizon]
        sufficient = [v for v in part if v["raw_trades"] >= 4]
        gross_pos = sum(v["raw_mean_gross"] > 0 for v in sufficient)
        net_pos = sum(v["raw_mean_net"] > 0 for v in sufficient)
        cost_only = sum(v["raw_cost_effect"] == "COST_ERASES_GROSS_EDGE"
                        for v in sufficient)
        print(
            f"{horizon}m | raw variants >=4: {len(sufficient)} | "
            f"gross positive: {gross_pos} | net positive: {net_pos} | "
            f"positive gross erased by assumed cost: {cost_only}"
        )
    print("\nRAW VALIDATION ROWS WITH MOST TRADES (net/gross = percentages)")
    for row in sorted(rows, key=lambda x: x["raw_trades"], reverse=True)[:12]:
        gross = row["raw_mean_gross"]
        net = row["raw_mean_net"]
        print(
            f"{row['symbol']:12s} {row['strategy']:15s} {row['side']:5s} "
            f"{row['horizon_minutes']:>2}m fold={row['fold']} n={row['raw_trades']:>2} "
            f"gross={'n/a' if gross is None else f'{gross * 100:+.4f}%':>10} "
            f"net={'n/a' if net is None else f'{net * 100:+.4f}%':>10} "
            f"{row['raw_cost_effect']}"
        )
    print("\nNo TEST performance was inspected; no account, service or orders touched.")
    print(f"JSON={json_path}")
    print(f"CSV={csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
