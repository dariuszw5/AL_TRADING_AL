from dataclasses import asdict, dataclass
import re


@dataclass(frozen=True)
class AssetSpec:
    symbol: str
    name: str
    asset_type: str
    provider: str
    provider_symbol: str
    quote: str
    min_difference: float = 1.0
    instrument_type: str = "spot"
    aliases: tuple[str, ...] = ()
    note: str | None = None


SUPPORTED_ASSETS = (
    AssetSpec("BTCUSDT", "Bitcoin", "crypto", "binance", "BTCUSDT", "USDT", 1.0),
    AssetSpec("ETHUSDT", "Ethereum", "crypto", "binance", "ETHUSDT", "USDT", 1.0),
    AssetSpec("SOLUSDT", "Solana", "crypto", "binance", "SOLUSDT", "USDT", 0.1),
    AssetSpec("BNBUSDT", "BNB", "crypto", "binance", "BNBUSDT", "USDT", 0.2),
    AssetSpec("XRPUSDT", "XRP", "crypto", "binance", "XRPUSDT", "USDT", 0.001),
    AssetSpec(
        "GOLD_FUT_CONT",
        "Złoto (futures proxy)",
        "gold",
        "yahoo",
        "GC=F",
        "USD",
        0.5,
        "continuous_future_proxy",
        ("XAUUSD", "GC=F"),
        "Ciągły kontrakt futures GC=F; proxy do paper/research, nie spot XAUUSD.",
    ),
    AssetSpec(
        "WTI_FUT_CONT",
        "Ropa WTI (futures proxy)",
        "oil",
        "yahoo",
        "CL=F",
        "USD",
        0.05,
        "continuous_future_proxy",
        ("WTIUSD", "CL=F"),
        "Ciągły kontrakt futures CL=F; proxy do paper/research, nie spot WTIUSD.",
    ),
    AssetSpec(
        "EURUSD",
        "Euro / dolar",
        "forex",
        "yahoo",
        "EURUSD=X",
        "USD",
        0.0001,
        "fx_spot_reference",
    ),
    AssetSpec(
        "AAPL",
        "Apple",
        "stock",
        "yahoo",
        "AAPL",
        "USD",
        0.05,
        "equity",
    ),
)

ASSET_BY_SYMBOL = {asset.symbol: asset for asset in SUPPORTED_ASSETS}
ASSET_ALIASES = {
    alias.upper(): asset.symbol
    for asset in SUPPORTED_ASSETS
    for alias in asset.aliases
}
_BINANCE_USDT_RE = re.compile(r"^[A-Z0-9]{2,20}USDT$")


def dynamic_binance_asset(symbol: str) -> AssetSpec:
    normalized = symbol.upper().strip()
    if not _BINANCE_USDT_RE.fullmatch(normalized):
        raise ValueError(f"Unsupported dynamic Binance symbol '{symbol}'")
    base = normalized[:-4]
    return AssetSpec(
        symbol=normalized,
        name=base,
        asset_type="crypto",
        provider="binance",
        provider_symbol=normalized,
        quote="USDT",
        min_difference=0.00000001,
        instrument_type="spot",
        note="Transient symbol discovered from Binance market data.",
    )


def get_asset(symbol: str, *, allow_dynamic_binance: bool = False) -> AssetSpec:
    normalized = symbol.upper().strip()
    canonical = ASSET_ALIASES.get(normalized, normalized)
    asset = ASSET_BY_SYMBOL.get(canonical)
    if asset is not None:
        return asset
    if allow_dynamic_binance:
        return dynamic_binance_asset(canonical)
    supported = ", ".join(ASSET_BY_SYMBOL)
    raise ValueError(
        f"Unsupported asset '{symbol}'. Supported assets: {supported}"
    )


def asset_payload(asset: AssetSpec) -> dict[str, object]:
    payload = asdict(asset)
    payload["aliases"] = list(asset.aliases)
    return payload
