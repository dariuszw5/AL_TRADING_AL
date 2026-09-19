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
        "commodity",
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
        "commodity",
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
        "equity",
        "yahoo",
        "AAPL",
        "USD",
        0.05,
        "equity",
    ),
)


RESEARCH_ASSETS = (
    *[asset for asset in SUPPORTED_ASSETS if asset.symbol == "AAPL"],
    AssetSpec("MSFT", "Microsoft", "equity", "yahoo", "MSFT", "USD", 0.05, "equity"),
    AssetSpec("NVDA", "NVIDIA", "equity", "yahoo", "NVDA", "USD", 0.05, "equity"),
    AssetSpec("AMZN", "Amazon", "equity", "yahoo", "AMZN", "USD", 0.05, "equity"),
    AssetSpec("META", "Meta", "equity", "yahoo", "META", "USD", 0.05, "equity"),
    AssetSpec("GOOGL", "Alphabet", "equity", "yahoo", "GOOGL", "USD", 0.05, "equity"),
    AssetSpec("TSLA", "Tesla", "equity", "yahoo", "TSLA", "USD", 0.05, "equity"),
    AssetSpec("JPM", "JPMorgan", "equity", "yahoo", "JPM", "USD", 0.05, "equity"),
    AssetSpec("XOM", "Exxon Mobil", "equity", "yahoo", "XOM", "USD", 0.05, "equity"),

    AssetSpec("SPY", "S&P 500 ETF", "etf", "yahoo", "SPY", "USD", 0.05, "etf"),
    AssetSpec("QQQ", "Nasdaq 100 ETF", "etf", "yahoo", "QQQ", "USD", 0.05, "etf"),
    AssetSpec("IWM", "Russell 2000 ETF", "etf", "yahoo", "IWM", "USD", 0.05, "etf"),
    AssetSpec("DIA", "Dow 30 ETF", "etf", "yahoo", "DIA", "USD", 0.05, "etf"),
    AssetSpec("XLK", "Technology Select ETF", "etf", "yahoo", "XLK", "USD", 0.05, "etf"),
    AssetSpec("XLF", "Financial Select ETF", "etf", "yahoo", "XLF", "USD", 0.05, "etf"),

    *[asset for asset in SUPPORTED_ASSETS if asset.symbol == "EURUSD"],
    AssetSpec("GBPUSD", "Funt / dolar", "forex", "yahoo", "GBPUSD=X", "USD", 0.0001, "fx_spot_reference"),
    AssetSpec("USDJPY", "Dolar / jen", "forex", "yahoo", "JPY=X", "JPY", 0.01, "fx_spot_reference"),
    AssetSpec("AUDUSD", "Dolar australijski / dolar", "forex", "yahoo", "AUDUSD=X", "USD", 0.0001, "fx_spot_reference"),
    AssetSpec("USDCAD", "Dolar / dolar kanadyjski", "forex", "yahoo", "CAD=X", "CAD", 0.0001, "fx_spot_reference"),
    AssetSpec("USDCHF", "Dolar / frank", "forex", "yahoo", "CHF=X", "CHF", 0.0001, "fx_spot_reference"),
    AssetSpec("NZDUSD", "Dolar nowozelandzki / dolar", "forex", "yahoo", "NZDUSD=X", "USD", 0.0001, "fx_spot_reference"),

    AssetSpec("SP500_INDEX", "S&P 500 Index", "index", "yahoo", "^GSPC", "USD", 0.1, "index_reference"),
    AssetSpec("NASDAQ100_INDEX", "Nasdaq 100 Index", "index", "yahoo", "^NDX", "USD", 0.1, "index_reference"),
    AssetSpec("DOW30_INDEX", "Dow Jones Index", "index", "yahoo", "^DJI", "USD", 0.1, "index_reference"),
    AssetSpec("RUSSELL2000_INDEX", "Russell 2000 Index", "index", "yahoo", "^RUT", "USD", 0.1, "index_reference"),
    AssetSpec("VIX_INDEX", "VIX Index", "index", "yahoo", "^VIX", "USD", 0.01, "index_reference"),

    *[asset for asset in SUPPORTED_ASSETS if asset.symbol in {"GOLD_FUT_CONT", "WTI_FUT_CONT"}],
    AssetSpec("SILVER_FUT_CONT", "Srebro (futures proxy)", "commodity", "yahoo", "SI=F", "USD", 0.01, "continuous_future_proxy"),
    AssetSpec("COPPER_FUT_CONT", "Miedź (futures proxy)", "commodity", "yahoo", "HG=F", "USD", 0.001, "continuous_future_proxy"),
    AssetSpec("NATGAS_FUT_CONT", "Gaz ziemny (futures proxy)", "commodity", "yahoo", "NG=F", "USD", 0.001, "continuous_future_proxy"),
    AssetSpec("BRENT_FUT_CONT", "Brent (futures proxy)", "commodity", "yahoo", "BZ=F", "USD", 0.01, "continuous_future_proxy"),
)

ASSET_BY_SYMBOL = {asset.symbol: asset for asset in SUPPORTED_ASSETS}
RESEARCH_ASSET_BY_SYMBOL = {asset.symbol: asset for asset in RESEARCH_ASSETS}
ASSET_ALIASES = {
    alias.upper(): asset.symbol
    for asset in (*SUPPORTED_ASSETS, *RESEARCH_ASSETS)
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
    asset = ASSET_BY_SYMBOL.get(canonical) or RESEARCH_ASSET_BY_SYMBOL.get(canonical)
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
