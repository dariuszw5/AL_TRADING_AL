from __future__ import annotations

import hashlib
import json
import os
from datetime import timezone
from pathlib import Path
from types import MappingProxyType

from src.core.clock import SystemClock


STARTUP_METADATA_JOURNAL_SCHEMA = (
    "phase10-startup-metadata-journal-v1"
)


class StartupMetadataStoreError(
    ValueError
):
    pass


def _required_text(
    value,
    field_name,
):
    if value is None:
        raise StartupMetadataStoreError(
            f"{field_name} is required"
        )

    result = str(
        value
    ).strip()

    if not result:
        raise StartupMetadataStoreError(
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
        raise StartupMetadataStoreError(
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
            separators=(
                ",",
                ":",
            ),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise StartupMetadataStoreError(
            "startup metadata is not canonical-JSON serializable"
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
        raise StartupMetadataStoreError(
            "startup timestamp is required"
        )

    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise StartupMetadataStoreError(
            "startup timestamp must be timezone-aware"
        )

    utc_value = value.astimezone(
        timezone.utc
    )

    return (
        utc_value
        .isoformat(
            timespec="microseconds"
        )
        .replace(
            "+00:00",
            "Z",
        )
    )


def _feature_flags(
    metadata,
):
    raw = getattr(
        metadata,
        "feature_flags",
        None,
    )

    if raw is None:
        raise StartupMetadataStoreError(
            "feature_flags are required"
        )

    flags = dict(
        raw
    )

    normalized = {}

    for key, value in flags.items():
        key = _required_text(
            key,
            "feature flag key",
        )

        if not isinstance(
            value,
            bool,
        ):
            raise StartupMetadataStoreError(
                "feature flag values must be bool"
            )

        normalized[
            key
        ] = value

    return normalized


def _runtime_policy(
    metadata,
):
    raw = getattr(
        metadata,
        "runtime_policy",
        None,
    )

    if raw is None:
        raise StartupMetadataStoreError(
            "runtime_policy is required"
        )

    policy = dict(
        raw
    )

    _canonical_json_bytes(
        policy
    )

    return policy


def build_startup_metadata_record(
    metadata,
    *,
    startup_timestamp,
):
    payload = {
        "journal_schema": (
            STARTUP_METADATA_JOURNAL_SCHEMA
        ),
        "startup_timestamp_utc": (
            _utc_timestamp_text(
                startup_timestamp
            )
        ),
        "metadata_schema": (
            _required_text(
                getattr(
                    metadata,
                    "schema",
                    None,
                ),
                "metadata.schema",
            )
        ),
        "execution_config_hash": (
            _hash_text(
                getattr(
                    metadata,
                    "execution_config_hash",
                    None,
                ),
                "metadata.execution_config_hash",
            )
        ),
        "base_global_config_hash": (
            _hash_text(
                getattr(
                    metadata,
                    "base_global_config_hash",
                    None,
                ),
                "metadata.base_global_config_hash",
            )
        ),
        "global_config_hash": (
            _hash_text(
                getattr(
                    metadata,
                    "global_config_hash",
                    None,
                ),
                "metadata.global_config_hash",
            )
        ),
        "asset_registry_hash": (
            _hash_text(
                getattr(
                    metadata,
                    "asset_registry_hash",
                    None,
                ),
                "metadata.asset_registry_hash",
            )
        ),
        "paper_mode": (
            _required_text(
                getattr(
                    metadata,
                    "paper_mode",
                    None,
                ),
                "metadata.paper_mode",
            )
        ),
        "feature_flags": (
            _feature_flags(
                metadata
            )
        ),
        "runtime_policy": (
            _runtime_policy(
                metadata
            )
        ),
        "limitations": [
            str(value)
            for value
            in tuple(
                getattr(
                    metadata,
                    "limitations",
                    (),
                )
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


def verify_startup_metadata_record(
    record,
):
    if not isinstance(
        record,
        dict,
    ):
        raise StartupMetadataStoreError(
            "startup metadata record must be an object"
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
        != STARTUP_METADATA_JOURNAL_SCHEMA
    ):
        raise StartupMetadataStoreError(
            "STARTUP_METADATA_JOURNAL_SCHEMA_MISMATCH"
        )

    expected_hash = (
        _record_hash(
            payload
        )
    )

    if stored_hash != expected_hash:
        raise StartupMetadataStoreError(
            "STARTUP_METADATA_RECORD_HASH_MISMATCH"
        )

    return MappingProxyType(
        dict(
            record
        )
    )


class StartupMetadataJournal:
    """
    Append-only JSONL persistence for Phase 10 startup metadata.

    This is a new, explicitly scoped metadata file. It does not write to
    execution_journal.jsonl, state.json or data/live_state.
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
        now = self.clock.now()

        record = (
            build_startup_metadata_record(
                metadata,
                startup_timestamp=now,
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
                        "startup metadata append wrote zero bytes"
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
                raise StartupMetadataStoreError(
                    "STARTUP_METADATA_BLANK_RECORD:"
                    + str(
                        line_number
                    )
                )

            try:
                record = json.loads(
                    line
                )

            except json.JSONDecodeError as exc:
                raise StartupMetadataStoreError(
                    "STARTUP_METADATA_JSON_INVALID:"
                    + str(
                        line_number
                    )
                ) from exc

            try:
                verified = (
                    verify_startup_metadata_record(
                        record
                    )
                )

            except StartupMetadataStoreError as exc:
                raise StartupMetadataStoreError(
                    "STARTUP_METADATA_RECORD_INVALID:"
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
