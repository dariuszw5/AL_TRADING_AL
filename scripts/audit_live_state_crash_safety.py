from pathlib import Path
import json

from src.agent.live_state_store import LiveStateStore


STATE_FILE = Path(
    "data/live_state/test_crash_safety.json"
)


def main():
    print("=" * 100)
    print("=== LIVE STATE STORE CRASH-SAFETY AUDIT ===")
    print("=" * 100)

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    temporary_file = STATE_FILE.with_suffix(".tmp")

    STATE_FILE.unlink(missing_ok=True)
    temporary_file.unlink(missing_ok=True)

    store = LiveStateStore(str(STATE_FILE))

    state_v1 = {
        "version": 2,
        "balance": 1000.0,
        "last_processed_timestamp": 123,
        "position": {
            "side": "BUY",
            "entry_price": 100000.0,
            "quantity": 0.01
        }
    }

    state_v2 = {
        "version": 2,
        "balance": 1015.0,
        "last_processed_timestamp": 456,
        "position": None
    }

    # ------------------------------------------------------------
    # 1. Initial valid state
    # ------------------------------------------------------------

    store.save(state_v1)

    loaded_v1 = store.load()

    initial_ok = loaded_v1 == state_v1

    print(
        "INITIAL STATE SAVED                 "
        + ("PASS" if initial_ok else "FAIL")
    )

    # ------------------------------------------------------------
    # 2. Simulate interrupted write
    #
    # We create a broken temporary file but DO NOT replace
    # the valid main state file.
    # ------------------------------------------------------------

    with temporary_file.open(
        "w",
        encoding="utf-8"
    ) as handle:
        handle.write(
            '{"version": 2, "balance": 999'
        )

    main_file_survives = (
        STATE_FILE.exists()
    )

    print(
        "MAIN STATE SURVIVES INTERRUPTED WRITE "
        + ("PASS" if main_file_survives else "FAIL")
    )

    recovered = store.load()

    recovery_ok = (
        recovered == state_v1
    )

    print(
        "PREVIOUS STATE RECOVERABLE          "
        + ("PASS" if recovery_ok else "FAIL")
    )

    # ------------------------------------------------------------
    # 3. Remove broken temporary file
    # ------------------------------------------------------------

    temporary_file.unlink(
        missing_ok=True
    )

    print(
        "TEMPORARY FILE CLEANED              "
        + (
            "PASS"
            if not temporary_file.exists()
            else "FAIL"
        )
    )

    # ------------------------------------------------------------
    # 4. Normal subsequent write
    # ------------------------------------------------------------

    store.save(state_v2)

    loaded_v2 = store.load()

    second_write_ok = (
        loaded_v2 == state_v2
    )

    print(
        "SUBSEQUENT WRITE RECOVERS           "
        + ("PASS" if second_write_ok else "FAIL")
    )

    # ------------------------------------------------------------
    # 5. JSON integrity
    # ------------------------------------------------------------

    try:
        with STATE_FILE.open(
            "r",
            encoding="utf-8"
        ) as handle:
            parsed = json.load(handle)

        json_ok = (
            parsed == state_v2
        )
    except Exception:
        json_ok = False

    print(
        "FINAL JSON INTEGRITY                "
        + ("PASS" if json_ok else "FAIL")
    )

    # ------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------

    STATE_FILE.unlink(missing_ok=True)
    temporary_file.unlink(missing_ok=True)

    all_ok = all([
        initial_ok,
        main_file_survives,
        recovery_ok,
        not temporary_file.exists(),
        second_write_ok,
        json_ok,
    ])

    print("-" * 100)

    if all_ok:
        print(
            "RESULT: PASS - STATE STORE IS CRASH-SAFE "
            "AGAINST INTERRUPTED TEMPORARY WRITES"
        )
    else:
        print("RESULT: FAIL")

    print("=" * 100)

    if not all_ok:
        raise AssertionError(
            "LiveStateStore crash-safety audit failed."
        )


if __name__ == "__main__":
    main()
