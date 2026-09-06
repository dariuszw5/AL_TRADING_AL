class RiskLevels:
    def calculate_stop_loss(
        self,
        entry_price,
        risk_percent,
        stop_loss_percent=None,
        side="BUY"
    ):
        if entry_price <= 0:
            raise ValueError(
                "Entry price must be greater than 0"
            )

        if risk_percent <= 0:
            raise ValueError(
                "Risk percent must be greater than 0"
            )

        if stop_loss_percent is None:
            stop_loss_percent = risk_percent

        if stop_loss_percent <= 0:
            raise ValueError(
                "Stop loss percent must be greater than 0"
            )

        if side == "BUY":
            return round(
                entry_price
                * (1 - stop_loss_percent / 100),
                2
            )

        if side == "SELL":
            return round(
                entry_price
                * (1 + stop_loss_percent / 100),
                2
            )

        raise ValueError(
            "Side must be BUY or SELL"
        )

    def calculate_take_profit(
        self,
        entry_price,
        stop_loss,
        risk_reward_ratio=2.0,
        side="BUY"
    ):
        if entry_price <= 0:
            raise ValueError(
                "Entry price must be greater than 0"
            )

        if stop_loss <= 0:
            raise ValueError(
                "Stop loss must be greater than 0"
            )

        if risk_reward_ratio <= 0:
            raise ValueError(
                "Risk reward ratio must be greater than 0"
            )

        if side == "BUY":
            risk = entry_price - stop_loss

            if risk <= 0:
                raise ValueError(
                    "Stop loss must be below entry price"
                )

            return round(
                entry_price
                + (risk * risk_reward_ratio),
                2
            )

        if side == "SELL":
            risk = stop_loss - entry_price

            if risk <= 0:
                raise ValueError(
                    "Stop loss must be above entry price"
                )

            return round(
                entry_price
                - (risk * risk_reward_ratio),
                2
            )

        raise ValueError(
            "Side must be BUY or SELL"
        )