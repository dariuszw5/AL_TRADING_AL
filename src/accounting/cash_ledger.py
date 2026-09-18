from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import MappingProxyType

from src.accounting.realized_persistence import (
    RealizedAccountingJournal,
)
from src.core.clock import SystemClock


CASH_LEDGER_SCHEMA = "phase11-cash-ledger-v1"
INITIAL_RECORD = "INITIAL"
REALIZED_SETTLEMENT_RECORD = "REALIZED_SETTLEMENT"

ENTRY_FEE_SETTLED_AT_REALIZATION = (
    "ENTRY_FEE_SETTLED_AT_REALIZATION"
)


class CashLedgerError(ValueError):
    pass


@dataclass(frozen=True)
class CashLedgerAppendResult:
    record: object
    appended: bool


def _decimal(value, field_name):
    try:
        result = Decimal(str(value))
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:
        raise CashLedgerError(
            f"{field_name} must be a finite decimal"
        ) from exc

    if not result.is_finite():
        raise CashLedgerError(
            f"{field_name} must be a finite decimal"
        )

    return result


def _required_text(value, field_name):
    if value is None:
        raise CashLedgerError(
            f"{field_name} is required"
        )

    result = str(value).strip()

    if not result:
        raise CashLedgerError(
            f"{field_name} is required"
        )

    return result


def _hash_text(value, field_name):
    result = _required_text(
        value,
        field_name,
    ).lower()

    if (
        len(result) != 64
        or any(
            char not in "0123456789abcdef"
            for char in result
        )
    ):
        raise CashLedgerError(
            f"{field_name} must be a 64-character lowercase SHA256"
        )

    return result


def _datetime_text(value):
    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CashLedgerError(
            "record timestamp must be timezone-aware"
        )

    return (
        value
        .astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _canonical_json_bytes(value):
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise CashLedgerError(
            "cash ledger record is not canonical-JSON serializable"
        ) from exc

    return encoded.encode("utf-8")


def _record_hash(payload):
    return hashlib.sha256(
        _canonical_json_bytes(payload)
    ).hexdigest()


def _cash_text(value):
    return str(
        _decimal(
            value,
            "cash_pln",
        )
    )


def _record_payload(record):
    return {
        key: value
        for key, value in record.items()
        if key != "record_hash"
    }


class Phase11CashLedger:
    """
    Append-only authoritative settled-cash PLN ledger.

    CASH SEMANTICS

    - OPEN does not mutate settled cash.
    - OPEN does not reserve notional, margin or collateral.
    - Entry fee is not settled separately at OPEN.
    - CLOSE settles exactly persisted net_realized_pnl_pln once.
    - Therefore entry and exit fees remain deducted exactly once inside the
      realized booking that produces net_realized_pnl_pln.
    - Spread/slippage remain attribution/reporting and are not deducted again.

    This ledger is accounting state only. It is not buying power, margin,
    collateral or permission to open a position.
    """

    def __init__(
        self,
        path,
        *,
        clock=None,
    ):
        self.path = Path(path)
        self.clock = clock or SystemClock()
        self._initialized = False

    def _write_append(self, record):
        encoded = (
            _canonical_json_bytes(record)
            + b"\n"
        )

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        fd = os.open(
            self.path,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_APPEND,
            0o600,
        )

        try:
            offset = 0

            while offset < len(encoded):
                written = os.write(
                    fd,
                    encoded[offset:],
                )

                if written <= 0:
                    raise OSError(
                        "cash ledger append wrote zero bytes"
                    )

                offset += written

            os.fsync(fd)

        finally:
            os.close(fd)

    def _verify_record_hash(
        self,
        record,
        *,
        line_number,
    ):
        if not isinstance(record, dict):
            raise CashLedgerError(
                "CASH_LEDGER_RECORD_NOT_OBJECT:"
                + str(line_number)
            )

        if (
            record.get("journal_schema")
            != CASH_LEDGER_SCHEMA
        ):
            raise CashLedgerError(
                "CASH_LEDGER_SCHEMA_MISMATCH:"
                + str(line_number)
            )

        stored = _hash_text(
            record.get("record_hash"),
            "record_hash",
        )

        expected = _record_hash(
            _record_payload(record)
        )

        if stored != expected:
            raise CashLedgerError(
                "CASH_LEDGER_RECORD_HASH_MISMATCH:"
                + str(line_number)
            )

    def read_records(self):
        if not self.path.exists():
            if self._initialized:
                raise CashLedgerError(
                    "CASH_LEDGER_MISSING_AFTER_INITIALIZATION"
                )

            return ()

        text = self.path.read_text(
            encoding="utf-8"
        )

        if not text:
            raise CashLedgerError(
                "CASH_LEDGER_EMPTY"
            )

        records = []
        realized_booking_keys = set()
        exit_execution_ids = set()
        previous_hash = None
        previous_cash = None

        for line_number, line in enumerate(
            text.splitlines(),
            start=1,
        ):
            if not line.strip():
                raise CashLedgerError(
                    "CASH_LEDGER_BLANK_RECORD:"
                    + str(line_number)
                )

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CashLedgerError(
                    "CASH_LEDGER_JSON_INVALID:"
                    + str(line_number)
                ) from exc

            self._verify_record_hash(
                record,
                line_number=line_number,
            )

            sequence = record.get("sequence")

            if (
                not isinstance(sequence, int)
                or sequence != line_number - 1
            ):
                raise CashLedgerError(
                    "CASH_LEDGER_SEQUENCE_MISMATCH:"
                    + str(line_number)
                )

            if record.get(
                "previous_record_hash"
            ) != previous_hash:
                raise CashLedgerError(
                    "CASH_LEDGER_CHAIN_MISMATCH:"
                    + str(line_number)
                )

            limitations = tuple(
                record.get(
                    "limitations",
                    (),
                )
            )

            if (
                ENTRY_FEE_SETTLED_AT_REALIZATION
                not in limitations
            ):
                raise CashLedgerError(
                    "CASH_LEDGER_LIMITATION_MISSING:"
                    + str(line_number)
                )

            record_type = record.get(
                "record_type"
            )

            if line_number == 1:
                if record_type != INITIAL_RECORD:
                    raise CashLedgerError(
                        "CASH_LEDGER_INITIAL_RECORD_REQUIRED"
                    )

                if record.get(
                    "cash_before_pln"
                ) is not None:
                    raise CashLedgerError(
                        "CASH_LEDGER_INITIAL_CASH_BEFORE_MUST_BE_NULL"
                    )

                initial_cash = _decimal(
                    record.get(
                        "initial_cash_pln"
                    ),
                    "initial_cash_pln",
                )

                delta = _decimal(
                    record.get(
                        "cash_delta_pln"
                    ),
                    "cash_delta_pln",
                )

                cash_after = _decimal(
                    record.get(
                        "cash_after_pln"
                    ),
                    "cash_after_pln",
                )

                if delta != Decimal("0"):
                    raise CashLedgerError(
                        "CASH_LEDGER_INITIAL_DELTA_MUST_BE_ZERO"
                    )

                if cash_after != initial_cash:
                    raise CashLedgerError(
                        "CASH_LEDGER_INITIAL_BALANCE_MISMATCH"
                    )

                if any(
                    record.get(field)
                    is not None
                    for field in (
                        "realized_booking_key",
                        "exit_execution_id",
                        "source_realized_record_hash",
                    )
                ):
                    raise CashLedgerError(
                        "CASH_LEDGER_INITIAL_SOURCE_MUST_BE_NULL"
                    )

                previous_cash = cash_after

            else:
                if (
                    record_type
                    != REALIZED_SETTLEMENT_RECORD
                ):
                    raise CashLedgerError(
                        "CASH_LEDGER_SETTLEMENT_RECORD_REQUIRED:"
                        + str(line_number)
                    )

                if record.get(
                    "initial_cash_pln"
                ) is not None:
                    raise CashLedgerError(
                        "CASH_LEDGER_SETTLEMENT_INITIAL_CASH_MUST_BE_NULL"
                    )

                cash_before = _decimal(
                    record.get(
                        "cash_before_pln"
                    ),
                    "cash_before_pln",
                )

                delta = _decimal(
                    record.get(
                        "cash_delta_pln"
                    ),
                    "cash_delta_pln",
                )

                cash_after = _decimal(
                    record.get(
                        "cash_after_pln"
                    ),
                    "cash_after_pln",
                )

                if cash_before != previous_cash:
                    raise CashLedgerError(
                        "CASH_LEDGER_CASH_BEFORE_MISMATCH:"
                        + str(line_number)
                    )

                if (
                    cash_before
                    + delta
                    != cash_after
                ):
                    raise CashLedgerError(
                        "CASH_LEDGER_SETTLEMENT_INVARIANT_BROKEN:"
                        + str(line_number)
                    )

                booking_key = _hash_text(
                    record.get(
                        "realized_booking_key"
                    ),
                    "realized_booking_key",
                )

                exit_execution_id = (
                    _required_text(
                        record.get(
                            "exit_execution_id"
                        ),
                        "exit_execution_id",
                    )
                )

                _hash_text(
                    record.get(
                        "source_realized_record_hash"
                    ),
                    "source_realized_record_hash",
                )

                if (
                    booking_key
                    in realized_booking_keys
                ):
                    raise CashLedgerError(
                        "CASH_LEDGER_DUPLICATE_REALIZED_BOOKING"
                    )

                if (
                    exit_execution_id
                    in exit_execution_ids
                ):
                    raise CashLedgerError(
                        "CASH_LEDGER_DUPLICATE_EXIT_EXECUTION"
                    )

                realized_booking_keys.add(
                    booking_key
                )

                exit_execution_ids.add(
                    exit_execution_id
                )

                previous_cash = cash_after

            previous_hash = record[
                "record_hash"
            ]

            records.append(
                MappingProxyType(
                    dict(record)
                )
            )

        return tuple(records)

    def initialize(
        self,
        initial_cash_pln=None,
    ):
        if self.path.exists():
            records = self.read_records()

            if not records:
                raise CashLedgerError(
                    "CASH_LEDGER_INITIAL_RECORD_REQUIRED"
                )

            existing_initial = _decimal(
                records[0][
                    "initial_cash_pln"
                ],
                "initial_cash_pln",
            )

            if initial_cash_pln is not None:
                requested_initial = _decimal(
                    initial_cash_pln,
                    "initial_cash_pln",
                )

                if (
                    requested_initial
                    != existing_initial
                ):
                    raise CashLedgerError(
                        "CASH_LEDGER_INITIAL_CASH_CONFLICT"
                    )

            self._initialized = True
            return records[0]

        if initial_cash_pln is None:
            raise CashLedgerError(
                "INITIAL_CASH_PLN_REQUIRED"
            )

        initial_cash = _decimal(
            initial_cash_pln,
            "initial_cash_pln",
        )

        payload = {
            "journal_schema": (
                CASH_LEDGER_SCHEMA
            ),
            "record_type": (
                INITIAL_RECORD
            ),
            "sequence": 0,
            "recorded_at_utc": (
                _datetime_text(
                    self.clock.now()
                )
            ),
            "previous_record_hash": None,
            "initial_cash_pln": str(
                initial_cash
            ),
            "cash_before_pln": None,
            "cash_delta_pln": "0",
            "cash_after_pln": str(
                initial_cash
            ),
            "realized_booking_key": None,
            "exit_execution_id": None,
            "source_realized_record_hash": None,
            "source_execution_config_hash": None,
            "source_global_config_hash": None,
            "limitations": [
                ENTRY_FEE_SETTLED_AT_REALIZATION,
            ],
        }

        record = {
            **payload,
            "record_hash": (
                _record_hash(payload)
            ),
        }

        self._write_append(
            record
        )

        verified = self.read_records()

        if len(verified) != 1:
            raise CashLedgerError(
                "CASH_LEDGER_INITIAL_APPEND_COUNT_MISMATCH"
            )

        self._initialized = True
        return verified[0]

    def current_cash_pln(self):
        records = self.read_records()

        if not records:
            raise CashLedgerError(
                "CASH_LEDGER_NOT_INITIALIZED"
            )

        return _decimal(
            records[-1][
                "cash_after_pln"
            ],
            "cash_after_pln",
        )

    def _find_realized_record(
        self,
        realized_journal,
        booking_key,
    ):
        if not isinstance(
            realized_journal,
            RealizedAccountingJournal,
        ):
            raise TypeError(
                "realized_journal must be RealizedAccountingJournal"
            )

        booking_key = _hash_text(
            booking_key,
            "booking_key",
        )

        records = (
            realized_journal
            .read_records()
        )

        matches = [
            record
            for record in records
            if record[
                "booking_key"
            ] == booking_key
        ]

        if len(matches) != 1:
            raise CashLedgerError(
                "CASH_LEDGER_REALIZED_BOOKING_REQUIRED"
            )

        return matches[0]

    def settle_from_realized_journal(
        self,
        *,
        realized_journal,
        booking_key,
    ):
        cash_records = self.read_records()

        if not cash_records:
            raise CashLedgerError(
                "CASH_LEDGER_NOT_INITIALIZED"
            )

        realized_record = (
            self._find_realized_record(
                realized_journal,
                booking_key,
            )
        )

        booking_key = _hash_text(
            realized_record[
                "booking_key"
            ],
            "realized_booking_key",
        )

        exit_execution_id = (
            _required_text(
                realized_record[
                    "exit_execution_id"
                ],
                "exit_execution_id",
            )
        )

        source_record_hash = (
            _hash_text(
                realized_record[
                    "record_hash"
                ],
                "source_realized_record_hash",
            )
        )

        source_execution_config_hash = (
            _hash_text(
                realized_record[
                    "execution_config_hash"
                ],
                "source_execution_config_hash",
            )
        )

        source_global_config_hash = (
            _hash_text(
                realized_record[
                    "global_config_hash"
                ],
                "source_global_config_hash",
            )
        )

        delta = _decimal(
            realized_record[
                "net_realized_pnl_pln"
            ],
            "net_realized_pnl_pln",
        )

        for existing in cash_records[1:]:
            if (
                existing[
                    "realized_booking_key"
                ] == booking_key
            ):
                if (
                    existing[
                        "exit_execution_id"
                    ] != exit_execution_id
                    or existing[
                        "source_realized_record_hash"
                    ] != source_record_hash
                    or _decimal(
                        existing[
                            "cash_delta_pln"
                        ],
                        "cash_delta_pln",
                    ) != delta
                ):
                    raise CashLedgerError(
                        "CASH_LEDGER_IDEMPOTENCY_CONFLICT"
                    )

                return CashLedgerAppendResult(
                    record=existing,
                    appended=False,
                )

            if (
                existing[
                    "exit_execution_id"
                ] == exit_execution_id
            ):
                raise CashLedgerError(
                    "CASH_LEDGER_EXIT_EXECUTION_CONFLICT"
                )

        cash_before = _decimal(
            cash_records[-1][
                "cash_after_pln"
            ],
            "cash_after_pln",
        )

        cash_after = (
            cash_before
            + delta
        )

        previous_hash = (
            cash_records[-1][
                "record_hash"
            ]
        )

        payload = {
            "journal_schema": (
                CASH_LEDGER_SCHEMA
            ),
            "record_type": (
                REALIZED_SETTLEMENT_RECORD
            ),
            "sequence": len(
                cash_records
            ),
            "recorded_at_utc": (
                _datetime_text(
                    self.clock.now()
                )
            ),
            "previous_record_hash": (
                previous_hash
            ),
            "initial_cash_pln": None,
            "cash_before_pln": str(
                cash_before
            ),
            "cash_delta_pln": str(
                delta
            ),
            "cash_after_pln": str(
                cash_after
            ),
            "realized_booking_key": (
                booking_key
            ),
            "exit_execution_id": (
                exit_execution_id
            ),
            "source_realized_record_hash": (
                source_record_hash
            ),
            "source_execution_config_hash": (
                source_execution_config_hash
            ),
            "source_global_config_hash": (
                source_global_config_hash
            ),
            "limitations": [
                ENTRY_FEE_SETTLED_AT_REALIZATION,
            ],
        }

        record = {
            **payload,
            "record_hash": (
                _record_hash(payload)
            ),
        }

        self._write_append(
            record
        )

        verified = self.read_records()

        if (
            len(verified)
            != len(cash_records) + 1
        ):
            raise CashLedgerError(
                "CASH_LEDGER_APPEND_COUNT_MISMATCH"
            )

        if (
            verified[-1][
                "record_hash"
            ]
            != record[
                "record_hash"
            ]
        ):
            raise CashLedgerError(
                "CASH_LEDGER_APPEND_HASH_MISMATCH"
            )

        return CashLedgerAppendResult(
            record=verified[-1],
            appended=True,
        )
