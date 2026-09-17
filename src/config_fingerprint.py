from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from enum import Enum

from src.data.assets import SUPPORTED_ASSETS, asset_payload


GLOBAL_CONFIG_SCHEMA = "phase09-global-config-v1"


def _normalized_value(value):
    if isinstance(value, Enum):
        return _normalized_value(value.value)

    if is_dataclass(value):
        return _normalized_value(asdict(value))

    if isinstance(value, Mapping):
        return {
            str(key): _normalized_value(value[key])
            for key in sorted(value, key=lambda item: str(item))
        }

    if isinstance(value, (list, tuple)):
        return [
            _normalized_value(item)
            for item in value
        ]

    if isinstance(value, (set, frozenset)):
        normalized = [
            _normalized_value(item)
            for item in value
        ]

        return sorted(
            normalized,
            key=lambda item: json.dumps(
                item,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ),
        )

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(
                "configuration contains non-finite float"
            )
        return value

    if value is None or isinstance(
        value,
        (str, int, bool),
    ):
        return value

    raise TypeError(
        "Unsupported configuration value: "
        f"{type(value).__name__}"
    )


def _sha256_json(payload):
    encoded = json.dumps(
        _normalized_value(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def normalized_asset_registry(
    assets=SUPPORTED_ASSETS,
):
    ordered = sorted(
        tuple(assets),
        key=lambda asset: asset.asset_id,
    )

    asset_ids = [
        asset.asset_id
        for asset in ordered
    ]

    if len(asset_ids) != len(set(asset_ids)):
        raise ValueError(
            "Duplicate asset_id in config fingerprint registry"
        )

    return tuple(
        _normalized_value(
            asset_payload(asset)
        )
        for asset in ordered
    )


def asset_registry_hash(
    assets=SUPPORTED_ASSETS,
):
    return _sha256_json(
        {
            "asset_registry": (
                normalized_asset_registry(assets)
            )
        }
    )


def _required_bool(
    name,
    value,
):
    if not isinstance(value, bool):
        raise TypeError(
            f"{name} must be bool"
        )

    return value


def build_phase09_feature_flags(
    *,
    realistic_v2_enabled,
    realistic_v2_execution_enabled,
    fx_enabled,
    pln_accounting_enabled,
):
    return {
        "AL_TRADING_REALISTIC_V2_ENABLED": _required_bool(
            "realistic_v2_enabled",
            realistic_v2_enabled,
        ),
        "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED": _required_bool(
            "realistic_v2_execution_enabled",
            realistic_v2_execution_enabled,
        ),
        "AL_TRADING_FX_ENABLED": _required_bool(
            "fx_enabled",
            fx_enabled,
        ),
        "AL_TRADING_PLN_ACCOUNTING_ENABLED": _required_bool(
            "pln_accounting_enabled",
            pln_accounting_enabled,
        ),
    }


def _validated_execution_hash(value):
    normalized = str(value).strip().lower()

    if len(normalized) != 64:
        raise ValueError(
            "execution_config_hash must be a SHA-256 hex digest"
        )

    try:
        int(normalized, 16)
    except ValueError as exc:
        raise ValueError(
            "execution_config_hash must be a SHA-256 hex digest"
        ) from exc

    return normalized


def _paper_mode_value(paper_mode):
    if isinstance(paper_mode, Enum):
        paper_mode = paper_mode.value

    value = str(paper_mode).strip()

    if not value:
        raise ValueError("paper_mode is required")

    return value


def global_config_payload(
    *,
    execution_config_hash,
    paper_mode,
    feature_flags,
    assets=SUPPORTED_ASSETS,
):
    if not isinstance(feature_flags, Mapping):
        raise TypeError(
            "feature_flags must be a mapping"
        )

    flags = {}

    for key, value in feature_flags.items():
        if not isinstance(value, bool):
            raise TypeError(
                "feature_flags values must be bool"
            )

        flags[str(key)] = value

    return {
        "schema": GLOBAL_CONFIG_SCHEMA,
        "asset_registry": normalized_asset_registry(assets),
        "asset_registry_hash": asset_registry_hash(assets),
        "execution_config_hash": _validated_execution_hash(
            execution_config_hash
        ),
        "paper_mode": _paper_mode_value(paper_mode),
        "feature_flags": flags,
    }


def global_config_hash(
    *,
    execution_config_hash,
    paper_mode,
    feature_flags,
    assets=SUPPORTED_ASSETS,
):
    return _sha256_json(
        global_config_payload(
            execution_config_hash=execution_config_hash,
            paper_mode=paper_mode,
            feature_flags=feature_flags,
            assets=assets,
        )
    )
