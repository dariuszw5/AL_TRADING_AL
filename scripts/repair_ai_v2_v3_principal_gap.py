from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil


BASE = Path("data/live_state")
AI_PATH = BASE / "ai_paper.json"
PORTFOLIO_PATH = BASE / "user_portfolio.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_atomic(path: Path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def accounting_gap(ai):
    expected = (
        float(ai.get("funded_capital") or 0.0)
        + float(ai.get("realized_pnl") or 0.0)
        + float(ai.get("unrealized_pnl") or 0.0)
        - float(ai.get("profit_swept") or 0.0)
    )
    return float(ai.get("equity") or 0.0) - expected


def allocated_principal(ai):
    return sum(
        float(position.get("allocation_pln") or 0.0)
        for position in (ai.get("positions") or {}).values()
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Repair the known v2->v3 open-position principal double-count "
            "without deleting trade history."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the repair. Without this flag the script is dry-run only.",
    )
    args = parser.parse_args()

    ai = load(AI_PATH)
    portfolio = load(PORTFOLIO_PATH)

    gap = accounting_gap(ai)
    transfers = list(ai.get("profit_transfers") or [])
    swept = float(ai.get("profit_swept") or 0.0)
    transfer_total = sum(float(row.get("amount") or 0.0) for row in transfers)
    transfer_ids = {
        str(row.get("id"))
        for row in transfers
        if row.get("id")
    }

    print("=== BEFORE ===")
    print("funded_capital      :", ai.get("funded_capital"))
    print("AI balance          :", ai.get("balance"))
    print("AI equity           :", ai.get("equity"))
    print("realized_pnl        :", ai.get("realized_pnl"))
    print("unrealized_pnl      :", ai.get("unrealized_pnl"))
    print("profit_swept        :", swept)
    print("accounting_gap      :", gap)
    print("wallet balance      :", portfolio.get("balance"))
    print("profit_transferred  :", portfolio.get("profit_transferred"))
    print("transfer events     :", len(transfers))

    checks = {
        "known 250 PLN migration signature": abs(gap - 250.0) <= 0.01,
        "single sweep event": len(transfers) == 1,
        "AI sweep total matches event": abs(swept - transfer_total) <= 0.01,
        "wallet credited same sweep": abs(
            float(portfolio.get("profit_transferred") or 0.0) - swept
        ) <= 0.01,
        "wallet still contains sweep": (
            float(portfolio.get("balance") or 0.0) + 0.01 >= swept
        ),
        "funding ledgers agree": abs(
            float(ai.get("funded_capital") or 0.0)
            - float(ai.get("funding_received") or 0.0)
        ) <= 0.01
        and abs(
            float(ai.get("funded_capital") or 0.0)
            - float(portfolio.get("transferred_to_ai") or 0.0)
        ) <= 0.01,
        "wallet applied sweep id": transfer_ids.issubset(
            set(portfolio.get("applied_ai_profit_ids") or [])
        ),
    }

    print()
    print("=== SAFETY CHECKS ===")
    for name, ok in checks.items():
        print(("[OK]   " if ok else "[FAIL] "), name)

    if not all(checks.values()):
        raise SystemExit(
            "Repair aborted: live state does not match the known migration incident."
        )

    # Reverse the sweep that was generated from the artificial v2->v3
    # principal duplication, then remove the duplicated principal itself.
    ai["balance"] = float(ai.get("balance") or 0.0) + swept - gap
    ai["profit_swept"] = 0.0
    ai["profit_transfers"] = []

    principal = allocated_principal(ai)
    unrealized = sum(
        float(position.get("unrealized_pnl") or 0.0)
        for position in (ai.get("positions") or {}).values()
    )
    ai["unrealized_pnl"] = unrealized
    ai["equity"] = float(ai["balance"]) + principal + unrealized
    ai["peak"] = max(
        float(ai.get("funded_capital") or 0.0),
        float(ai["equity"]),
    )
    ai["accounting_gap"] = accounting_gap(ai)
    ai["accounting_error"] = abs(float(ai["accounting_gap"])) > 0.01
    ai["halted"] = False

    portfolio["balance"] = (
        float(portfolio.get("balance") or 0.0) - swept
    )
    portfolio["profit_transferred"] = max(
        0.0,
        float(portfolio.get("profit_transferred") or 0.0) - swept,
    )
    portfolio["result"] = float(portfolio["profit_transferred"])
    portfolio["profit_transfers"] = [
        row
        for row in (portfolio.get("profit_transfers") or [])
        if str(row.get("id")) not in transfer_ids
    ]
    portfolio["applied_ai_profit_ids"] = [
        event_id
        for event_id in (portfolio.get("applied_ai_profit_ids") or [])
        if str(event_id) not in transfer_ids
    ]

    repair_event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "V2_V3_PRINCIPAL_DOUBLE_COUNT_REPAIR",
        "removed_artificial_principal_pln": gap,
        "reversed_sweep_pln": swept,
        "preserved_trade_history": True,
    }
    ai["accounting_repairs"] = (
        list(ai.get("accounting_repairs") or []) + [repair_event]
    )[-50:]
    portfolio["accounting_repairs"] = (
        list(portfolio.get("accounting_repairs") or []) + [repair_event]
    )[-50:]

    print()
    print("=== AFTER (CALCULATED) ===")
    print("AI balance          :", ai["balance"])
    print("AI equity           :", ai["equity"])
    print("profit_swept        :", ai["profit_swept"])
    print("accounting_gap      :", ai["accounting_gap"])
    print("accounting_error    :", ai["accounting_error"])
    print("wallet balance      :", portfolio["balance"])
    print("profit_transferred  :", portfolio["profit_transferred"])

    if abs(float(ai["accounting_gap"])) > 0.01:
        raise SystemExit("Repair aborted: calculated accounting gap is not zero.")
    if float(portfolio["balance"]) < -0.01:
        raise SystemExit("Repair aborted: wallet would become negative.")

    if not args.apply:
        print()
        print("DRY RUN ONLY. Re-run with --apply to write the repair.")
        return

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ai_backup = AI_PATH.with_name(f"{AI_PATH.name}.bak.{stamp}")
    portfolio_backup = PORTFOLIO_PATH.with_name(
        f"{PORTFOLIO_PATH.name}.bak.{stamp}"
    )
    shutil.copy2(AI_PATH, ai_backup)
    shutil.copy2(PORTFOLIO_PATH, portfolio_backup)

    save_atomic(AI_PATH, ai)
    save_atomic(PORTFOLIO_PATH, portfolio)

    print()
    print("REPAIR APPLIED")
    print("AI backup        :", ai_backup)
    print("Portfolio backup :", portfolio_backup)


if __name__ == "__main__":
    main()
