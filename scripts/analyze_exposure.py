from src.risk.risk_manager import RiskManager


def main():
    manager = RiskManager()

    balance = 1000.0
    entry_price = 100000.0
    risk_percent = 5.0

    stop_loss_values = [
        1.0,
        1.5,
        2.0,
        2.5,
        3.0,
        4.0,
        5.0,
        6.0,
        8.0,
        10.0
    ]

    print("=== POSITION EXPOSURE ANALYSIS ===")
    print()

    for stop_percent in stop_loss_values:
        if stop_percent <= 0:
            continue

        stop_loss = entry_price * (
            1 - stop_percent / 100
        )

        position_size = manager.calculate_position_size(
            balance=balance,
            risk_percent=risk_percent,
            entry_price=entry_price,
            stop_loss=stop_loss
        )

        position_value = (
            position_size * entry_price
        )

        exposure_percent = (
            position_value / balance
        ) * 100

        print(
            f"SL={stop_percent:>4.1f}% | "
            f"Position={position_size:>10.6f} BTC | "
            f"Value={position_value:>12.2f} | "
            f"Exposure={exposure_percent:>8.2f}%"
        )


if __name__ == "__main__":
    main()
