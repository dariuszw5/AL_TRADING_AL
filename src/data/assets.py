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
        symbol="LTCUSDT", name="Litecoin", asset_type="crypto", provider="binance",
        provider_symbol="LTCUSDT", quote="USDT", min_difference=0.05,
    ),
    AssetSpec(
        symbol="ADAUSDT", name="Cardano", asset_type="crypto", provider="binance",
        provider_symbol="ADAUSDT", quote="USDT", min_difference=0.001,
    ),
    AssetSpec(
        symbol="DOGEUSDT", name="Dogecoin", asset_type="crypto", provider="binance",
        provider_symbol="DOGEUSDT", quote="USDT", min_difference=0.0001,
    ),
    AssetSpec(
        symbol="AVAXUSDT", name="Avalanche", asset_type="crypto", provider="binance",
        provider_symbol="AVAXUSDT", quote="USDT", min_difference=0.01,
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
    AssetSpec("MSFT", "Microsoft", "stock", "yahoo", "MSFT", "USD", 0.05),
    AssetSpec("NVDA", "Nvidia", "stock", "yahoo", "NVDA", "USD", 0.05),
    AssetSpec("AMZN", "Amazon", "stock", "yahoo", "AMZN", "USD", 0.05),
    AssetSpec("GOOGL", "Alphabet", "stock", "yahoo", "GOOGL", "USD", 0.05),
    AssetSpec("TSLA", "Tesla", "stock", "yahoo", "TSLA", "USD", 0.05),
    AssetSpec("META", "Meta", "stock", "yahoo", "META", "USD", 0.05),
    AssetSpec("SPX", "S&P 500", "index", "yahoo", "^GSPC", "USD", 0.1),
    AssetSpec("NDX", "Nasdaq 100", "index", "yahoo", "^NDX", "USD", 0.1),
    AssetSpec("DAX", "DAX", "index", "yahoo", "^GDAXI", "EUR", 0.1),
    AssetSpec("WIG20", "WIG20", "index", "yahoo", "WIG20.WA", "PLN", 0.1),
    AssetSpec("XAGUSD", "Srebro", "metal", "yahoo", "SI=F", "USD", 0.01),
    AssetSpec("XPTUSD", "Platyna", "metal", "yahoo", "PL=F", "USD", 0.1),
    AssetSpec("HGUSD", "Miedź", "metal", "yahoo", "HG=F", "USD", 0.001),
    AssetSpec("BRENTUSD", "Ropa Brent", "oil", "yahoo", "BZ=F", "USD", 0.05),
    AssetSpec("NATGASUSD", "Gaz ziemny", "energy", "yahoo", "NG=F", "USD", 0.001),
    AssetSpec("CORNUSD", "Kukurydza", "agriculture", "yahoo", "ZC=F", "USD", 0.01),
    AssetSpec("WHEATUSD", "Pszenica", "agriculture", "yahoo", "ZW=F", "USD", 0.01),
    AssetSpec("SOYUSD", "Soja", "agriculture", "yahoo", "ZS=F", "USD", 0.01),
    AssetSpec("COFFEEUSD", "Kawa", "agriculture", "yahoo", "KC=F", "USD", 0.01),
    AssetSpec("GBPUSD", "Funt / dolar", "forex", "yahoo", "GBPUSD=X", "USD", 0.0001),
    AssetSpec("USDJPY", "Dolar / jen", "forex", "yahoo", "JPY=X", "JPY", 0.01),
    AssetSpec("USDCHF", "Dolar / frank", "forex", "yahoo", "CHF=X", "CHF", 0.0001),
    AssetSpec("AUDUSD", "Dolar australijski", "forex", "yahoo", "AUDUSD=X", "USD", 0.0001),
    AssetSpec("USDCAD", "Dolar kanadyjski", "forex", "yahoo", "CAD=X", "CAD", 0.0001),
    AssetSpec("LINKUSDT", "Chainlink", "crypto", "binance", "LINKUSDT", "USDT", 0.001),
    AssetSpec("DOTUSDT", "Polkadot", "crypto", "binance", "DOTUSDT", "USDT", 0.001),
    AssetSpec("MATICUSDT", "Polygon", "crypto", "binance", "MATICUSDT", "USDT", 0.0001),
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
