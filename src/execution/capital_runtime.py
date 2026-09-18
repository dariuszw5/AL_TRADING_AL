from __future__ import annotations

from dataclasses import dataclass

from src.accounting.cash_runtime import Phase11CashRuntimeBundle, wire_phase11_cash_runtime
from src.execution.capital_admission import CashBackedCapitalAdmissionPolicy
from src.execution.capital_exposure import BtcUsdtLongExposureCalculator
from src.execution.capital_feature_flags import CapitalAdmissionFeatureFlags
from src.execution.capital_startup import (
    Phase12CapitalAdmissionPolicy,
    Phase12StartupMetadata,
    build_phase12_startup_metadata,
    require_phase12_capital_flag,
)


@dataclass(frozen=True)
class CapitalAdmissionGateResult:
    allowed: bool
    reason: str
    exposure_result: object | None = None
    admission_decision: object | None = None
    error: str | None = None


class Phase12CapitalAdmissionProvider:
    """Controlled BTCUSDT LONG-entry admission provider."""

    def __init__(
        self,
        *,
        cash_pln_resolver,
        fx_quotes_resolver,
        exposure_calculator,
        admission_policy,
        max_exposure_percent,
    ):
        if not callable(cash_pln_resolver):
            raise TypeError("cash_pln_resolver must be callable")
        if not callable(fx_quotes_resolver):
            raise TypeError("fx_quotes_resolver must be callable")
        if not isinstance(exposure_calculator, BtcUsdtLongExposureCalculator):
            raise TypeError("exposure_calculator must be BtcUsdtLongExposureCalculator")
        if not isinstance(admission_policy, CashBackedCapitalAdmissionPolicy):
            raise TypeError("admission_policy must be CashBackedCapitalAdmissionPolicy")

        self.cash_pln_resolver = cash_pln_resolver
        self.fx_quotes_resolver = fx_quotes_resolver
        self.exposure_calculator = exposure_calculator
        self.admission_policy = admission_policy
        self.max_exposure_percent = max_exposure_percent

    def __call__(self, *, asset_id, snapshot, position, decision):
        try:
            settled_cash = self.cash_pln_resolver()
        except Exception as exc:
            admission = self.admission_policy.evaluate_long_entry(
                settled_cash_pln=None,
                proposed_exposure_pln=None,
                max_exposure_percent=self.max_exposure_percent,
            )
            return CapitalAdmissionGateResult(
                allowed=False,
                reason=admission.reason.value,
                admission_decision=admission,
                error=f"{type(exc).__name__}: {exc}",
            )

        try:
            fx_quotes = tuple(self.fx_quotes_resolver())
        except Exception as exc:
            admission = self.admission_policy.evaluate_long_entry(
                settled_cash_pln=settled_cash,
                proposed_exposure_pln=None,
                max_exposure_percent=self.max_exposure_percent,
            )
            return CapitalAdmissionGateResult(
                allowed=False,
                reason=admission.reason.value,
                admission_decision=admission,
                error=f"{type(exc).__name__}: {exc}",
            )

        exposure = self.exposure_calculator.calculate(
            market_snapshot=snapshot,
            quantity=decision.quantity,
            fx_quotes=fx_quotes,
        )

        admission = self.admission_policy.evaluate_long_entry(
            settled_cash_pln=settled_cash,
            proposed_exposure_pln=(exposure.exposure_pln if exposure.available else None),
            max_exposure_percent=self.max_exposure_percent,
        )

        if not exposure.available:
            return CapitalAdmissionGateResult(
                allowed=False,
                reason=exposure.reason.value,
                exposure_result=exposure,
                admission_decision=admission,
                error=exposure.unavailable_detail,
            )

        return CapitalAdmissionGateResult(
            allowed=bool(admission.allowed),
            reason=admission.reason.value,
            exposure_result=exposure,
            admission_decision=admission,
        )


@dataclass(frozen=True)
class Phase12CapitalRuntimeBundle:
    runtime: object
    phase11_bundle: Phase11CashRuntimeBundle
    phase12_metadata: Phase12StartupMetadata
    admission_provider: Phase12CapitalAdmissionProvider


def wire_phase12_capital_runtime(
    *,
    runtime,
    broker,
    runtime_flags,
    phase10_policy,
    cash_ledger,
    realized_journal,
    capital_flags,
    capital_policy,
    clock=None,
    nbp_provider=None,
    yahoo_provider=None,
    coinbase_provider=None,
    assets=None,
):
    if runtime is None:
        raise TypeError("runtime is required")
    if broker is None:
        raise TypeError("broker is required")
    if not isinstance(capital_flags, CapitalAdmissionFeatureFlags):
        raise TypeError("capital_flags must be CapitalAdmissionFeatureFlags")

    require_phase12_capital_flag(capital_flags)

    if not isinstance(capital_policy, Phase12CapitalAdmissionPolicy):
        raise TypeError("capital_policy must be Phase12CapitalAdmissionPolicy")

    if getattr(runtime, "admission_provider", None) is not None:
        raise ValueError("RUNTIME_ALREADY_HAS_ADMISSION_PROVIDER")

    phase11_kwargs = {
        "runtime": runtime,
        "broker": broker,
        "runtime_flags": runtime_flags,
        "policy": phase10_policy,
        "cash_ledger": cash_ledger,
        "realized_journal": realized_journal,
        "clock": clock,
        "nbp_provider": nbp_provider,
        "yahoo_provider": yahoo_provider,
        "coinbase_provider": coinbase_provider,
    }
    if assets is not None:
        phase11_kwargs["assets"] = assets

    phase11_bundle = wire_phase11_cash_runtime(**phase11_kwargs)

    phase12_metadata = build_phase12_startup_metadata(
        phase10_metadata=phase11_bundle.phase10_bundle.startup_metadata,
        capital_flags=capital_flags,
        capital_policy=capital_policy,
    )

    fx_resolver = phase11_bundle.phase10_bundle.wiring.fx_resolver
    exposure_calculator = BtcUsdtLongExposureCalculator(
        slippage_model=broker.slippage_model,
        fx_converter=fx_resolver.converter,
    )
    admission_provider = Phase12CapitalAdmissionProvider(
        cash_pln_resolver=cash_ledger.current_cash_pln,
        fx_quotes_resolver=lambda: fx_resolver.mtm_quotes,
        exposure_calculator=exposure_calculator,
        admission_policy=CashBackedCapitalAdmissionPolicy(),
        max_exposure_percent=capital_policy.max_exposure_percent,
    )

    runtime.admission_provider = admission_provider

    return Phase12CapitalRuntimeBundle(
        runtime=phase11_bundle.runtime,
        phase11_bundle=phase11_bundle,
        phase12_metadata=phase12_metadata,
        admission_provider=admission_provider,
    )
