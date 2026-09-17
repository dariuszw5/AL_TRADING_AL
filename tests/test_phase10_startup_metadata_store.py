from datetime import (
    datetime,
    timedelta,
    timezone,
)
from types import SimpleNamespace

import pytest

from src.accounting.startup_metadata_store import (
    STARTUP_METADATA_JOURNAL_SCHEMA,
    StartupMetadataJournal,
    StartupMetadataStoreError,
)


UTC = timezone.utc

T0 = datetime(
    2026,
    9,
    17,
    18,
    30,
    tzinfo=UTC,
)


class FixedClock:
    def __init__(
        self,
        value=T0,
    ):
        self.value = value

    def now(self):
        return self.value


def metadata(
    *,
    global_hash="c" * 64,
    pln=True,
):
    return SimpleNamespace(
        schema="phase10-accounting-runtime-v1",
        execution_config_hash="a" * 64,
        base_global_config_hash="b" * 64,
        global_config_hash=global_hash,
        asset_registry_hash="d" * 64,
        paper_mode="realistic_paper",
        feature_flags={
            "AL_TRADING_REALISTIC_V2_ENABLED": True,
            "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED": True,
            "AL_TRADING_FX_ENABLED": True,
            "AL_TRADING_PLN_ACCOUNTING_ENABLED": pln,
        },
        runtime_policy={
            "schema": "phase10-accounting-runtime-v1",
            "realized_market_max_age_seconds": 7200.0,
            "realized_daily_reference_max_age_days": 7,
            "fx_prefetch_timeout_seconds": 4.0,
            "fx_prefetch_max_workers": 3,
            "cycle_timeout_seconds": 20.0,
        },
        limitations=(),
    )


def test_append_and_read_round_trip(tmp_path):
    path = (
        tmp_path
        / "phase10_startup_metadata.jsonl"
    )

    store = (
        StartupMetadataJournal(
            path,
            clock=FixedClock(),
        )
    )

    written = store.append(
        metadata()
    )

    assert path.exists()
    assert (
        written["journal_schema"]
        == STARTUP_METADATA_JOURNAL_SCHEMA
    )
    assert (
        written["startup_timestamp_utc"]
        == "2026-09-17T18:30:00.000000Z"
    )
    assert len(
        written["record_hash"]
    ) == 64

    records = (
        store.read_records()
    )

    assert len(
        records
    ) == 1

    assert (
        records[0][
            "global_config_hash"
        ]
        == "c" * 64
    )

    assert (
        records[0][
            "feature_flags"
        ][
            "AL_TRADING_PLN_ACCOUNTING_ENABLED"
        ]
        is True
    )


def test_second_append_preserves_first_record(tmp_path):
    path = (
        tmp_path
        / "phase10_startup_metadata.jsonl"
    )

    store1 = (
        StartupMetadataJournal(
            path,
            clock=FixedClock(
                T0
            ),
        )
    )

    first = store1.append(
        metadata(
            global_hash="c" * 64
        )
    )

    first_bytes = (
        path.read_bytes()
    )

    store2 = (
        StartupMetadataJournal(
            path,
            clock=FixedClock(
                T0
                + timedelta(
                    minutes=1
                )
            ),
        )
    )

    second = store2.append(
        metadata(
            global_hash="e" * 64
        )
    )

    all_bytes = (
        path.read_bytes()
    )

    assert all_bytes.startswith(
        first_bytes
    )

    records = (
        store2.read_records()
    )

    assert len(
        records
    ) == 2

    assert (
        records[0][
            "record_hash"
        ]
        == first[
            "record_hash"
        ]
    )

    assert (
        records[1][
            "record_hash"
        ]
        == second[
            "record_hash"
        ]
    )

    assert (
        records[0][
            "global_config_hash"
        ]
        == "c" * 64
    )

    assert (
        records[1][
            "global_config_hash"
        ]
        == "e" * 64
    )


def test_tampered_record_fails_closed(tmp_path):
    path = (
        tmp_path
        / "phase10_startup_metadata.jsonl"
    )

    store = (
        StartupMetadataJournal(
            path,
            clock=FixedClock(),
        )
    )

    store.append(
        metadata()
    )

    text = path.read_text(
        encoding="utf-8"
    )

    path.write_text(
        text.replace(
            '"paper_mode":"realistic_paper"',
            '"paper_mode":"tampered"',
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        StartupMetadataStoreError,
        match="STARTUP_METADATA_RECORD_HASH_MISMATCH",
    ):
        store.read_records()


def test_naive_clock_timestamp_fails_closed(tmp_path):
    path = (
        tmp_path
        / "phase10_startup_metadata.jsonl"
    )

    naive = datetime(
        2026,
        9,
        17,
        18,
        30,
    )

    store = (
        StartupMetadataJournal(
            path,
            clock=FixedClock(
                naive
            ),
        )
    )

    with pytest.raises(
        StartupMetadataStoreError,
        match="timezone-aware",
    ):
        store.append(
            metadata()
        )

    assert not path.exists()


def test_invalid_global_hash_fails_before_file_creation(tmp_path):
    path = (
        tmp_path
        / "phase10_startup_metadata.jsonl"
    )

    store = (
        StartupMetadataJournal(
            path,
            clock=FixedClock(),
        )
    )

    with pytest.raises(
        StartupMetadataStoreError,
        match="global_config_hash",
    ):
        store.append(
            metadata(
                global_hash="bad"
            )
        )

    assert not path.exists()


def test_non_boolean_feature_flag_fails_closed(tmp_path):
    path = (
        tmp_path
        / "phase10_startup_metadata.jsonl"
    )

    value = metadata()

    value.feature_flags = {
        **value.feature_flags,
        "AL_TRADING_FX_ENABLED": 1,
    }

    store = (
        StartupMetadataJournal(
            path,
            clock=FixedClock(),
        )
    )

    with pytest.raises(
        StartupMetadataStoreError,
        match="feature flag values must be bool",
    ):
        store.append(
            value
        )

    assert not path.exists()


def test_corrupt_json_line_fails_closed(tmp_path):
    path = (
        tmp_path
        / "phase10_startup_metadata.jsonl"
    )

    path.write_text(
        '{"broken":\n',
        encoding="utf-8",
    )

    store = (
        StartupMetadataJournal(
            path,
            clock=FixedClock(),
        )
    )

    with pytest.raises(
        StartupMetadataStoreError,
        match="STARTUP_METADATA_JSON_INVALID",
    ):
        store.read_records()
