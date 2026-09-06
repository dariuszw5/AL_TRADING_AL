class RiskManager:

    def calculate_position_size(
        self,
        balance,
        risk_percent,
        entry_price,
        stop_loss
    ):
        if balance < 0:
            raise ValueError(
                "Balance must not be negative"
            )

        if risk_percent <= 0:
            raise ValueError(
                "Risk percent must be greater than 0"
            )

        if entry_price <= 0:
            raise ValueError(
                "Entry price must be greater than 0"
            )

        if stop_loss <= 0:
            raise ValueError(
                "Stop loss must be greater than 0"
            )

        risk_amount = (
            balance * (risk_percent / 100)
        )

        risk_per_unit = abs(
            entry_price - stop_loss
        )

        if risk_per_unit <= 0:
            return 0.0

        position_size = (
            risk_amount / risk_per_unit
        )

        return position_size