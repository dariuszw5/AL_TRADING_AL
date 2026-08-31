from src.data.data_provider import DataProvider


TRAINING_FILE = "data/backtest/BTCUSDT_1m_5000.json"
VALIDATION_FILE = "data/backtest/BTCUSDT_1m_validation_5000.json"
TEST_FILE = "data/backtest/BTCUSDT_1m_test_5000.json"

TOTAL_CANDLES = 15000
SET_SIZE = 5000


def main():
    provider = DataProvider()

    print("=== CREATING DATASETS ===")
    print()
    print(f"Pobieranie: {TOTAL_CANDLES} świec BTCUSDT 1m...")
    print()

    candles = provider.get_historical_candles(
        symbol="BTCUSDT",
        interval="1m",
        limit=TOTAL_CANDLES
    )

    if len(candles) != TOTAL_CANDLES:
        raise RuntimeError(
            f"Nie pobrano wymaganej liczby świec. "
            f"Oczekiwano {TOTAL_CANDLES}, otrzymano {len(candles)}."
        )

    candles = sorted(
        candles,
        key=lambda candle: candle.timestamp
    )

    training = candles[:SET_SIZE]
    validation = candles[SET_SIZE:SET_SIZE * 2]
    test = candles[SET_SIZE * 2:SET_SIZE * 3]

    provider.save_candles(
        training,
        TRAINING_FILE
    )

    provider.save_candles(
        validation,
        VALIDATION_FILE
    )

    provider.save_candles(
        test,
        TEST_FILE
    )

    print("=== DATASETS CREATED ===")
    print()

    print("TRAINING")
    print(f"Świece:     {len(training)}")
    print(f"Pierwsza:   {training[0].timestamp}")
    print(f"Ostatnia:   {training[-1].timestamp}")
    print(f"Plik:       {TRAINING_FILE}")
    print()

    print("VALIDATION")
    print(f"Świece:     {len(validation)}")
    print(f"Pierwsza:   {validation[0].timestamp}")
    print(f"Ostatnia:   {validation[-1].timestamp}")
    print(f"Plik:       {VALIDATION_FILE}")
    print()

    print("TEST")
    print(f"Świece:     {len(test)}")
    print(f"Pierwsza:   {test[0].timestamp}")
    print(f"Ostatnia:   {test[-1].timestamp}")
    print(f"Plik:       {TEST_FILE}")
    print()

    print("=== DATA SPLIT COMPLETE ===")


if __name__ == "__main__":
    main()