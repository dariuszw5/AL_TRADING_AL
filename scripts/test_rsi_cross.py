from src.analysis.market_analyzer import MarketAnalyzer
from src.strategy.basic_strategy import BasicStrategy
import json


TIME_EXIT = 240


def load_candles(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_result(side, entry, exit_price):
    if side == "BUY":
        return (exit_price - entry) / entry * 100

    return (entry - exit_price) / entry * 100


def print_stats(label, trades):

    results = [t["result"] for t in trades]

    wins = [x for x in results if x > 0]
    losses = [x for x in results if x < 0]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    pf = (
        gross_profit / gross_loss
        if gross_loss > 0
        else (float("inf") if gross_profit > 0 else 0.0)
    )

    wr = (
        len(wins) / len(results) * 100
        if results
        else 0.0
    )

    print(
        f"{label:24} | "
        f"TRADES={len(trades):>3} | "
        f"WR={wr:>6.2f}% | "
        f"PROFIT={sum(results):>+9.4f}% | "
        f"PF={pf:>7.3f}"
    )

    for side in ("BUY", "SELL"):

        side_results = [
            t["result"]
            for t in trades
            if t["side"] == side
        ]

        if not side_results:
            continue

        side_wins = [
            x for x in side_results
            if x > 0
        ]

        side_losses = [
            x for x in side_results
            if x < 0
        ]

        gp = sum(side_wins)
        gl = abs(sum(side_losses))

        side_pf = (
            gp / gl
            if gl > 0
            else (float("inf") if gp > 0 else 0.0)
        )

        side_wr = (
            len(side_wins)
            / len(side_results)
            * 100
        )

        print(
            f"  {side:4} | "
            f"N={len(side_results):>2} | "
            f"WR={side_wr:>6.2f}% | "
            f"PROFIT={sum(side_results):>+9.4f}% | "
            f"PF={side_pf:>7.3f}"
        )


def run_test(name, path, mode):

    candles = load_candles(path)

    analyzer = MarketAnalyzer(
        rsi_method="classic"
    )

    strategy = BasicStrategy()

    position = None
    trades = []

    previous_rsi = None

    armed_buy = True
    armed_sell = True

    for i in range(len(candles)):

        class Candle:

            def __init__(self, data):
                self.timestamp = data["timestamp"]
                self.open = float(data["open"])
                self.high = float(data["high"])
                self.low = float(data["low"])
                self.close = float(data["close"])

        history = [
            Candle(x)
            for x in candles[:i + 1]
        ]

        analysis = analyzer.analyze(history)

        sma_values = analysis.get("sma", [])
        ema_values = analysis.get("ema", [])
        rsi_values = analysis.get("rsi", [])

        if not sma_values or not ema_values or not rsi_values:
            continue

        sma = sma_values[-1]
        ema = ema_values[-1]
        rsi = rsi_values[-1]

        signal = strategy.generate_signal(
            sma_value=sma,
            ema_value=ema,
            rsi_value=rsi,
            min_difference=1.0,
            buy_rsi=30.0,
            sell_rsi=70.0,
        )

        # -------------------------------------------------
        # ARMING / DISARMING
        # -------------------------------------------------

        if rsi >= 30:
            armed_buy = True

        if rsi <= 70:
            armed_sell = True

        # -------------------------------------------------
        # RSI CROSS
        # -------------------------------------------------

        crossed_buy = (
            previous_rsi is not None
            and previous_rsi >= 30
            and rsi < 30
        )

        crossed_sell = (
            previous_rsi is not None
            and previous_rsi <= 70
            and rsi > 70
        )

        if mode == "CROSS":

            if signal == "BUY" and not crossed_buy:
                signal = "HOLD"

            elif signal == "SELL" and not crossed_sell:
                signal = "HOLD"

        # -------------------------------------------------
        # RSI RE-ENTRY
        # -------------------------------------------------

        elif mode == "REENTRY":

            if signal == "BUY":

                if not crossed_buy or not armed_buy:
                    signal = "HOLD"
                else:
                    armed_buy = False

            elif signal == "SELL":

                if not crossed_sell or not armed_sell:
                    signal = "HOLD"
                else:
                    armed_sell = False

        # -------------------------------------------------
        # OTWARTA POZYCJA
        # -------------------------------------------------

        if position is not None:

            position["bars"] += 1

            if position["bars"] >= TIME_EXIT:

                exit_price = float(
                    candles[i]["close"]
                )

                position["result"] = calculate_result(
                    position["side"],
                    position["entry"],
                    exit_price,
                )

                position["exit"] = exit_price

                trades.append(position)

                position = None

            previous_rsi = rsi
            continue

        # -------------------------------------------------
        # NOWE WEJŚCIE
        # -------------------------------------------------

        if signal in ("BUY", "SELL"):

            position = {
                "side": signal,
                "entry": float(
                    candles[i]["close"]
                ),
                "entry_index": i,
                "bars": 0,
            }

        previous_rsi = rsi

    # -----------------------------------------------------
    # END OF DATA
    # -----------------------------------------------------

    if position is not None:

        exit_price = float(
            candles[-1]["close"]
        )

        position["result"] = calculate_result(
            position["side"],
            position["entry"],
            exit_price,
        )

        position["exit"] = exit_price

        trades.append(position)

    print_stats(name, trades)


if __name__ == "__main__":

    print()
    print("=" * 90)
    print("RSI CROSS / RE-ENTRY TEST")
    print("=" * 90)
    print()

    for dataset_name, path in [
        (
            "TRAIN",
            "data/backtest/BTCUSDT_1m_5000.json",
        ),
        (
            "VALIDATION",
            "data/backtest/BTCUSDT_1m_validation_5000.json",
        ),
    ]:

        print()
        print(f"================ {dataset_name} ================")
        print()

        run_test(
            "CURRENT",
            path,
            "CURRENT",
        )

        run_test(
            "RSI CROSS",
            path,
            "CROSS",
        )

        run_test(
            "RSI RE-ENTRY",
            path,
            "REENTRY",
        )

        print()
