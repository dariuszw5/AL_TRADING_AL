import json
from datetime import (
    datetime,
    timezone,
)
from types import (
    MappingProxyType,
    SimpleNamespace,
)

import pytest

from src.core.clock import FixedClock
from src.execution.capital_feature_flags import (
    CapitalAdmissionFeatureFlags,
)
from src.execution.capital_startup import (
    Phase12CapitalAdmissionPolicy,
    build_phase12_startup_metadata,
)
from src.execution.capital_startup_store import (
    PHASE12_STARTUP_JOURNAL_SCHEMA,
    Phase12StartupMetadataJournal,
    Phase12StartupMetadataStoreError,
    build_phase12_startup_record,
    verify_phase12_startup_record,
)


NOW = datetime(
    2026,
    9,
    18,
    15,
    30,
    tzinfo=timezone.utc,
)


def phase10_metadata():
    return SimpleNamespace(
        execution_config_hash=(
            "a8c84046f4919a1c39bcaef86e926a2"
            "87240b14359b9b60b7f626252f7c5e781"
        ),
        global_config_hash=(
            "017d9e3ef4fba21bc17102519cf6b499"
            "4dd50ae3f53a4f05b178b5913fd9127d"
        ),
        asset_registry_hash=(
            "71ddae6f81cdd829caf2431881ee513f"
            "0424553c959625f5e843d4cf3e7fc714"
        ),
        paper_mode="realistic_paper",
        feature_flags=MappingProxyType(
            {
                "AL_TRADING_REALISTIC_V2_ENABLED": True,
                "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED": True,
                "AL_TRADING_FX_ENABLED": True,
                "AL_TRADING_PLN_ACCOUNTING_ENABLED": True,
            }
        ),
        runtime_policy=MappingProxyType(
            {
                "schema": "phase10-accounting-runtime-v1",
                "cycle_timeout_seconds": 20.0,
            }
        ),
        limitations=(),
    )


def phase12_metadata():
    return build_phase12_startup_metadata(
        phase10_metadata=phase10_metadata(),
        capital_flags=(
            CapitalAdmissionFeatureFlags(
                enabled=True
            )
        ),
        capital_policy=(
            Phase12CapitalAdmissionPolicy(
                controlled_asset_id="BTCUSDT",
                max_exposure_percent=100.0,
            )
        ),
    )


def test_build_record_contains_both_hash_layers():
    metadata = phase12_metadata()

    record = build_phase12_startup_record(
        metadata,
        startup_timestamp=NOW,
    )

    assert (
        record["journal_schema"]
        == PHASE12_STARTUP_JOURNAL_SCHEMA
    )
    assert (
        record["metadata_schema"]
        == "phase12-capital-admission-v1"
    )
    assert (
        record["execution_config_hash"]
        == metadata.execution_config_hash
    )
    assert (
        record["phase10_global_config_hash"]
        == metadata.phase10_global_config_hash
    )
    assert (
        record["global_config_hash"]
        == metadata.global_config_hash
    )
    assert (
        record["phase12_feature_flags"][
            "AL_TRADING_CAPITAL_ADMISSION_ENABLED"
        ]
        is True
    )


def test_record_hash_verifies():
    record = build_phase12_startup_record(
        phase12_metadata(),
        startup_timestamp=NOW,
    )

    verified = (
        verify_phase12_startup_record(
            record
        )
    )

    assert verified["record_hash"] == record["record_hash"]


def test_tampered_record_is_rejected():
    record = build_phase12_startup_record(
        phase12_metadata(),
        startup_timestamp=NOW,
    )

    tampered = dict(
        record
    )
    tampered["paper_mode"] = "research_paper"

    with pytest.raises(
        Phase12StartupMetadataStoreError,
        match="HASH_MISMATCH",
    ):
        verify_phase12_startup_record(
            tampered
        )


def test_append_and_read_roundtrip(tmp_path):
    journal = Phase12StartupMetadataJournal(
        tmp_path / "phase12_startup_metadata.jsonl",
        clock=FixedClock(NOW),
    )

    written = journal.append(
        phase12_metadata()
    )

    records = journal.read_records()

    assert len(records) == 1
    assert (
        records[0]["record_hash"]
        == written["record_hash"]
    )
    assert (
        records[0]["startup_timestamp_utc"]
        == "2026-09-18T15:30:00.000000Z"
    )


def test_multiple_startups_append_not_overwrite(tmp_path):
    journal = Phase12StartupMetadataJournal(
        tmp_path / "phase12_startup_metadata.jsonl",
        clock=FixedClock(NOW),
    )

    first = journal.append(
        phase12_metadata()
    )
    second = journal.append(
        phase12_metadata()
    )

    records = journal.read_records()

    assert len(records) == 2
    assert records[0]["record_hash"] == first["record_hash"]
    assert records[1]["record_hash"] == second["record_hash"]


def test_missing_file_reads_empty(tmp_path):
    journal = Phase12StartupMetadataJournal(
        tmp_path / "missing.jsonl",
        clock=FixedClock(NOW),
    )

    assert journal.read_records() == ()


def test_invalid_json_fails_closed(tmp_path):
    path = (
        tmp_path
        / "phase12_startup_metadata.jsonl"
    )

    path.write_text(
        "{bad-json}\n",
        encoding="utf-8",
    )

    journal = Phase12StartupMetadataJournal(
        path,
        clock=FixedClock(NOW),
    )

    with pytest.raises(
        Phase12StartupMetadataStoreError,
        match="JSON_INVALID",
    ):
        journal.read_records()


def test_blank_record_fails_closed(tmp_path):
    path = (
        tmp_path
        / "phase12_startup_metadata.jsonl"
    )

    path.write_text(
        "\n",
        encoding="utf-8",
    )

    journal = Phase12StartupMetadataJournal(
        path,
        clock=FixedClock(NOW),
    )

    with pytest.raises(
        Phase12StartupMetadataStoreError,
        match="BLANK_RECORD",
    ):
        journal.read_records()


def test_corrupted_persisted_hash_fails_closed(tmp_path):
    journal = Phase12StartupMetadataJournal(
        tmp_path / "phase12_startup_metadata.jsonl",
        clock=FixedClock(NOW),
    )

    written = dict(
        journal.append(
            phase12_metadata()
        )
    )

    written["record_hash"] = "0" * 64

    journal.path.write_text(
        json.dumps(
            written
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        Phase12StartupMetadataStoreError,
        match="HASH_MISMATCH",
    ):
        journal.read_records()


def test_phase10_and_phase12_feature_flags_are_persisted_separately(tmp_path):
    journal = Phase12StartupMetadataJournal(
        tmp_path / "phase12_startup_metadata.jsonl",
        clock=FixedClock(NOW),
    )

    record = journal.append(
        phase12_metadata()
    )

    assert (
        "AL_TRADING_REALISTIC_V2_ENABLED"
        in record["phase10_feature_flags"]
    )
    assert (
        record["phase12_feature_flags"]
        == {
            "AL_TRADING_CAPITAL_ADMISSION_ENABLED": True
        }
    )


def test_capital_policy_is_persisted_for_audit(tmp_path):
    journal = Phase12StartupMetadataJournal(
        tmp_path / "phase12_startup_metadata.jsonl",
        clock=FixedClock(NOW),
    )

    record = journal.append(
        phase12_metadata()
    )

    policy = record[
        "capital_policy"
    ]

    assert (
        policy["controlled_asset_id"]
        == "BTCUSDT"
    )
    assert (
        policy["capital_source"]
        == "PHASE11_SETTLED_CASH_PLN"
    )
    assert (
        policy["fx_path"]
        == "USDT->USD->PLN"
    )
    assert (
        policy["max_exposure_percent"]
        == 100.0
    )
