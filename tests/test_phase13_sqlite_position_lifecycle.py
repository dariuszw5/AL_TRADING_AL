import pytest

from src.persistence.sqlite_bootstrap import (
    bootstrap_fresh_database,
)
from src.persistence.sqlite_repository import (
    IdempotencyConflictError,
    SQLiteLedgerRepository,
    SQLiteLedgerRepositoryError,
)


NOW = "2026-09-18T22:30:00.000000Z"
NEXT = "2026-09-18T22:31:00.000000Z"


def order_payload(
    *,
    order_id,
    client_order_id,
    side,
    intent,
):
    return {
        "order_id": order_id,
        "client_order_id": client_order_id,
        "asset_id": "BTCUSDT",
        "strategy_id": "PHASE13_A13_TEST",
        "intent": intent,
        "side": side,
        "quantity_native": "1",
        "signal_reference": "PHASE13_A13",
        "source_timestamp_utc": NOW,
        "created_at_utc": NOW,
        "execution_profile": "REALISTIC_V2",
        "paper_mode": "realistic_paper",
        "status": "FILLED",
        "config_hash": "config-a13",
        "order_fingerprint": (
            "fingerprint-" + client_order_id
        ),
        "raw_json": {
            "phase": "13A13",
        },
    }


def execution_payload(
    *,
    execution_id,
    order_id,
    side,
    price,
    timestamp,
):
    return {
        "execution_id": execution_id,
        "order_id": order_id,
        "asset_id": "BTCUSDT",
        "side": side,
        "quantity_native": "1",
        "reference_price_native": price,
        "execution_price_native": price,
        "bid_native": price,
        "ask_native": price,
        "spread_native": "0",
        "slippage_native": "0",
        "fee_native": "0",
        "fee_pln": "0",
        "provider_timestamp_utc": timestamp,
        "execution_timestamp_utc": timestamp,
        "data_quality": "REALTIME_BOOK",
        "execution_quality": "REAL_BOOK",
        "session_quality": "EXCHANGE_CALENDAR",
        "fx_path": "USDT->USD->PLN",
        "fx_rate": "4",
        "fx_provider": "TEST",
        "fx_timestamp_utc": timestamp,
        "fx_quality": "LIVE",
        "config_hash": "config-a13",
        "raw_json": {
            "phase": "13A13",
        },
    }


def open_position_payload():
    return {
        "position_id": "position-a13",
        "asset_id": "BTCUSDT",
        "side": "LONG",
        "quantity_native": "1",
        "entry_execution_id": "execution-entry-a13",
        "exit_execution_id": None,
        "entry_price_native": "100",
        "exit_price_native": None,
        "stop_loss_native": "95",
        "take_profit_native": "110",
        "status": "OPEN",
        "opened_at_utc": NOW,
        "closed_at_utc": None,
        "short_mechanism": None,
        "short_financing_model": None,
        "execution_profile": "REALISTIC_V2",
        "execution_quality_at_entry": "REAL_BOOK",
        "unrealized_pnl_native": "0",
        "unrealized_pnl_pln": "0",
        "raw_json": {
            "phase": "13A13",
            "state": "open",
        },
    }


def closed_position_payload(
    *,
    exit_price="106.25",
):
    result = dict(
        open_position_payload()
    )

    result.update(
        {
            "exit_execution_id": "execution-exit-a13",
            "exit_price_native": exit_price,
            "status": "CLOSED",
            "closed_at_utc": NEXT,
            "unrealized_pnl_native": "0",
            "unrealized_pnl_pln": "0",
            "raw_json": {
                "phase": "13A13",
                "state": "closed",
            },
        }
    )

    return result


def build_repo(
    tmp_path,
    *,
    include_exit_execution=True,
):
    path = tmp_path / "position-lifecycle.db"

    bootstrap_fresh_database(
        path,
        initial_cash_pln="1000",
        bootstrap_id="phase13-a13-test",
        created_at_utc=NOW,
    )

    repo = SQLiteLedgerRepository.open_writer(path)

    with repo.atomic_cycle():
        repo.insert_order_idempotent(
            order_payload(
                order_id="order-entry-a13",
                client_order_id="client-entry-a13",
                side="BUY",
                intent="ENTRY",
            )
        )

        repo.insert_execution_idempotent(
            execution_payload(
                execution_id="execution-entry-a13",
                order_id="order-entry-a13",
                side="BUY",
                price="100",
                timestamp=NOW,
            )
        )

        repo.save_position_idempotent(
            open_position_payload()
        )

        if include_exit_execution:
            repo.insert_order_idempotent(
                order_payload(
                    order_id="order-exit-a13",
                    client_order_id="client-exit-a13",
                    side="SELL",
                    intent="EXIT",
                )
            )

            repo.insert_execution_idempotent(
                execution_payload(
                    execution_id="execution-exit-a13",
                    order_id="order-exit-a13",
                    side="SELL",
                    price="106.25",
                    timestamp=NEXT,
                )
            )

    return repo


def read_position(repo):
    row = repo.connection.execute(
        """
        SELECT *
        FROM positions
        WHERE position_id = ?
        """,
        ("position-a13",),
    ).fetchone()

    if row is None:
        return None

    return dict(row)


def test_close_position_requires_atomic_cycle(tmp_path):
    repo = build_repo(tmp_path)

    try:
        with pytest.raises(
            SQLiteLedgerRepositoryError,
            match="atomic_cycle",
        ):
            repo.close_position_idempotent(
                closed_position_payload()
            )
    finally:
        repo.close()


def test_open_position_can_transition_to_closed(tmp_path):
    repo = build_repo(tmp_path)

    try:
        with repo.atomic_cycle():
            row, changed = (
                repo.close_position_idempotent(
                    closed_position_payload()
                )
            )

        assert changed is True
        assert row["status"] == "CLOSED"
        assert row["exit_execution_id"] == "execution-exit-a13"
        assert row["exit_price_native"] == "106.25"
        assert row["closed_at_utc"] == NEXT

        persisted = read_position(repo)

        assert persisted["status"] == "CLOSED"
    finally:
        repo.close()


def test_exact_close_replay_is_idempotent(tmp_path):
    repo = build_repo(tmp_path)

    try:
        with repo.atomic_cycle():
            first, first_changed = (
                repo.close_position_idempotent(
                    closed_position_payload()
                )
            )

        with repo.atomic_cycle():
            second, second_changed = (
                repo.close_position_idempotent(
                    closed_position_payload()
                )
            )

        assert first_changed is True
        assert second_changed is False
        assert first == second
    finally:
        repo.close()


def test_conflicting_closed_replay_fails_closed(tmp_path):
    repo = build_repo(tmp_path)

    try:
        with repo.atomic_cycle():
            repo.close_position_idempotent(
                closed_position_payload()
            )

        conflicting = closed_position_payload(
            exit_price="999",
        )

        with pytest.raises(
            IdempotencyConflictError,
            match="position",
        ):
            with repo.atomic_cycle():
                repo.close_position_idempotent(
                    conflicting
                )
    finally:
        repo.close()


def test_close_requires_existing_position(tmp_path):
    path = tmp_path / "missing-position.db"

    bootstrap_fresh_database(
        path,
        initial_cash_pln="1000",
        bootstrap_id="phase13-a13-missing",
        created_at_utc=NOW,
    )

    repo = SQLiteLedgerRepository.open_writer(path)

    try:
        with pytest.raises(
            IdempotencyConflictError,
            match="existing position",
        ):
            with repo.atomic_cycle():
                repo.close_position_idempotent(
                    closed_position_payload()
                )
    finally:
        repo.close()


def test_close_requires_closed_target_status(tmp_path):
    repo = build_repo(tmp_path)

    try:
        with pytest.raises(
            ValueError,
            match="CLOSED",
        ):
            with repo.atomic_cycle():
                repo.close_position_idempotent(
                    open_position_payload()
                )
    finally:
        repo.close()


def test_close_requires_exit_execution(tmp_path):
    repo = build_repo(
        tmp_path,
        include_exit_execution=False,
    )

    try:
        with pytest.raises(
            IdempotencyConflictError,
            match="exit execution",
        ):
            with repo.atomic_cycle():
                repo.close_position_idempotent(
                    closed_position_payload()
                )

        assert read_position(repo)["status"] == "OPEN"
    finally:
        repo.close()


def test_close_rejects_immutable_position_mutation(tmp_path):
    repo = build_repo(tmp_path)

    try:
        payload = closed_position_payload()
        payload["quantity_native"] = "2"

        with pytest.raises(
            IdempotencyConflictError,
            match="immutable",
        ):
            with repo.atomic_cycle():
                repo.close_position_idempotent(
                    payload
                )

        assert read_position(repo)["status"] == "OPEN"
    finally:
        repo.close()


def test_existing_insert_only_method_still_rejects_open_to_closed(
    tmp_path,
):
    repo = build_repo(tmp_path)

    try:
        with pytest.raises(
            IdempotencyConflictError,
            match="position_id",
        ):
            with repo.atomic_cycle():
                repo.save_position_idempotent(
                    closed_position_payload()
                )

        assert read_position(repo)["status"] == "OPEN"
    finally:
        repo.close()


def test_close_rollback_restores_open_position(tmp_path):
    repo = build_repo(tmp_path)

    try:
        with pytest.raises(
            RuntimeError,
            match="forced rollback",
        ):
            with repo.atomic_cycle():
                repo.close_position_idempotent(
                    closed_position_payload()
                )

                raise RuntimeError(
                    "forced rollback"
                )

        persisted = read_position(repo)

        assert persisted["status"] == "OPEN"
        assert persisted["exit_execution_id"] is None
        assert persisted["closed_at_utc"] is None
    finally:
        repo.close()


def test_closed_position_survives_reopen(tmp_path):
    path = tmp_path / "reopen.db"

    bootstrap_fresh_database(
        path,
        initial_cash_pln="1000",
        bootstrap_id="phase13-a13-reopen",
        created_at_utc=NOW,
    )

    repo = SQLiteLedgerRepository.open_writer(path)

    with repo.atomic_cycle():
        repo.insert_order_idempotent(
            order_payload(
                order_id="order-entry-a13",
                client_order_id="client-entry-a13",
                side="BUY",
                intent="ENTRY",
            )
        )

        repo.insert_execution_idempotent(
            execution_payload(
                execution_id="execution-entry-a13",
                order_id="order-entry-a13",
                side="BUY",
                price="100",
                timestamp=NOW,
            )
        )

        repo.save_position_idempotent(
            open_position_payload()
        )

        repo.insert_order_idempotent(
            order_payload(
                order_id="order-exit-a13",
                client_order_id="client-exit-a13",
                side="SELL",
                intent="EXIT",
            )
        )

        repo.insert_execution_idempotent(
            execution_payload(
                execution_id="execution-exit-a13",
                order_id="order-exit-a13",
                side="SELL",
                price="106.25",
                timestamp=NEXT,
            )
        )

        repo.close_position_idempotent(
            closed_position_payload()
        )

    repo.close()

    reopened = SQLiteLedgerRepository.open_writer(path)

    try:
        persisted = read_position(reopened)

        assert persisted["status"] == "CLOSED"
        assert persisted["exit_execution_id"] == "execution-exit-a13"
    finally:
        reopened.close()
