from src.fx.providers import (
    CoinbaseUsdtUsdProvider,
    NbpTableAProvider,
    YahooPlnProvider,
)


def print_quote(
    name,
    quote,
):
    print(
        name
    )

    print(
        "  pair:",
        quote.pair,
    )

    print(
        "  rate:",
        quote.rate,
    )

    print(
        "  provider:",
        quote.provider,
    )

    print(
        "  source_quality:",
        quote.source_quality.value,
    )

    print(
        "  provider_timestamp:",
        quote.provider_timestamp,
    )

    print(
        "  effective_date:",
        quote.effective_date,
    )

    print(
        "  table:",
        quote.table,
    )

    print(
        "  bid:",
        quote.bid,
    )

    print(
        "  ask:",
        quote.ask,
    )

    print(
        "  labels:",
        quote.labels,
    )


def main():
    print(
        "PHASE 09 A.4 - LIVE FX PROVIDER PROBE"
    )

    print(
        "READ-ONLY MARKET DATA - NO TRADING"
    )

    nbp = NbpTableAProvider()
    yahoo = YahooPlnProvider()
    coinbase = CoinbaseUsdtUsdProvider()

    print_quote(
        "NBP USD/PLN",
        nbp.get_reference(
            "USD"
        ),
    )

    print_quote(
        "NBP EUR/PLN",
        nbp.get_reference(
            "EUR"
        ),
    )

    print_quote(
        "Yahoo USD/PLN",
        yahoo.get_quote(
            "USD"
        ),
    )

    print_quote(
        "Yahoo EUR/PLN",
        yahoo.get_quote(
            "EUR"
        ),
    )

    print_quote(
        "Coinbase USDT/USD",
        coinbase.get_quote(),
    )

    print(
        "REAL ORDERS SENT: 0"
    )


if __name__ == "__main__":
    main()
