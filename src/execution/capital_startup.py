from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from types import MappingProxyType

from src.data.assets import (
    AssetConfig,
)
from src.execution.capital_feature_flags import (
    CapitalAdmissionFeatureFlags,
)


PHASE12_GLOBAL_CONFIG_SCHEMA = (
    "phase12-capital-admission-v1"
)

PHASE12_CAPITAL_ADMISSION_FLAG_NOT_ENABLED = (
    "PHASE12_CAPITAL_ADMISSION_FLAG_NOT_ENABLED"
)

PHASE12_CONTROLLED_ASSET = "BTCUSDT"

PHASE12_CAPITAL_SOURCE = (
    "PHASE11_SETTLED_CASH_PLN"
)

PHASE12_CAPITAL_LIMIT_FORMULA = (
    "max(0,settled_cash_pln)"
    "*max_exposure_percent/100"
)

PHASE12_PROPOSED_EXPOSURE_BASIS = (
    "GROSS_ENTRY_NOTIONAL_PLN"
)

PHASE12_EXECUTION_PRICE_BASIS = (
    "REAL_BOOK_ASK_PLUS_EXISTING_SLIPPAGE"
)

PHASE12_FX_PATH = "USDT->USD->PLN"

PHASE12_FX_FRESHNESS_REQUIRED = "FX_FRESH"

PHASE12_ENTRY_FEE_SEMANTICS = (
    "ENTRY_FEE_SETTLED_AT_REALIZATION"
)


class Phase12StartupPolicyError(
    ValueError
):
    pass


def _sha256_payload(
    payload,
):
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")

    return hashlib.sha256(
        encoded
    ).hexdigest()


def _required_text(
    value,
    field_name,
):
    result = str(
        value
    ).strip()

    if not result:
        raise Phase12StartupPolicyError(
            f"{field_name} is required"
        )

    return result


def _finite_percent(
    value,
):
    try:
        result = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise Phase12StartupPolicyError(
            "max_exposure_percent must be "
            "a finite number in (0, 100]"
        ) from exc

    if (
        not math.isfinite(result)
        or result <= 0
        or result > 100
    ):
        raise Phase12StartupPolicyError(
            "max_exposure_percent must be "
            "a finite number in (0, 100]"
        )

    return result


@dataclass(frozen=True)
class Phase12CapitalAdmissionPolicy:
    controlled_asset_id: str
    max_exposure_percent: float

    capital_source: str = PHASE12_CAPITAL_SOURCE
    capital_limit_formula: str = PHASE12_CAPITAL_LIMIT_FORMULA
    proposed_exposure_basis: str = PHASE12_PROPOSED_EXPOSURE_BASIS
    execution_price_basis: str = PHASE12_EXECUTION_PRICE_BASIS
    fx_path: str = PHASE12_FX_PATH
    fx_freshness_required: str = PHASE12_FX_FRESHNESS_REQUIRED
    entry_fee_semantics: str = PHASE12_ENTRY_FEE_SEMANTICS
    open_mutates_settled_cash: bool = False
    exit_subject_to_capital_admission: bool = False
    margin_model: str = "NONE"
    collateral_model: str = "NONE"
    leverage_model: str = "NONE"
    short_financing_added: bool = False

    def __post_init__(
        self,
    ):
        asset_id = (
            str(self.controlled_asset_id)
            .strip()
            .upper()
        )

        if asset_id != PHASE12_CONTROLLED_ASSET:
            raise Phase12StartupPolicyError(
                "Phase 12 controlled asset "
                "must be BTCUSDT"
            )

        object.__setattr__(
            self,
            "controlled_asset_id",
            asset_id,
        )

        object.__setattr__(
            self,
            "max_exposure_percent",
            _finite_percent(
                self.max_exposure_percent
            ),
        )

        fixed = {
            "capital_source": PHASE12_CAPITAL_SOURCE,
            "capital_limit_formula": PHASE12_CAPITAL_LIMIT_FORMULA,
            "proposed_exposure_basis": PHASE12_PROPOSED_EXPOSURE_BASIS,
            "execution_price_basis": PHASE12_EXECUTION_PRICE_BASIS,
            "fx_path": PHASE12_FX_PATH,
            "fx_freshness_required": PHASE12_FX_FRESHNESS_REQUIRED,
            "entry_fee_semantics": PHASE12_ENTRY_FEE_SEMANTICS,
            "margin_model": "NONE",
            "collateral_model": "NONE",
            "leverage_model": "NONE",
        }

        for field_name, expected in fixed.items():
            actual = getattr(
                self,
                field_name,
            )

            if actual != expected:
                raise Phase12StartupPolicyError(
                    f"{field_name} must be {expected}"
                )

        if self.open_mutates_settled_cash:
            raise Phase12StartupPolicyError(
                "OPEN must not mutate settled cash"
            )

        if self.exit_subject_to_capital_admission:
            raise Phase12StartupPolicyError(
                "EXIT must not be subject to capital admission"
            )

        if self.short_financing_added:
            raise Phase12StartupPolicyError(
                "Phase 12 must not add short financing"
            )

    @classmethod
    def from_asset(
        cls,
        asset,
    ):
        if not isinstance(
            asset,
            AssetConfig,
        ):
            raise TypeError(
                "asset must be AssetConfig"
            )

        return cls(
            controlled_asset_id=asset.asset_id,
            max_exposure_percent=(
                asset.risk.max_exposure_percent
            ),
        )

    def fingerprint_payload(
        self,
    ):
        return {
            "controlled_asset_id": self.controlled_asset_id,
            "capital_source": self.capital_source,
            "capital_limit_formula": self.capital_limit_formula,
            "max_exposure_percent": self.max_exposure_percent,
            "proposed_exposure_basis": self.proposed_exposure_basis,
            "execution_price_basis": self.execution_price_basis,
            "fx_path": self.fx_path,
            "fx_freshness_required": self.fx_freshness_required,
            "entry_fee_semantics": self.entry_fee_semantics,
            "open_mutates_settled_cash": self.open_mutates_settled_cash,
            "exit_subject_to_capital_admission": (
                self.exit_subject_to_capital_admission
            ),
            "margin_model": self.margin_model,
            "collateral_model": self.collateral_model,
            "leverage_model": self.leverage_model,
            "short_financing_added": self.short_financing_added,
        }


@dataclass(frozen=True)
class Phase12StartupMetadata:
    schema: str
    execution_config_hash: str
    phase10_global_config_hash: str
    global_config_hash: str
    asset_registry_hash: str
    paper_mode: str
    phase10_feature_flags: object
    phase12_feature_flags: object
    phase10_runtime_policy: object
    capital_policy: object
    limitations: tuple[str, ...]


def require_phase12_capital_flag(
    capital_flags,
):
    if not isinstance(
        capital_flags,
        CapitalAdmissionFeatureFlags,
    ):
        raise TypeError(
            "capital_flags must be "
            "CapitalAdmissionFeatureFlags"
        )

    if not capital_flags.enabled:
        raise Phase12StartupPolicyError(
            PHASE12_CAPITAL_ADMISSION_FLAG_NOT_ENABLED
        )

    return capital_flags.fingerprint_flags()


def build_phase12_startup_metadata(
    *,
    phase10_metadata,
    capital_flags,
    capital_policy,
):
    if phase10_metadata is None:
        raise TypeError(
            "phase10_metadata is required"
        )

    if not isinstance(
        capital_policy,
        Phase12CapitalAdmissionPolicy,
    ):
        raise TypeError(
            "capital_policy must be "
            "Phase12CapitalAdmissionPolicy"
        )

    phase12_flags = require_phase12_capital_flag(
        capital_flags
    )

    execution_hash = (
        _required_text(
            getattr(
                phase10_metadata,
                "execution_config_hash",
                None,
            ),
            "execution_config_hash",
        )
        .lower()
    )

    phase10_hash = (
        _required_text(
            getattr(
                phase10_metadata,
                "global_config_hash",
                None,
            ),
            "phase10_global_config_hash",
        )
        .lower()
    )

    asset_hash = (
        _required_text(
            getattr(
                phase10_metadata,
                "asset_registry_hash",
                None,
            ),
            "asset_registry_hash",
        )
        .lower()
    )

    paper_mode = _required_text(
        getattr(
            phase10_metadata,
            "paper_mode",
            None,
        ),
        "paper_mode",
    )

    phase10_feature_flags = dict(
        getattr(
            phase10_metadata,
            "feature_flags",
            {},
        )
    )

    phase10_runtime_policy = dict(
        getattr(
            phase10_metadata,
            "runtime_policy",
            {},
        )
    )

    limitations = tuple(
        getattr(
            phase10_metadata,
            "limitations",
            (),
        )
    )

    capital_payload = (
        capital_policy
        .fingerprint_payload()
    )

    phase12_payload = {
        "schema": PHASE12_GLOBAL_CONFIG_SCHEMA,
        "phase10_global_config_hash": phase10_hash,
        "phase12_feature_flags": phase12_flags,
        "capital_policy": capital_payload,
    }

    global_hash = _sha256_payload(
        phase12_payload
    )

    return Phase12StartupMetadata(
        schema=PHASE12_GLOBAL_CONFIG_SCHEMA,
        execution_config_hash=execution_hash,
        phase10_global_config_hash=phase10_hash,
        global_config_hash=global_hash,
        asset_registry_hash=asset_hash,
        paper_mode=paper_mode,
        phase10_feature_flags=MappingProxyType(
            phase10_feature_flags
        ),
        phase12_feature_flags=MappingProxyType(
            dict(phase12_flags)
        ),
        phase10_runtime_policy=MappingProxyType(
            phase10_runtime_policy
        ),
        capital_policy=MappingProxyType(
            dict(capital_payload)
        ),
        limitations=limitations,
    )
