from __future__ import annotations

from dataclasses import dataclass

from src.accounting.feature_flags import PlnAccountingFeatureFlags
from src.config_fingerprint import build_phase09_feature_flags
from src.execution.feature_flags import RealisticV2FeatureFlags
from src.fx.feature_flags import FxFeatureFlags


@dataclass(frozen=True)
class Phase09RuntimeFeatureFlags:
    execution: RealisticV2FeatureFlags
    fx: FxFeatureFlags
    pln_accounting: PlnAccountingFeatureFlags

    def fingerprint_flags(self):
        return build_phase09_feature_flags(
            realistic_v2_enabled=self.execution.enabled,
            realistic_v2_execution_enabled=(
                self.execution.execution_enabled
            ),
            fx_enabled=self.fx.enabled,
            pln_accounting_enabled=self.pln_accounting.enabled,
        )


def resolve_phase09_runtime_flags(
    *,
    env=None,
    execution_flags=None,
):
    if execution_flags is None:
        execution_flags = RealisticV2FeatureFlags.from_env(env)

    if not isinstance(
        execution_flags,
        RealisticV2FeatureFlags,
    ):
        raise TypeError(
            "execution_flags must be RealisticV2FeatureFlags"
        )

    return Phase09RuntimeFeatureFlags(
        execution=execution_flags,
        fx=FxFeatureFlags.from_env(env),
        pln_accounting=PlnAccountingFeatureFlags.from_env(env),
    )