from __future__ import annotations

import argparse
from pathlib import Path

from src.persistence.sqlite_application_binding import (
    Phase14ApplicationBindingError,
    build_phase14_application_context,
)
from src.persistence.sqlite_production_application_provider import (
    Phase14ProductionApplicationProviderError,
    build_phase14_production_application_inputs,
)
from src.persistence.sqlite_cutover_dependencies import (
    make_phase14_sqlite_bundle_kwargs_provider,
)
from src.persistence.sqlite_cutover_factory import (
    Phase14CutoverFactoryError,
    build_phase14_runtime,
)
from src.persistence.sqlite_cutover_seam import (
    CutoverMode,
    SQLiteCutoverSeamError,
    select_runtime_construction,
)


EXIT_CONFIRMATION_REQUIRED = 4
EXIT_PREFLIGHT_FAILED = 5
EXIT_DEPENDENCIES_REQUIRED = 6
EXIT_CONSTRUCTION_FAILED = 7
EXIT_APPLICATION_BINDING_FAILED = 8
EXIT_PRODUCTION_BINDING_FAILED = 9


def _parser():
    parser = argparse.ArgumentParser(
        description=(
            "Phase 14 opt-in SQLite cutover construction preflight. "
            "Construction only. Never runs a paper cycle."
        )
    )

    parser.add_argument(
        "--mode",
        choices=(
            CutoverMode.LEGACY.value,
            CutoverMode.SQLITE.value,
        ),
        default=CutoverMode.LEGACY.value,
    )

    parser.add_argument(
        "--sqlite-db",
        default=None,
    )

    parser.add_argument(
        "--live-db",
        default="data/live/trading.db",
    )

    parser.add_argument(
        "--confirm-temp-sqlite-construction",
        action="store_true",
        help=(
            "Explicitly confirm TEMP/TEST SQLite construction. "
            "Does not authorize data/live, HALT clear or run_cycle."
        ),
    )

    return parser


def _print_safe_footer(
    *,
    constructed,
    closed,
):
    print(
        "SQLITE CONSTRUCTED: "
        + (
            "YES"
            if constructed
            else "NO"
        )
    )

    print(
        "SQLITE BUNDLE CLOSED: "
        + (
            "YES"
            if closed
            else "NO"
        )
    )

    print(
        "PAPER CYCLE: NOT RUN"
    )
    print(
        "HALT CLEAR: NOT REQUESTED"
    )
    print(
        "REAL ORDER PATH: NOT USED"
    )


def _validate_sqlite_path_only(
    *,
    sqlite_database_path,
    live_database_path,
):
    """
    Run the A.2 path gate before dependency acquisition.

    The dummy SQLite builder does not open either database.
    """

    return select_runtime_construction(
        mode=CutoverMode.SQLITE,
        legacy_builder=lambda: None,
        sqlite_builder=lambda **kwargs: None,
        sqlite_database_path=sqlite_database_path,
        live_database_path=live_database_path,
    )


def main(
    argv=None,
    *,
    sqlite_bundle_kwargs_provider=None,
    paper_dependency_context=None,
    application_binding_inputs=None,
    production_binding_inputs=None,
):
    args = _parser().parse_args(
        argv
    )

    print(
        "PHASE 14 SQLITE CUTOVER ENTRYPOINT"
    )
    print(
        "CONSTRUCTION ONLY"
    )
    print(
        "CUTOVER MODE: "
        + args.mode.upper()
    )

    if args.mode == CutoverMode.LEGACY.value:
        selection = build_phase14_runtime(
            mode=CutoverMode.LEGACY,
            legacy_builder=lambda: None,
            sqlite_database_path=None,
            live_database_path=args.live_db,
            sqlite_bundle_kwargs=None,
        )

        assert (
            selection.mode
            is CutoverMode.LEGACY
        )

        _print_safe_footer(
            constructed=False,
            closed=False,
        )

        return 0

    if not args.confirm_temp_sqlite_construction:
        print(
            "EXPLICIT TEMP SQLITE CONSTRUCTION "
            "CONFIRMATION REQUIRED"
        )

        _print_safe_footer(
            constructed=False,
            closed=False,
        )

        return EXIT_CONFIRMATION_REQUIRED

    try:
        preflight = _validate_sqlite_path_only(
            sqlite_database_path=(
                args.sqlite_db
            ),
            live_database_path=(
                args.live_db
            ),
        )
    except (
        SQLiteCutoverSeamError,
        TypeError,
        OSError,
    ) as exc:
        print(
            "CUTOVER PREFLIGHT FAILED: "
            + str(exc)
        )

        _print_safe_footer(
            constructed=False,
            closed=False,
        )

        return EXIT_PREFLIGHT_FAILED

    assert (
        preflight.mode
        is CutoverMode.SQLITE
    )

    candidate = Path(
        preflight.sqlite_database_path
    ).resolve()

    live = Path(
        args.live_db
    ).resolve()

    if (
        sqlite_bundle_kwargs_provider is None
        and paper_dependency_context is None
        and application_binding_inputs is None
        and production_binding_inputs is not None
    ):
        try:
            application_binding_inputs = (
                build_phase14_production_application_inputs(
                    production_binding_inputs
                )
            )
        except (
            Phase14ProductionApplicationProviderError,
            TypeError,
            ValueError,
        ) as exc:
            print(
                "PRODUCTION BINDING FAILED: "
                + str(exc)
            )

            _print_safe_footer(
                constructed=False,
                closed=False,
            )

            return EXIT_PRODUCTION_BINDING_FAILED

        print(
            "PRODUCTION BINDING: PASS"
        )

    if (
        sqlite_bundle_kwargs_provider is None
        and paper_dependency_context is None
        and application_binding_inputs is not None
    ):
        try:
            paper_dependency_context = (
                build_phase14_application_context(
                    application_binding_inputs
                )
            )
        except (
            Phase14ApplicationBindingError,
            TypeError,
            ValueError,
        ) as exc:
            print(
                "APPLICATION BINDING FAILED: "
                + str(exc)
            )

            _print_safe_footer(
                constructed=False,
                closed=False,
            )

            return EXIT_APPLICATION_BINDING_FAILED

        print(
            "APPLICATION BINDING: PASS"
        )

    if (
        sqlite_bundle_kwargs_provider is None
        and paper_dependency_context is not None
    ):
        sqlite_bundle_kwargs_provider = (
            make_phase14_sqlite_bundle_kwargs_provider(
                paper_dependency_context
            )
        )

    if not callable(
        sqlite_bundle_kwargs_provider
    ):
        print(
            "SQLITE BUNDLE DEPENDENCY PROVIDER REQUIRED"
        )

        _print_safe_footer(
            constructed=False,
            closed=False,
        )

        return EXIT_DEPENDENCIES_REQUIRED

    try:
        bundle_kwargs = (
            sqlite_bundle_kwargs_provider(
                database_path=candidate,
                live_database_path=live,
            )
        )

        selection = build_phase14_runtime(
            mode=CutoverMode.SQLITE,
            legacy_builder=lambda: (
                (_ for _ in ())
                .throw(
                    AssertionError(
                        "legacy builder must not run in sqlite mode"
                    )
                )
            ),
            sqlite_database_path=candidate,
            live_database_path=live,
            sqlite_bundle_kwargs=bundle_kwargs,
        )
    except (
        SQLiteCutoverSeamError,
        Phase14CutoverFactoryError,
        TypeError,
        ValueError,
        RuntimeError,
        OSError,
    ) as exc:
        print(
            "SQLITE CONSTRUCTION FAILED: "
            + str(exc)
        )

        _print_safe_footer(
            constructed=False,
            closed=False,
        )

        return EXIT_CONSTRUCTION_FAILED

    runtime = selection.runtime
    closed = False

    try:
        if not hasattr(
            runtime,
            "close",
        ):
            raise RuntimeError(
                "constructed SQLite runtime must expose close()"
            )
    except Exception as exc:
        print(
            "SQLITE CONSTRUCTION FAILED: "
            + str(exc)
        )

        _print_safe_footer(
            constructed=False,
            closed=False,
        )

        return EXIT_CONSTRUCTION_FAILED

    try:
        runtime.close()
        closed = True
    except Exception as exc:
        print(
            "SQLITE CONSTRUCTION FAILED DURING CLOSE: "
            + str(exc)
        )

        _print_safe_footer(
            constructed=True,
            closed=False,
        )

        return EXIT_CONSTRUCTION_FAILED

    _print_safe_footer(
        constructed=True,
        closed=closed,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
