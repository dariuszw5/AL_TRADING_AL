from __future__ import annotations

import hashlib
import json
import os
from datetime import timezone
from pathlib import Path
from types import MappingProxyType

from src.core.clock import SystemClock
from src.execution.capital_startup import (
    Phase12StartupMetadata,
)


PHASE12_STARTUP_JOURNAL_SCHEMA = (
    "phase12-capital-startup-metadata-journal-v1"
)


class Phase12StartupMetadataStoreError(
    ValueError
):
    pass


def _required_text(
    value,
    field_name,
):
    if value is None:
        raise Phase12StartupMetadataStoreError(
            f"{field_name} is required"
        )

    result = str(
        value
    ).strip()

    if not result:
        raise Phase12StartupMetadataStoreError(
            f"{field_name} is required"
        )

    return result


def _hash_text(
    value,
    field_name,
):
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
        raise Phase12StartupMetadataStoreError(
            f"{field_name} must be a 64-character lowercase SHA256"
        )

    return result


def _canonical_json_bytes(
    value,
):
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
        raise Phase12StartupMetadataStoreError(
            "Phase 12 startup metadata is not canonical-JSON serializable"
        ) from exc

    return encoded.encode(
        "utf-8"
    )


def _record_hash(
    payload,
):
    return hashlib.sha256(
        _canonical_json_bytes(
            payload
        )
    ).hexdigest()


def _utc_timestamp_text(
    value,
):
    if value is None:
        raise Phase12StartupMetadataStoreError(
            "startup timestamp is required"
        )

    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise Phase12StartupMetadataStoreError(
            "startup timestamp must be timezone-aware"
        )

    return (
        value
        .astimezone(
            timezone.utc
        )
        .isoformat(
            timespec="microseconds"
        )
        .replace(
            "+00:00",
            "Z",
        )
    )


def _bool_mapping(
    value,
    field_name,
):
    try:
        raw = dict(
            value
        )
    except Exception as exc:
        raise Phase12StartupMetadataStoreError(
            f"{field_name} must be a mapping"
        ) from exc

    normalized = {}

    for key, item in raw.items():
        key_text = _required_text(
            key,
            f"{field_name} key",
        )

        if not isinstance(
            item,
            bool,
        ):
            raise Phase12StartupMetadataStoreError(
                f"{field_name} values must be bool"
            )

        normalized[
            key_text
        ] = item

    return normalized


def _json_mapping(
    value,
    field_name,
):
    try:
        result = dict(
            value
        )
    except Exception as exc:
        raise Phase12StartupMetadataStoreError(
            f"{field_name} must be a mapping"
        ) from exc

    _canonical_json_bytes(
        result
    )

    return result


def build_phase12_startup_record(
    metadata,
    *,
    startup_timestamp,
):
    if not isinstance(
        metadata,
        Phase12StartupMetadata,
    ):
        raise TypeError(
            "metadata must be Phase12StartupMetadata"
        )

    payload = {
        "journal_schema": (
            PHASE12_STARTUP_JOURNAL_SCHEMA
        ),
        "startup_timestamp_utc": (
            _utc_timestamp_text(
                startup_timestamp
            )
        ),
        "metadata_schema": (
            _required_text(
                metadata.schema,
                "metadata.schema",
            )
        ),
        "execution_config_hash": (
            _hash_text(
                metadata.execution_config_hash,
                "metadata.execution_config_hash",
            )
        ),
        "phase10_global_config_hash": (
            _hash_text(
                metadata.phase10_global_config_hash,
                "metadata.phase10_global_config_hash",
            )
        ),
        "global_config_hash": (
            _hash_text(
                metadata.global_config_hash,
                "metadata.global_config_hash",
            )
        ),
        "asset_registry_hash": (
            _hash_text(
                metadata.asset_registry_hash,
                "metadata.asset_registry_hash",
            )
        ),
        "paper_mode": (
            _required_text(
                metadata.paper_mode,
                "metadata.paper_mode",
            )
        ),
        "phase10_feature_flags": (
            _bool_mapping(
                metadata.phase10_feature_flags,
                "phase10_feature_flags",
            )
        ),
        "phase12_feature_flags": (
            _bool_mapping(
                metadata.phase12_feature_flags,
                "phase12_feature_flags",
            )
        ),
        "phase10_runtime_policy": (
            _json_mapping(
                metadata.phase10_runtime_policy,
                "phase10_runtime_policy",
            )
        ),
        "capital_policy": (
            _json_mapping(
                metadata.capital_policy,
                "capital_policy",
            )
        ),
        "limitations": [
            str(value)
            for value
            in tuple(
                metadata.limitations
            )
        ],
    }

    return {
        **payload,
        "record_hash": (
            _record_hash(
                payload
            )
        ),
    }


def verify_phase12_startup_record(
    record,
):
    if not isinstance(
        record,
        dict,
    ):
        raise Phase12StartupMetadataStoreError(
            "Phase 12 startup record must be an object"
        )

    stored_hash = _hash_text(
        record.get(
            "record_hash"
        ),
        "record_hash",
    )

    payload = {
        key: value
        for key, value
        in record.items()
        if key != "record_hash"
    }

    if (
        payload.get(
            "journal_schema"
        )
        != PHASE12_STARTUP_JOURNAL_SCHEMA
    ):
        raise Phase12StartupMetadataStoreError(
            "PHASE12_STARTUP_JOURNAL_SCHEMA_MISMATCH"
        )

    expected_hash = (
        _record_hash(
            payload
        )
    )

    if stored_hash != expected_hash:
        raise Phase12StartupMetadataStoreError(
            "PHASE12_STARTUP_RECORD_HASH_MISMATCH"
        )

    return MappingProxyType(
        dict(
            record
        )
    )


class Phase12StartupMetadataJournal:
    """
    Append-only JSONL persistence for Phase 12 capital startup metadata.

    This file is separate from Phase 10 startup metadata and does not
    mutate state.json, execution_journal.jsonl, realized accounting or
    the Phase 11 cash ledger.
    """

    def __init__(
        self,
        path,
        *,
        clock=None,
    ):
        self.path = Path(
            path
        )

        self.clock = (
            clock
            or SystemClock()
        )

    def append(
        self,
        metadata,
    ):
        record = (
            build_phase12_startup_record(
                metadata,
                startup_timestamp=(
                    self.clock.now()
                ),
            )
        )

        encoded = (
            _canonical_json_bytes(
                record
            )
            + b"\n"
        )

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        fd = os.open(
            self.path,
            (
                os.O_WRONLY
                | os.O_CREAT
                | os.O_APPEND
            ),
            0o600,
        )

        try:
            offset = 0

            while offset < len(
                encoded
            ):
                written = os.write(
                    fd,
                    encoded[
                        offset:
                    ],
                )

                if written <= 0:
                    raise OSError(
                        "Phase 12 startup metadata append wrote zero bytes"
                    )

                offset += written

            os.fsync(
                fd
            )

        finally:
            os.close(
                fd
            )

        return MappingProxyType(
            dict(
                record
            )
        )

    def read_records(
        self,
    ):
        if not self.path.exists():
            return ()

        text = self.path.read_text(
            encoding="utf-8"
        )

        records = []

        for line_number, line in enumerate(
            text.splitlines(),
            start=1,
        ):
            if not line.strip():
                raise Phase12StartupMetadataStoreError(
                    "PHASE12_STARTUP_BLANK_RECORD:"
                    + str(
                        line_number
                    )
                )

            try:
                record = json.loads(
                    line
                )
            except json.JSONDecodeError as exc:
                raise Phase12StartupMetadataStoreError(
                    "PHASE12_STARTUP_JSON_INVALID:"
                    + str(
                        line_number
                    )
                ) from exc

            try:
                verified = (
                    verify_phase12_startup_record(
                        record
                    )
                )
            except Phase12StartupMetadataStoreError as exc:
                raise Phase12StartupMetadataStoreError(
                    "PHASE12_STARTUP_RECORD_INVALID:"
                    + str(
                        line_number
                    )
                    + ":"
                    + str(
                        exc
                    )
                ) from exc

            records.append(
                verified
            )

        return tuple(
            records
        )
