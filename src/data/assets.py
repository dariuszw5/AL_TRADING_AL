from dataclasses import asdict, dataclass, field
from enum import Enum
from types import MappingProxyType


class AssetClass(str, Enum):
    CRYPTO = "CRYPTO"
    FOREX = "FOREX"
    METAL = "METAL"
    ENERGY = "ENERGY"
    STOCK = "STOCK"


class ValidationStatus(str, Enum):
    UNTESTED = "UNTESTED"
    EXPERIMENTAL = "EXPERIMENTAL"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    FROZEN = "FROZEN"
    DISABLED = "DISABLED"


class ShortMechanism(str, Enum):
    MARGIN = "MARGIN"
    FUTURES = "FUTURES"
    CFD = "CFD"
    BORROW = "BORROW"
    SYNTHETIC = "SYNTHETIC"
    NONE = "NONE"


@dataclass(frozen=True)
class StrategyConfig:
    buy_rsi: float
    sell_rsi: float
    min_difference: float
    rsi_method: str

    def __post_init__(self):
        if not 0.0 < self.buy_rsi < 100.0:
            raise ValueError(
                "buy_rsi must be between 0 and 100"
            )

        if not 0.0 < self.sell_rsi < 100.0:
            raise ValueError(
                "sell_rsi must be between 0 and 100"
            )

        if self.buy_rsi >= self.sell_rsi:
            raise ValueError(
                "buy_rsi must be below sell_rsi"
            )

        if self.min_difference < 0.0:
            raise ValueError(
                "min_difference cannot be negative"
            )

        if self.rsi_method not in {
            "classic",
            "wilder",
        }:
            raise ValueError(
                f"Unsupported RSI method: "
                f"{self.rsi_method}"
            )


@dataclass(frozen=True)
class RiskConfig:
    risk_percent: float
    stop_loss_percent: float
    max_daily_loss_percent: float
    max_exposure_percent: float
    risk_reward_ratio: float
    initial_balance: float

    def __post_init__(self):
        if not 0.0 < self.risk_percent <= 100.0:
            raise ValueError(
                "risk_percent must be in (0, 100]"
            )

        if self.stop_loss_percent <= 0.0:
            raise ValueError(
                "stop_loss_percent must be positive"
            )

        if self.max_daily_loss_percent <= 0.0:
            raise ValueError(
                "max_daily_loss_percent must be positive"
            )

        if not 0.0 < self.max_exposure_percent <= 100.0:
            raise ValueError(
                "max_exposure_percent must be in "
                "(0, 100]"
            )

        if self.risk_reward_ratio <= 0.0:
            raise ValueError(
                "risk_reward_ratio must be positive"
            )

        if self.initial_balance <= 0.0:
            raise ValueError(
                "initial_balance must be positive"
            )


@dataclass(frozen=True)
class ExecutionConfig:
    trading_fee: float
    max_position_candles: int

    def __post_init__(self):
        if not 0.0 <= self.trading_fee < 1.0:
            raise ValueError(
                "trading_fee must be in [0, 1)"
            )

        if self.max_position_candles <= 0:
            raise ValueError(
                "max_position_candles must be positive"
            )


@dataclass(frozen=True)
class ProviderConfig:
    provider_id: str
    metadata_reference: str
    unofficial: bool
    degraded_by_design: bool

    def __post_init__(self):
        if not self.provider_id.strip():
            raise ValueError(
                "provider_id is required"
            )

        if not self.metadata_reference.strip():
            raise ValueError(
                "metadata_reference is required"
            )


_PROVIDER_CONFIGS = {
    "binance": ProviderConfig(
        provider_id="binance",
        metadata_reference=(
            "docs/PROVIDER_CAPABILITY.md#binance"
        ),
        unofficial=False,
        degraded_by_design=False,
    ),
    "yahoo": ProviderConfig(
        provider_id="yahoo",
        metadata_reference=(
            "docs/PROVIDER_CAPABILITY.md#yahoo"
        ),
        unofficial=True,
        degraded_by_design=True,
    ),
}

PROVIDER_CONFIGS = MappingProxyType(
    _PROVIDER_CONFIGS
)


def get_provider_config(
    provider_id: str,
) -> ProviderConfig:
    normalized = provider_id.strip().lower()

    try:
        return PROVIDER_CONFIGS[normalized]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported provider "
            f"'{provider_id}'"
        ) from exc


@dataclass(frozen=True)
class AssetConfig:
    asset_id: str
    display_name: str

    provider: str
    provider_symbol: str

    instrument_type: str
    asset_class: AssetClass

    base_currency: str
    quote_currency: str

    interval: str

    precision: int | None = None
    tick_size: float | None = None
    quantity_step: float | None = None
    min_quantity: float | None = None
    min_notional: float | None = None

    contract_metadata: tuple[
        tuple[str, str],
        ...
    ] = ()

    allow_long: bool = True
    allow_short: bool = True

    short_mechanism: ShortMechanism = (
        ShortMechanism.SYNTHETIC
    )
    short_financing_model: str | None = (
        "FINANCING_NOT_MODELLED"
    )

    market_id: str = "UNKNOWN"
    session_id: str = "UNKNOWN"

    validation_status: ValidationStatus = (
        ValidationStatus.EXPERIMENTAL
    )
    validation_reference: str | None = None

    strategy: StrategyConfig = field(
        default_factory=lambda: StrategyConfig(
            buy_rsi=33.8,
            sell_rsi=68.5,
            min_difference=1.0,
            rsi_method="classic",
        )
    )

    risk: RiskConfig = field(
        default_factory=lambda: RiskConfig(
            risk_percent=5.0,
            stop_loss_percent=5.0,
            max_daily_loss_percent=10.0,
            max_exposure_percent=100.0,
            risk_reward_ratio=2.0,
            initial_balance=1000.0,
        )
    )

    execution: ExecutionConfig = field(
        default_factory=lambda: ExecutionConfig(
            trading_fee=0.0004,
            max_position_candles=241,
        )
    )

    # Compatibility only. This preserves existing persisted
    # state identifiers without pretending that they are the
    # canonical instrument identity.
    legacy_symbol: str | None = None

    def __post_init__(self):
        required = {
            "asset_id": self.asset_id,
            "display_name": self.display_name,
            "provider": self.provider,
            "provider_symbol": self.provider_symbol,
            "instrument_type": self.instrument_type,
            "base_currency": self.base_currency,
            "quote_currency": self.quote_currency,
            "interval": self.interval,
            "market_id": self.market_id,
            "session_id": self.session_id,
        }

        for name, value in required.items():
            if not str(value).strip():
                raise ValueError(
                    f"{name} is required"
                )

        get_provider_config(self.provider)

        if (
            self.precision is not None
            and self.precision < 0
        ):
            raise ValueError(
                "precision cannot be negative"
            )

        for name, value in (
            ("tick_size", self.tick_size),
            ("quantity_step", self.quantity_step),
            ("min_quantity", self.min_quantity),
            ("min_notional", self.min_notional),
        ):
            if value is not None and value <= 0.0:
                raise ValueError(
                    f"{name} must be positive "
                    "when specified"
                )

        if not self.allow_long and not self.allow_short:
            raise ValueError(
                "At least one direction must "
                "be supported"
            )

        if self.allow_short:
            if self.short_mechanism is ShortMechanism.NONE:
                raise ValueError(
                    "allow_short=True requires "
                    "a short mechanism"
                )

            if not self.short_financing_model:
                raise ValueError(
                    "allow_short=True requires "
                    "short_financing_model"
                )

        else:
            if (
                self.short_mechanism
                is not ShortMechanism.NONE
            ):
                raise ValueError(
                    "allow_short=False requires "
                    "short_mechanism=NONE"
                )

            if self.short_financing_model is not None:
                raise ValueError(
                    "allow_short=False requires "
                    "short_financing_model=None"
                )

        if (
            self.validation_status
            in {
                ValidationStatus.VALIDATED,
                ValidationStatus.FROZEN,
            }
            and not self.validation_reference
        ):
            raise ValueError(
                f"{self.validation_status.value} "
                "requires validation_reference"
            )

        if (
            self.instrument_type
            == "continuous_future_proxy"
            and self.validation_status
            not in {
                ValidationStatus.UNTESTED,
                ValidationStatus.EXPERIMENTAL,
                ValidationStatus.DISABLED,
            }
        ):
            raise ValueError(
                "continuous_future_proxy cannot "
                "be promoted above EXPERIMENTAL"
            )

    @property
    def state_key(self) -> str:
        return self.legacy_symbol or self.asset_id

    # Compatibility fields used by older parts of the repo.
    # They are intentionally not canonical identity.
    @property
    def symbol(self) -> str:
        return self.state_key

    @property
    def name(self) -> str:
        return self.display_name

    @property
    def asset_type(self) -> str:
        if self.asset_id == "GOLD_FUT_CONT":
            return "gold"

        if self.asset_id == "WTI_FUT_CONT":
            return "oil"

        return self.asset_class.value.lower()

    @property
    def quote(self) -> str:
        return self.quote_currency

    @property
    def min_difference(self) -> float:
        return self.strategy.min_difference


# Compatibility type name for code written before Phase 05.
AssetSpec = AssetConfig


def _strategy(
    min_difference: float,
) -> StrategyConfig:
    return StrategyConfig(
        buy_rsi=33.8,
        sell_rsi=68.5,
        min_difference=min_difference,
        rsi_method="classic",
    )


def _risk() -> RiskConfig:
    return RiskConfig(
        risk_percent=5.0,
        stop_loss_percent=5.0,
        max_daily_loss_percent=10.0,
        max_exposure_percent=100.0,
        risk_reward_ratio=2.0,
        initial_balance=1000.0,
    )


def _execution() -> ExecutionConfig:
    return ExecutionConfig(
        trading_fee=0.0004,
        max_position_candles=241,
    )


SUPPORTED_ASSETS = (
    AssetConfig(
        asset_id="BTCUSDT",
        display_name="Bitcoin",
        provider="binance",
        provider_symbol="BTCUSDT",
        instrument_type="spot_reference",
        asset_class=AssetClass.CRYPTO,
        base_currency="BTC",
        quote_currency="USDT",
        interval="1m",
        market_id="BINANCE_SPOT_REFERENCE",
        session_id="CRYPTO_24_7",
        validation_status=ValidationStatus.FROZEN,
        validation_reference=(
            "v1.0.0:"
            "data/backtest/BTCUSDT_1m_5000.json"
        ),
        strategy=_strategy(1.0),
        risk=_risk(),
        execution=_execution(),
    ),
    AssetConfig(
        asset_id="ETHUSDT",
        display_name="Ethereum",
        provider="binance",
        provider_symbol="ETHUSDT",
        instrument_type="spot_reference",
        asset_class=AssetClass.CRYPTO,
        base_currency="ETH",
        quote_currency="USDT",
        interval="1m",
        market_id="BINANCE_SPOT_REFERENCE",
        session_id="CRYPTO_24_7",
        strategy=_strategy(1.0),
        risk=_risk(),
        execution=_execution(),
    ),
    AssetConfig(
        asset_id="SOLUSDT",
        display_name="Solana",
        provider="binance",
        provider_symbol="SOLUSDT",
        instrument_type="spot_reference",
        asset_class=AssetClass.CRYPTO,
        base_currency="SOL",
        quote_currency="USDT",
        interval="1m",
        market_id="BINANCE_SPOT_REFERENCE",
        session_id="CRYPTO_24_7",
        strategy=_strategy(0.1),
        risk=_risk(),
        execution=_execution(),
    ),
    AssetConfig(
        asset_id="BNBUSDT",
        display_name="BNB",
        provider="binance",
        provider_symbol="BNBUSDT",
        instrument_type="spot_reference",
        asset_class=AssetClass.CRYPTO,
        base_currency="BNB",
        quote_currency="USDT",
        interval="1m",
        market_id="BINANCE_SPOT_REFERENCE",
        session_id="CRYPTO_24_7",
        strategy=_strategy(0.2),
        risk=_risk(),
        execution=_execution(),
    ),
    AssetConfig(
        asset_id="XRPUSDT",
        display_name="XRP",
        provider="binance",
        provider_symbol="XRPUSDT",
        instrument_type="spot_reference",
        asset_class=AssetClass.CRYPTO,
        base_currency="XRP",
        quote_currency="USDT",
        interval="1m",
        market_id="BINANCE_SPOT_REFERENCE",
        session_id="CRYPTO_24_7",
        strategy=_strategy(0.001),
        risk=_risk(),
        execution=_execution(),
    ),
    AssetConfig(
        asset_id="GOLD_FUT_CONT",
        display_name=(
            "Gold Continuous Futures Proxy"
        ),
        provider="yahoo",
        provider_symbol="GC=F",
        instrument_type=(
            "continuous_future_proxy"
        ),
        asset_class=AssetClass.METAL,
        base_currency="GOLD",
        quote_currency="USD",
        interval="1m",
        contract_metadata=(
            ("proxy", "continuous_future"),
            (
                "known_limitation",
                "rollover_discontinuities",
            ),
        ),
        market_id="CME_FUTURES_PROXY",
        session_id="CME_GLOBEX_REFERENCE",
        validation_status=(
            ValidationStatus.EXPERIMENTAL
        ),
        strategy=_strategy(0.5),
        risk=_risk(),
        execution=_execution(),
        legacy_symbol="XAUUSD",
    ),
    AssetConfig(
        asset_id="WTI_FUT_CONT",
        display_name=(
            "WTI Continuous Futures Proxy"
        ),
        provider="yahoo",
        provider_symbol="CL=F",
        instrument_type=(
            "continuous_future_proxy"
        ),
        asset_class=AssetClass.ENERGY,
        base_currency="WTI",
        quote_currency="USD",
        interval="1m",
        contract_metadata=(
            ("proxy", "continuous_future"),
            (
                "known_limitation",
                "rollover_discontinuities",
            ),
        ),
        market_id="CME_FUTURES_PROXY",
        session_id="CME_GLOBEX_REFERENCE",
        validation_status=(
            ValidationStatus.EXPERIMENTAL
        ),
        strategy=_strategy(0.05),
        risk=_risk(),
        execution=_execution(),
        legacy_symbol="WTIUSD",
    ),
    AssetConfig(
        asset_id="EURUSD",
        display_name="EUR/USD",
        provider="yahoo",
        provider_symbol="EURUSD=X",
        instrument_type="fx_spot_reference",
        asset_class=AssetClass.FOREX,
        base_currency="EUR",
        quote_currency="USD",
        interval="1m",
        market_id="FX_REFERENCE",
        session_id="FX_24_5_REFERENCE",
        strategy=_strategy(0.0001),
        risk=_risk(),
        execution=_execution(),
    ),
    AssetConfig(
        asset_id="AAPL",
        display_name="Apple",
        provider="yahoo",
        provider_symbol="AAPL",
        instrument_type="equity_reference",
        asset_class=AssetClass.STOCK,
        base_currency="AAPL",
        quote_currency="USD",
        interval="1m",
        market_id="NASDAQ_REFERENCE",
        session_id="NASDAQ_REGULAR_REFERENCE",
        strategy=_strategy(0.05),
        risk=_risk(),
        execution=_execution(),
    ),
)


_ASSET_BY_ID = {
    asset.asset_id: asset
    for asset in SUPPORTED_ASSETS
}

ASSET_BY_ID = MappingProxyType(
    _ASSET_BY_ID
)

# Backward-compatible name used by old code.
ASSET_BY_SYMBOL = ASSET_BY_ID


ASSET_ALIASES = MappingProxyType(
    {
        "XAUUSD": "GOLD_FUT_CONT",
        "GC=F": "GOLD_FUT_CONT",
        "WTIUSD": "WTI_FUT_CONT",
        "CL=F": "WTI_FUT_CONT",
    }
)


def _validate_registry():
    if len(ASSET_BY_ID) != len(SUPPORTED_ASSETS):
        raise ValueError(
            "Duplicate asset_id in asset registry"
        )

    provider_symbols = [
        (
            asset.provider,
            asset.provider_symbol,
        )
        for asset in SUPPORTED_ASSETS
    ]

    if len(set(provider_symbols)) != len(
        provider_symbols
    ):
        raise ValueError(
            "Duplicate provider/provider_symbol "
            "pair in asset registry"
        )


_validate_registry()


def get_asset(
    symbol: str,
) -> AssetConfig:
    normalized = symbol.upper().strip()

    normalized = ASSET_ALIASES.get(
        normalized,
        normalized,
    )

    try:
        return ASSET_BY_ID[normalized]
    except KeyError as exc:
        supported = ", ".join(
            ASSET_BY_ID
        )

        raise ValueError(
            f"Unsupported asset '{symbol}'. "
            f"Supported assets: {supported}"
        ) from exc


def asset_payload(
    asset: AssetConfig,
) -> dict[str, object]:
    payload = asdict(asset)

    payload["asset_class"] = (
        asset.asset_class.value
    )
    payload["validation_status"] = (
        asset.validation_status.value
    )
    payload["short_mechanism"] = (
        asset.short_mechanism.value
    )

    # Public identity is always canonical.
    payload["symbol"] = asset.asset_id
    payload["name"] = asset.display_name
    payload["asset_type"] = asset.asset_type
    payload["quote"] = asset.quote_currency
    payload["min_difference"] = (
        asset.strategy.min_difference
    )

    provider = get_provider_config(
        asset.provider
    )

    payload["provider_metadata"] = {
        "provider_id": provider.provider_id,
        "metadata_reference": (
            provider.metadata_reference
        ),
        "unofficial": provider.unofficial,
        "degraded_by_design": (
            provider.degraded_by_design
        ),
    }

    return payload
