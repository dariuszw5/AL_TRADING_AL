from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from types import MappingProxyType

from src.core.clock import SystemClock


REALIZED_ACCOUNTING_JOURNAL_SCHEMA = "phase10-realized-accounting-v1"


class RealizedAccountingStoreError(ValueError):
    pass


@dataclass(frozen=True)
class RealizedAccountingPersistResult:
    record: object
    appended: bool


def _required_text(value, field_name):
    if value is None:
        raise RealizedAccountingStoreError(f"{field_name} is required")

    result = str(value).strip()

    if not result:
        raise RealizedAccountingStoreError(f"{field_name} is required")

    return result


def _hash_text(value, field_name):
    result = _required_text(value, field_name).lower()

    if (
        len(result) != 64
        or any(char not in "0123456789abcdef" for char in result)
    ):
        raise RealizedAccountingStoreError(
            f"{field_name} must be a 64-character lowercase SHA256"
        )

    return result


def _datetime_text(value):
    if value.tzinfo is None or value.utcoffset() is None:
        raise RealizedAccountingStoreError("datetime must be timezone-aware")

    return (
        value.astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _jsonable(value):
    if value is None:
        return None

    if isinstance(value, Enum):
        return _jsonable(value.value)

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, datetime):
        return _datetime_text(value)

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, (str, int, float, bool)):
        return value

    if is_dataclass(value):
        return {
            field.name: _jsonable(getattr(value, field.name))
            for field in fields(value)
        }

    if isinstance(value, MappingProxyType):
        value = dict(value)

    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}

    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]

    if hasattr(value, "__dict__"):
        return {
            str(key): _jsonable(item)
            for key, item in vars(value).items()
            if not str(key).startswith("_")
        }

    raise RealizedAccountingStoreError(
        "unsupported realized accounting evidence type: "
        + type(value).__name__
    )


def _canonical_json_bytes(value):
    try:
        text = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise RealizedAccountingStoreError(
            "realized accounting record is not canonical-JSON serializable"
        ) from exc

    return text.encode("utf-8")


def _sha256(value):
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _booking_identity(
    *,
    asset_id,
    position_id,
    entry_execution_id,
    exit_execution_id,
):
    return {
        "asset_id": asset_id,
        "position_id": position_id,
        "entry_execution_id": entry_execution_id,
        "exit_execution_id": exit_execution_id,
    }


def _booking_key(identity):
    return _sha256(identity)


def _semantic_payload(record):
    return {
        key: value
        for key, value in record.items()
        if key not in {"recorded_at_utc", "record_hash"}
    }


def _verify_record(record):
    if not isinstance(record, dict):
        raise RealizedAccountingStoreError(
            "realized accounting record must be an object"
        )

    if record.get("journal_schema") != REALIZED_ACCOUNTING_JOURNAL_SCHEMA:
        raise RealizedAccountingStoreError(
            "REALIZED_ACCOUNTING_SCHEMA_MISMATCH"
        )

    stored_hash = _hash_text(record.get("record_hash"), "record_hash")

    payload = {
        key: value
        for key, value in record.items()
        if key != "record_hash"
    }

    if stored_hash != _sha256(payload):
        raise RealizedAccountingStoreError(
            "REALIZED_ACCOUNTING_RECORD_HASH_MISMATCH"
        )

    booking_key = _hash_text(record.get("booking_key"), "booking_key")

    identity = _booking_identity(
        asset_id=_required_text(record.get("asset_id"), "asset_id"),
        position_id=_required_text(
            record.get("position_id"),
            "position_id",
        ),
        entry_execution_id=_required_text(
            record.get("entry_execution_id"),
            "entry_execution_id",
        ),
        exit_execution_id=_required_text(
            record.get("exit_execution_id"),
            "exit_execution_id",
        ),
    )

    if booking_key != _booking_key(identity):
        raise RealizedAccountingStoreError(
            "REALIZED_ACCOUNTING_BOOKING_KEY_MISMATCH"
        )

    return MappingProxyType(dict(record))


class RealizedAccountingJournal:
    """
    Append-only realized PLN booking journal.

    Sequential idempotency is defined by asset id + position id +
    entry execution id + exit execution id.
    """

    def __init__(self, path, *, clock=None):
        self.path = Path(path)
        self.clock = clock or SystemClock()

    def read_records(self):
        if not self.path.exists():
            return ()

        text = self.path.read_text(encoding="utf-8")
        records = []
        keys = set()

        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                raise RealizedAccountingStoreError(
                    "REALIZED_ACCOUNTING_BLANK_RECORD:"
                    + str(line_number)
                )

            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RealizedAccountingStoreError(
                    "REALIZED_ACCOUNTING_JSON_INVALID:"
                    + str(line_number)
                ) from exc

            try:
                record = _verify_record(raw)
            except RealizedAccountingStoreError as exc:
                raise RealizedAccountingStoreError(
                    "REALIZED_ACCOUNTING_RECORD_INVALID:"
                    + str(line_number)
                    + ":"
                    + str(exc)
                ) from exc

            key = record["booking_key"]

            if key in keys:
                raise RealizedAccountingStoreError(
                    "REALIZED_ACCOUNTING_DUPLICATE_BOOKING_KEY"
                )

            keys.add(key)
            records.append(record)

        return tuple(records)

    def append_booking(
        self,
        *,
        asset_id,
        position,
        exit_execution,
        realized_result,
        startup_metadata,
    ):
        if position is None:
            raise RealizedAccountingStoreError("position is required")
        if exit_execution is None:
            raise RealizedAccountingStoreError("exit_execution is required")
        if realized_result is None:
            raise RealizedAccountingStoreError("realized_result is required")

        accounting_record = getattr(
            realized_result,
            "accounting_record",
            None,
        )
        fx_booking = getattr(realized_result, "fx_booking", None)

        if accounting_record is None:
            raise RealizedAccountingStoreError(
                "realized_result.accounting_record is required"
            )
        if fx_booking is None:
            raise RealizedAccountingStoreError(
                "realized_result.fx_booking is required"
            )

        asset_id = _required_text(asset_id, "asset_id")
        position_asset = _required_text(
            getattr(position, "asset_id", None),
            "position.asset_id",
        )
        execution_asset = _required_text(
            getattr(exit_execution, "asset_id", None),
            "exit_execution.asset_id",
        )

        if position_asset != asset_id or execution_asset != asset_id:
            raise RealizedAccountingStoreError(
                "REALIZED_ACCOUNTING_ASSET_MISMATCH"
            )

        position_id = _required_text(
            getattr(position, "position_id", None),
            "position.position_id",
        )
        entry_execution_id = _required_text(
            getattr(position, "entry_execution_id", None),
            "position.entry_execution_id",
        )
        exit_execution_id = _required_text(
            getattr(position, "exit_execution_id", None),
            "position.exit_execution_id",
        )
        actual_exit_execution_id = _required_text(
            getattr(exit_execution, "execution_id", None),
            "exit_execution.execution_id",
        )

        if exit_execution_id != actual_exit_execution_id:
            raise RealizedAccountingStoreError(
                "REALIZED_ACCOUNTING_EXIT_EXECUTION_MISMATCH"
            )

        if getattr(position, "closed_at", None) is None:
            raise RealizedAccountingStoreError(
                "REALIZED_ACCOUNTING_CLOSED_POSITION_REQUIRED"
            )

        net_native = getattr(
            accounting_record,
            "net_realized_pnl_native",
            None,
        )
        net_pln = getattr(
            accounting_record,
            "net_realized_pnl_pln",
            None,
        )
        fx_rate = getattr(accounting_record, "fx_rate", None)
        fx_path = getattr(accounting_record, "fx_path", None)

        if net_native is None:
            raise RealizedAccountingStoreError(
                "net_realized_pnl_native is required"
            )
        if net_pln is None:
            raise RealizedAccountingStoreError(
                "net_realized_pnl_pln is required"
            )
        if fx_rate is None:
            raise RealizedAccountingStoreError("fx_rate is required")
        if fx_path is None:
            raise RealizedAccountingStoreError("fx_path is required")

        identity = _booking_identity(
            asset_id=asset_id,
            position_id=position_id,
            entry_execution_id=entry_execution_id,
            exit_execution_id=exit_execution_id,
        )
        booking_key = _booking_key(identity)

        semantic = {
            "journal_schema": REALIZED_ACCOUNTING_JOURNAL_SCHEMA,
            "booking_key": booking_key,
            **identity,
            "closed_at_utc": _jsonable(
                getattr(position, "closed_at", None)
            ),
            "native_currency": _jsonable(
                getattr(accounting_record, "native_currency", None)
            ),
            "net_realized_pnl_native": _jsonable(net_native),
            "fx_rate": _jsonable(fx_rate),
            "fx_path": _required_text(
                fx_path,
                "accounting_record.fx_path",
            ),
            "net_realized_pnl_pln": _jsonable(net_pln),
            "fx_evidence": _jsonable(fx_booking),
            "accounting_evidence": _jsonable(accounting_record),
            "limitations": _jsonable(
                tuple(getattr(realized_result, "limitations", ()))
            ),
            "execution_config_hash": _hash_text(
                getattr(exit_execution, "config_hash", None),
                "exit_execution.config_hash",
            ),
            "global_config_hash": _hash_text(
                getattr(startup_metadata, "global_config_hash", None),
                "startup_metadata.global_config_hash",
            ),
        }

        records = self.read_records()

        for existing in records:
            if existing["booking_key"] != booking_key:
                continue

            if _semantic_payload(dict(existing)) != semantic:
                raise RealizedAccountingStoreError(
                    "REALIZED_ACCOUNTING_IDEMPOTENCY_CONFLICT"
                )

            return RealizedAccountingPersistResult(
                record=existing,
                appended=False,
            )

        now = self.clock.now()

        record_without_hash = {
            **semantic,
            "recorded_at_utc": _datetime_text(now),
        }
        record = {
            **record_without_hash,
            "record_hash": _sha256(record_without_hash),
        }

        encoded = _canonical_json_bytes(record) + b"\n"

        self.path.parent.mkdir(parents=True, exist_ok=True)

        fd = os.open(
            self.path,
            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
            0o600,
        )

        try:
            offset = 0
            while offset < len(encoded):
                written = os.write(fd, encoded[offset:])
                if written <= 0:
                    raise OSError(
                        "realized accounting append wrote zero bytes"
                    )
                offset += written

            os.fsync(fd)
        finally:
            os.close(fd)

        verified = self.read_records()

        if len(verified) != len(records) + 1:
            raise RealizedAccountingStoreError(
                "REALIZED_ACCOUNTING_APPEND_COUNT_MISMATCH"
            )

        if verified[-1]["record_hash"] != record["record_hash"]:
            raise RealizedAccountingStoreError(
                "REALIZED_ACCOUNTING_APPEND_HASH_MISMATCH"
            )

        return RealizedAccountingPersistResult(
            record=verified[-1],
            appended=True,
        )


class PersistingAccountingRuntime:
    """
    Additive wrapper around the already-wired accounting runtime.

    Only successful realized booking results are persisted.
    """

    def __init__(self, *, runtime, journal, startup_metadata):
        if runtime is None:
            raise TypeError("runtime is required")
        if not isinstance(journal, RealizedAccountingJournal):
            raise TypeError(
                "journal must be RealizedAccountingJournal"
            )
        if startup_metadata is None:
            raise TypeError("startup_metadata is required")

        self.runtime = runtime
        self.journal = journal
        self.startup_metadata = startup_metadata
        self.last_persistence = MappingProxyType({})

    def run_cycle(self, asset_ids):
        result = self.runtime.run_cycle(asset_ids)
        persisted = {}

        for asset_id in tuple(str(value) for value in asset_ids):
            accounting_result = result.accounting_results.get(asset_id)

            if (
                accounting_result is None
                or accounting_result.realized_result is None
            ):
                continue

            execution_asset_result = (
                result.execution_cycle.results.get(asset_id)
            )

            if execution_asset_result is None:
                raise RealizedAccountingStoreError(
                    "REALIZED_ACCOUNTING_EXECUTION_RESULT_REQUIRED"
                )

            broker_result = getattr(
                execution_asset_result,
                "broker_result",
                None,
            )

            if broker_result is None:
                raise RealizedAccountingStoreError(
                    "REALIZED_ACCOUNTING_BROKER_RESULT_REQUIRED"
                )

            persist_result = self.journal.append_booking(
                asset_id=asset_id,
                position=getattr(
                    broker_result,
                    "position",
                    None,
                ),
                exit_execution=getattr(
                    broker_result,
                    "execution",
                    None,
                ),
                realized_result=accounting_result.realized_result,
                startup_metadata=self.startup_metadata,
            )

            persisted[asset_id] = persist_result

        self.last_persistence = MappingProxyType(dict(persisted))
        return result
