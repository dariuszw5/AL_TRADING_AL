from __future__ import annotations

from src.accounting.runtime_integration import (
    Phase09AccountingRuntime,
)


ENTRY_EXECUTION_RECOVERY_FROM_JOURNAL = (
    "ENTRY_EXECUTION_RECOVERY_FROM_JOURNAL"
)


class JournalEntryExecutionResolverError(
    ValueError
):
    pass


def _required_text(
    value,
    field_name,
):
    if value is None:
        raise JournalEntryExecutionResolverError(
            f"{field_name} is required"
        )

    result = str(
        value
    ).strip()

    if not result:
        raise JournalEntryExecutionResolverError(
            f"{field_name} is required"
        )

    return result


def _enum_text(
    value,
):
    raw = getattr(
        value,
        "value",
        value,
    )

    return str(
        raw
    ).strip()


class JournalEntryExecutionResolver:
    """
    Read-only resolver for a full entry Execution already persisted in
    the existing append-only REALISTIC_V2 execution journal.

    The resolver never reconstructs execution evidence from Position.
    It returns only an exact committed ENTRY execution whose execution_id
    and asset identity match the persisted Position contract.
    """

    def __init__(
        self,
        journal,
    ):
        if journal is None:
            raise TypeError(
                "journal is required"
            )

        committed_results = getattr(
            journal,
            "committed_results",
            None,
        )

        if not callable(
            committed_results
        ):
            raise TypeError(
                "journal.committed_results is required"
            )

        self.journal = journal

    def __call__(
        self,
        *,
        asset_id,
        position,
        entry_execution_id,
    ):
        asset_id = _required_text(
            asset_id,
            "asset_id",
        )

        entry_execution_id = _required_text(
            entry_execution_id,
            "entry_execution_id",
        )

        if position is None:
            raise JournalEntryExecutionResolverError(
                "position is required"
            )

        position_asset = _required_text(
            getattr(
                position,
                "asset_id",
                None,
            ),
            "position.asset_id",
        )

        position_entry_execution_id = (
            _required_text(
                getattr(
                    position,
                    "entry_execution_id",
                    None,
                ),
                "position.entry_execution_id",
            )
        )

        if position_asset != asset_id:
            raise JournalEntryExecutionResolverError(
                "ENTRY_EXECUTION_POSITION_ASSET_MISMATCH"
            )

        if (
            position_entry_execution_id
            != entry_execution_id
        ):
            raise JournalEntryExecutionResolverError(
                "ENTRY_EXECUTION_POSITION_ID_MISMATCH"
            )

        matches = []

        for broker_result in (
            self.journal
            .committed_results()
        ):
            execution = getattr(
                broker_result,
                "execution",
                None,
            )

            if execution is None:
                continue

            execution_id = getattr(
                execution,
                "execution_id",
                None,
            )

            if (
                execution_id is None
                or str(
                    execution_id
                ) != entry_execution_id
            ):
                continue

            order = getattr(
                broker_result,
                "order",
                None,
            )

            if order is None:
                raise JournalEntryExecutionResolverError(
                    "ENTRY_EXECUTION_JOURNAL_ORDER_REQUIRED"
                )

            status = _enum_text(
                getattr(
                    broker_result,
                    "status",
                    "",
                )
            )

            intent = _enum_text(
                getattr(
                    order,
                    "intent",
                    "",
                )
            )

            order_asset = _required_text(
                getattr(
                    order,
                    "asset_id",
                    None,
                ),
                "broker_result.order.asset_id",
            )

            execution_asset = (
                _required_text(
                    getattr(
                        execution,
                        "asset_id",
                        None,
                    ),
                    "execution.asset_id",
                )
            )

            if status != "FILLED":
                raise JournalEntryExecutionResolverError(
                    "ENTRY_EXECUTION_JOURNAL_NOT_FILLED"
                )

            if intent != "ENTRY":
                raise JournalEntryExecutionResolverError(
                    "ENTRY_EXECUTION_JOURNAL_NOT_ENTRY"
                )

            if (
                order_asset != asset_id
                or execution_asset
                != asset_id
            ):
                raise JournalEntryExecutionResolverError(
                    "ENTRY_EXECUTION_JOURNAL_ASSET_MISMATCH"
                )

            matches.append(
                execution
            )

        if not matches:
            return None

        if len(
            matches
        ) != 1:
            raise JournalEntryExecutionResolverError(
                "ENTRY_EXECUTION_JOURNAL_DUPLICATE"
            )

        return matches[0]


class JournalBackedPhase09AccountingRuntime(
    Phase09AccountingRuntime
):
    """
    Phase 09 accounting runtime with an optional read-only journal
    fallback for the complete entry Execution.

    In-process behavior remains unchanged: the in-memory cache is used
    first. The journal is consulted only when the exact cached entry
    Execution is missing.
    """

    def __init__(
        self,
        *,
        entry_execution_resolver=None,
        **kwargs,
    ):
        super().__init__(
            **kwargs
        )

        if (
            entry_execution_resolver
            is not None
            and not callable(
                entry_execution_resolver
            )
        ):
            raise TypeError(
                "entry_execution_resolver must be callable"
            )

        self.entry_execution_resolver = (
            entry_execution_resolver
        )

    def _book_realized(
        self,
        *,
        asset_id,
        position,
        exit_execution,
    ):
        entry_execution_id = (
            _required_text(
                getattr(
                    position,
                    "entry_execution_id",
                    None,
                ),
                "position.entry_execution_id",
            )
        )

        if (
            entry_execution_id
            in self._entry_executions
        ):
            return super()._book_realized(
                asset_id=asset_id,
                position=position,
                exit_execution=exit_execution,
            )

        if (
            self.entry_execution_resolver
            is None
        ):
            return super()._book_realized(
                asset_id=asset_id,
                position=position,
                exit_execution=exit_execution,
            )

        recovered = (
            self.entry_execution_resolver(
                asset_id=asset_id,
                position=position,
                entry_execution_id=(
                    entry_execution_id
                ),
            )
        )

        if recovered is None:
            return super()._book_realized(
                asset_id=asset_id,
                position=position,
                exit_execution=exit_execution,
            )

        recovered_id = _required_text(
            getattr(
                recovered,
                "execution_id",
                None,
            ),
            "recovered.execution_id",
        )

        if (
            recovered_id
            != entry_execution_id
        ):
            raise JournalEntryExecutionResolverError(
                "ENTRY_EXECUTION_RECOVERY_ID_MISMATCH"
            )

        self._entry_executions[
            entry_execution_id
        ] = recovered

        try:
            return super()._book_realized(
                asset_id=asset_id,
                position=position,
                exit_execution=exit_execution,
            )

        finally:
            self._entry_executions.pop(
                entry_execution_id,
                None,
            )
