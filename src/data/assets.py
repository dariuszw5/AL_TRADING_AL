from dataclasses import asdict, dataclass


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


# Paper-trading instruments exposed by the existing application.
# Crypto candles come from Binance. Non-crypto market candles use Yahoo's
# chart endpoint. GOLD/WTI are deliberately named as continuous-futures
# proxies so the UI never presents GC=F / CL=F as spot XAUUSD / WTIUSD.
SUPPORTED_ASSETS = (
    AssetSpec(
        symbol="BTCUSDT",
        name="Bitcoin",
        asset_type="crypto",
        provider="binance",
        provider_symbol="BTCUSDT",
        quote="USDT",
        min_difference=1.0,
    ),
    AssetSpec(
        symbol="ETHUSDT",
        name="Ethereum",
        asset_type="crypto",
        provider="binance",
        provider_symbol="ETHUSDT",
        quote="USDT",
        min_difference=1.0,
    ),
    AssetSpec(
        symbol="SOLUSDT",
        name="Solana",
        asset_type="crypto",
        provider="binance",
        provider_symbol="SOLUSDT",
        quote="USDT",
        min_difference=0.1,
    ),
    AssetSpec(
        symbol="BNBUSDT",
        name="BNB",
        asset_type="crypto",
        provider="binance",
        provider_symbol="BNBUSDT",
        quote="USDT",
        min_difference=0.2,
    ),
    AssetSpec(
        symbol="XRPUSDT",
        name="XRP",
        asset_type="crypto",
        provider="binance",
        provider_symbol="XRPUSDT",
        quote="USDT",
        min_difference=0.001,
    ),
    AssetSpec(
        symbol="GOLD_FUT_CONT",
        name="Złoto (futures proxy)",
        asset_type="gold",
        provider="yahoo",
        provider_symbol="GC=F",
        quote="USD",
        min_difference=0.5,
        instrument_type="continuous_future_proxy",
        aliases=("XAUUSD", "GC=F"),
        note="Ciągły kontrakt futures GC=F; proxy do paper/research, nie spot XAUUSD.",
    ),
    AssetSpec(
        symbol="WTI_FUT_CONT",
        name="Ropa WTI (futures proxy)",
        asset_type="oil",
        provider="yahoo",
        provider_symbol="CL=F",
        quote="USD",
        min_difference=0.05,
        instrument_type="continuous_future_proxy",
        aliases=("WTIUSD", "CL=F"),
        note="Ciągły kontrakt futures CL=F; proxy do paper/research, nie spot WTIUSD.",
    ),
    AssetSpec(
        symbol="EURUSD",
        name="Euro / dolar",
        asset_type="forex",
        provider="yahoo",
        provider_symbol="EURUSD=X",
        quote="USD",
        min_difference=0.0001,
        instrument_type="fx_spot_reference",
    ),
    AssetSpec(
        symbol="AAPL",
        name="Apple",
        asset_type="stock",
        provider="yahoo",
        provider_symbol="AAPL",
        quote="USD",
        min_difference=0.05,
        instrument_type="equity",
    ),
)

ASSET_BY_SYMBOL = {asset.symbol: asset for asset in SUPPORTED_ASSETS}
ASSET_ALIASES = {
    alias.upper(): asset.symbol
    for asset in SUPPORTED_ASSETS
    for alias in asset.aliases
}


def get_asset(symbol: str) -> AssetSpec:
    normalized = symbol.upper().strip()
    canonical = ASSET_ALIASES.get(normalized, normalized)

    try:
        return ASSET_BY_SYMBOL[canonical]
    except KeyError as exc:
        supported = ", ".join(ASSET_BY_SYMBOL)
        raise ValueError(
            f"Unsupported asset '{symbol}'. Supported assets: {supported}"
        ) from exc


def asset_payload(asset: AssetSpec) -> dict[str, object]:
    payload = asdict(asset)
    payload["aliases"] = list(asset.aliases)
    return payload
