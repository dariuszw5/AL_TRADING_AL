from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from src.accounting.runtime_bridge import (
    ACCOUNTING_PERSISTENCE_LIMITATION,
    Phase09RuntimeAccountingBridge,
    RuntimeAccountingBridgeError,
)


ACCOUNTING_FAIL_CLOSED = "ACCOUNTING_FAIL_CLOSED"
ENTRY_EXECUTION_CACHE_IN_MEMORY_ONLY = (
    "ENTRY_EXECUTION_CACHE_IN_MEMORY_ONLY"
)
PORTFOLIO_PARTIAL_ACCOUNTING_BLOCKED = (
    "PORTFOLIO_PARTIAL_ACCOUNTING_BLOCKED"
)


def _required_callable(value, field_name):
    if not callable(value):
        raise TypeError(
            f"{field_name} must be callable"
        )

    return value


def _required_text(value, field_name):
    if value is None:
        raise ValueError(
            f"{field_name} is required"
        )

    result = str(value).strip()

    if not result:
        raise ValueError(
            f"{field_name} is required"
        )

    return result


class SnapshotCaptureDecisionProvider:
    """
    Transparent decision-provider wrapper.

    It captures only the snapshot that the existing REALISTIC_V2
    runtime already passes to the decision provider. It does not
    change the returned decision.
    """

    def __init__(self, delegate):
        self.delegate = _required_callable(
            delegate,
            "delegate",
        )
        self._snapshots = {}

    def clear(self):
        self._snapshots.clear()

    def snapshot_for(self, asset_id):
        return self._snapshots.get(
            str(asset_id)
        )

    def __call__(
        self,
        *,
        asset_id,
        snapshot,
        position,
    ):
        self._snapshots[
            str(asset_id)
        ] = snapshot

        return self.delegate(
            asset_id=asset_id,
            snapshot=snapshot,
            position=position,
        )


@dataclass(frozen=True)
class RuntimeAccountingAssetResult:
    asset_id: str
    mtm_record: object | None = None
    realized_result: object | None = None
    error: str | None = None
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimeAccountingCycleResult:
    execution_cycle: object
    accounting_results: object
    portfolio_snapshot: object | None
    limitations: tuple[str, ...]


class Phase09AccountingRuntime:
    """
    Additive accounting wrapper around the existing REALISTIC_V2 runtime.

    Execution happens first inside the unchanged runtime. Accounting is
    post-cycle only. Accounting failures never rewrite the execution
    cycle and are returned per asset as fail-closed accounting results.

    The entry Execution cache is intentionally in-memory only. After a
    restart, realized accounting fails closed when the complete original
    entry Execution is unavailable.
    """

    def __init__(
        self,
        *,
        runtime,
        accounting_bridge,
        snapshot_capture,
        fx_conversion_resolver,
        estimated_exit_fee_resolver,
        realized_quotes_resolver=None,
        cash_pln_resolver=None,
    ):
        if runtime is None:
            raise TypeError(
                "runtime is required"
            )

        if not isinstance(
            accounting_bridge,
            Phase09RuntimeAccountingBridge,
        ):
            raise TypeError(
                "accounting_bridge must be "
                "Phase09RuntimeAccountingBridge"
            )

        if not isinstance(
            snapshot_capture,
            SnapshotCaptureDecisionProvider,
        ):
            raise TypeError(
                "snapshot_capture must be "
                "SnapshotCaptureDecisionProvider"
            )

        runtime_decision_provider = getattr(
            runtime,
            "decision_provider",
            snapshot_capture,
        )

        if (
            runtime_decision_provider
            is not snapshot_capture
        ):
            raise ValueError(
                "RUNTIME_DECISION_PROVIDER_NOT_CAPTURE_WRAPPER"
            )

        self.runtime = runtime
        self.accounting_bridge = (
            accounting_bridge
        )

        self.snapshot_capture = (
            snapshot_capture
        )

        self.fx_conversion_resolver = (
            _required_callable(
                fx_conversion_resolver,
                "fx_conversion_resolver",
            )
        )

        self.estimated_exit_fee_resolver = (
            _required_callable(
                estimated_exit_fee_resolver,
                "estimated_exit_fee_resolver",
            )
        )

        if (
            realized_quotes_resolver
            is not None
        ):
            _required_callable(
                realized_quotes_resolver,
                "realized_quotes_resolver",
            )

        if cash_pln_resolver is not None:
            _required_callable(
                cash_pln_resolver,
                "cash_pln_resolver",
            )

        self.realized_quotes_resolver = (
            realized_quotes_resolver
        )

        self.cash_pln_resolver = (
            cash_pln_resolver
        )

        self._entry_executions = {}

    @property
    def entry_execution_ids(self):
        return tuple(
            sorted(
                self._entry_executions
            )
        )

    @staticmethod
    def _broker_result(
        asset_result,
    ):
        return getattr(
            asset_result,
            "broker_result",
            None,
        )

    @staticmethod
    def _execution(
        broker_result,
    ):
        if broker_result is None:
            return None

        return getattr(
            broker_result,
            "execution",
            None,
        )

    @staticmethod
    def _broker_position(
        broker_result,
    ):
        if broker_result is None:
            return None

        return getattr(
            broker_result,
            "position",
            None,
        )

    def _cache_entry_execution(
        self,
        *,
        open_position,
        execution,
    ):
        if (
            open_position is None
            or execution is None
        ):
            return False

        entry_execution_id = getattr(
            open_position,
            "entry_execution_id",
            None,
        )

        execution_id = getattr(
            execution,
            "execution_id",
            None,
        )

        if (
            entry_execution_id is None
            or execution_id is None
            or str(entry_execution_id)
            != str(execution_id)
        ):
            return False

        self._entry_executions[
            str(execution_id)
        ] = execution

        return True

    def _realized_candidate(
        self,
        *,
        broker_position,
        execution,
    ):
        if (
            broker_position is None
            or execution is None
        ):
            return False

        if getattr(
            broker_position,
            "closed_at",
            None,
        ) is None:
            return False

        exit_execution_id = getattr(
            broker_position,
            "exit_execution_id",
            None,
        )

        execution_id = getattr(
            execution,
            "execution_id",
            None,
        )

        return (
            exit_execution_id is not None
            and execution_id is not None
            and str(exit_execution_id)
            == str(execution_id)
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

        entry_execution = (
            self._entry_executions.get(
                entry_execution_id
            )
        )

        if entry_execution is None:
            raise RuntimeAccountingBridgeError(
                "ENTRY_EXECUTION_REQUIRED"
            )

        if (
            self.realized_quotes_resolver
            is None
        ):
            raise RuntimeAccountingBridgeError(
                "REALIZED_FX_QUOTES_RESOLVER_REQUIRED"
            )

        fx_quotes = (
            self.realized_quotes_resolver(
                asset_id=asset_id,
                position=position,
                entry_execution=(
                    entry_execution
                ),
                exit_execution=(
                    exit_execution
                ),
            )
        )

        result = (
            self.accounting_bridge
            .book_realized(
                position=position,
                entry_execution=(
                    entry_execution
                ),
                exit_execution=(
                    exit_execution
                ),
                fx_quotes=tuple(
                    fx_quotes
                ),
            )
        )

        self._entry_executions.pop(
            entry_execution_id,
            None,
        )

        return result

    def _mark_open_position(
        self,
        *,
        asset_id,
        position,
    ):
        snapshot = (
            self.snapshot_capture
            .snapshot_for(
                asset_id
            )
        )

        if snapshot is None:
            raise RuntimeAccountingBridgeError(
                "ACCOUNTING_MARKET_SNAPSHOT_REQUIRED"
            )

        fx_conversion = (
            self.fx_conversion_resolver(
                asset_id=asset_id,
                position=position,
                market_snapshot=snapshot,
            )
        )

        estimated_exit_fee_native = (
            self.estimated_exit_fee_resolver(
                asset_id=asset_id,
                position=position,
                market_snapshot=snapshot,
            )
        )

        return (
            self.accounting_bridge
            .mark_position(
                position=position,
                market_snapshot=snapshot,
                fx_conversion=fx_conversion,
                estimated_exit_fee_native=(
                    estimated_exit_fee_native
                ),
            )
        )

    def _portfolio(
        self,
        *,
        asset_ids,
        accounting_results,
    ):
        if self.cash_pln_resolver is None:
            return (
                None,
                (),
            )

        open_positions = {
            str(asset_id): position
            for asset_id, position
            in self.runtime.positions.items()
            if str(asset_id)
            in set(asset_ids)
        }

        mtm_records = []

        for asset_id in open_positions:
            item = accounting_results.get(
                asset_id
            )

            if (
                item is None
                or item.error is not None
                or item.mtm_record is None
            ):
                return (
                    None,
                    (
                        PORTFOLIO_PARTIAL_ACCOUNTING_BLOCKED,
                    ),
                )

            mtm_records.append(
                item.mtm_record
            )

        cash_pln = (
            self.cash_pln_resolver()
        )

        return (
            self.accounting_bridge
            .portfolio_snapshot(
                cash_pln=cash_pln,
                mtm_records=tuple(
                    mtm_records
                ),
            ),
            (),
        )

    def run_cycle(
        self,
        asset_ids,
    ):
        asset_ids = tuple(
            str(asset_id)
            for asset_id in asset_ids
        )

        self.snapshot_capture.clear()

        execution_cycle = (
            self.runtime.run_cycle(
                asset_ids
            )
        )

        accounting_results = {}

        for asset_id in asset_ids:
            asset_result = (
                execution_cycle.results.get(
                    asset_id
                )
            )

            if asset_result is None:
                accounting_results[
                    asset_id
                ] = (
                    RuntimeAccountingAssetResult(
                        asset_id=asset_id,
                        error=(
                            "RUNTIME_ASSET_RESULT_MISSING"
                        ),
                        limitations=(
                            ACCOUNTING_FAIL_CLOSED,
                        ),
                    )
                )

                continue

            broker_result = (
                self._broker_result(
                    asset_result
                )
            )

            execution = (
                self._execution(
                    broker_result
                )
            )

            broker_position = (
                self._broker_position(
                    broker_result
                )
            )

            open_position = (
                self.runtime.positions.get(
                    asset_id
                )
            )

            limitations = []
            mtm_record = None
            realized_result = None

            try:
                cached = (
                    self._cache_entry_execution(
                        open_position=(
                            open_position
                        ),
                        execution=execution,
                    )
                )

                if cached:
                    limitations.append(
                        ENTRY_EXECUTION_CACHE_IN_MEMORY_ONLY
                    )

                if self._realized_candidate(
                    broker_position=(
                        broker_position
                    ),
                    execution=execution,
                ):
                    realized_result = (
                        self._book_realized(
                            asset_id=asset_id,
                            position=(
                                broker_position
                            ),
                            exit_execution=(
                                execution
                            ),
                        )
                    )

                    limitations.extend(
                        realized_result.limitations
                    )

                if open_position is not None:
                    mtm_record = (
                        self._mark_open_position(
                            asset_id=asset_id,
                            position=(
                                open_position
                            ),
                        )
                    )

                accounting_results[
                    asset_id
                ] = (
                    RuntimeAccountingAssetResult(
                        asset_id=asset_id,
                        mtm_record=mtm_record,
                        realized_result=(
                            realized_result
                        ),
                        limitations=tuple(
                            dict.fromkeys(
                                limitations
                            )
                        ),
                    )
                )

            except Exception as exc:
                accounting_results[
                    asset_id
                ] = (
                    RuntimeAccountingAssetResult(
                        asset_id=asset_id,
                        error=(
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        ),
                        limitations=tuple(
                            dict.fromkeys(
                                limitations
                                + [
                                    ACCOUNTING_FAIL_CLOSED,
                                ]
                            )
                        ),
                    )
                )

        portfolio_snapshot, portfolio_limits = (
            self._portfolio(
                asset_ids=asset_ids,
                accounting_results=(
                    accounting_results
                ),
            )
        )

        cycle_limits = list(
            portfolio_limits
        )

        if any(
            item.error is not None
            for item in accounting_results.values()
        ):
            cycle_limits.append(
                ACCOUNTING_FAIL_CLOSED
            )

        if any(
            (
                item.realized_result
                is not None
                and ACCOUNTING_PERSISTENCE_LIMITATION
                in item.limitations
            )
            for item in accounting_results.values()
        ):
            cycle_limits.append(
                ACCOUNTING_PERSISTENCE_LIMITATION
            )

        return RuntimeAccountingCycleResult(
            execution_cycle=execution_cycle,
            accounting_results=(
                MappingProxyType(
                    dict(
                        accounting_results
                    )
                )
            ),
            portfolio_snapshot=(
                portfolio_snapshot
            ),
            limitations=tuple(
                dict.fromkeys(
                    cycle_limits
                )
            ),
        )
