class RiskManager:
    def calculate_position_size(
        self,
        balance,
        risk_percent,
        entry_price,
        stop_loss
    ):
        risk_amount = balance * (risk_percent / 100)

        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit <= 0:
            return 0.0

        position_size = risk_amount / risk_per_unit

        return round(position_size, 2)