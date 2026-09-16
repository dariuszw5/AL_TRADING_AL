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


# These are paper-trading instruments only. Binance supplies the crypto
# candles; Yahoo's public chart endpoint supplies the non-crypto examples.
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
        symbol="XAUUSD",
        name="Złoto",
        asset_type="gold",
        provider="yahoo",
        provider_symbol="GC=F",
        quote="USD",
        min_difference=0.5,
    ),
    AssetSpec(
        symbol="WTIUSD",
        name="Ropa WTI",
        asset_type="oil",
        provider="yahoo",
        provider_symbol="CL=F",
        quote="USD",
        min_difference=0.05,
    ),
    AssetSpec(
        symbol="EURUSD",
        name="Euro / dolar",
        asset_type="forex",
        provider="yahoo",
        provider_symbol="EURUSD=X",
        quote="USD",
        min_difference=0.0001,
    ),
    AssetSpec(
        symbol="AAPL",
        name="Apple",
        asset_type="stock",
        provider="yahoo",
        provider_symbol="AAPL",
        quote="USD",
        min_difference=0.05,
    ),
)

ASSET_BY_SYMBOL = {asset.symbol: asset for asset in SUPPORTED_ASSETS}


def get_asset(symbol: str) -> AssetSpec:
    normalized = symbol.upper().strip()

    try:
        return ASSET_BY_SYMBOL[normalized]
    except KeyError as exc:
        supported = ", ".join(ASSET_BY_SYMBOL)
        raise ValueError(
            f"Unsupported asset '{symbol}'. Supported assets: {supported}"
        ) from exc


def asset_payload(asset: AssetSpec) -> dict[str, object]:
    return asdict(asset)
