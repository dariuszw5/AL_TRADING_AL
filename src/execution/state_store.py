from __future__ import annotations

import json
import os
import tempfile
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path

from src.core.clock import (
    Clock,
    SystemClock,
)
from src.data.market_data import (
    ExecutionQuality,
)

from .models import (
    ExecutionProfile,
    Position,
    PositionSide,
    PositionStatus,
)


_SCHEMA_VERSION = 1


def _datetime_to_text(
    value,
):
    if value is None:
        return None

    if value.tzinfo is None:
        raise ValueError(
            "State datetime must be timezone-aware"
        )

    return (
        value
        .astimezone(
            timezone.utc
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


def _datetime_from_text(
    value,
):
    if value is None:
        return None

    parsed = datetime.fromisoformat(
        str(value).replace(
            "Z",
            "+00:00",
        )
    )

    if parsed.tzinfo is None:
        raise ValueError(
            "Stored datetime must be timezone-aware"
        )

    return parsed.astimezone(
        timezone.utc
    )


def _position_to_dict(
    position,
):
    if (
        position.execution_profile
        is not ExecutionProfile.REALISTIC_V2
    ):
        raise ValueError(
            "Only REALISTIC_V2 positions "
            "may be persisted"
        )

    return {
        "position_id": (
            position.position_id
        ),
        "asset_id": (
            position.asset_id
        ),
        "side": (
            position.side.value
        ),
        "quantity": (
            position.quantity
        ),
        "entry_execution_id": (
            position.entry_execution_id
        ),
        "entry_price": (
            position.entry_price
        ),
        "stop_loss": (
            position.stop_loss
        ),
        "take_profit": (
            position.take_profit
        ),
        "opened_at": (
            _datetime_to_text(
                position.opened_at
            )
        ),
        "short_mechanism": (
            position.short_mechanism
        ),
        "short_financing_model": (
            position.short_financing_model
        ),
        "execution_profile": (
            position.execution_profile.value
        ),
        "execution_quality_at_entry": (
            position
            .execution_quality_at_entry
            .value
        ),
        "status": (
            position.status.value
        ),
        "closed_at": (
            _datetime_to_text(
                position.closed_at
            )
        ),
        "exit_execution_id": (
            position.exit_execution_id
        ),
        "exit_price": (
            position.exit_price
        ),
        "pending_exit_reason": (
            position.pending_exit_reason
        ),
        "pending_since": (
            _datetime_to_text(
                position.pending_since
            )
        ),
    }


def _position_from_dict(
    payload,
):
    if (
        payload.get(
            "execution_profile"
        )
        != ExecutionProfile.REALISTIC_V2.value
    ):
        raise ValueError(
            "Stored position is not REALISTIC_V2"
        )

    return Position(
        position_id=str(
            payload["position_id"]
        ),
        asset_id=str(
            payload["asset_id"]
        ),
        side=PositionSide(
            payload["side"]
        ),
        quantity=float(
            payload["quantity"]
        ),
        entry_execution_id=str(
            payload[
                "entry_execution_id"
            ]
        ),
        entry_price=float(
            payload["entry_price"]
        ),
        stop_loss=(
            None
            if payload.get(
                "stop_loss"
            )
            is None
            else float(
                payload["stop_loss"]
            )
        ),
        take_profit=(
            None
            if payload.get(
                "take_profit"
            )
            is None
            else float(
                payload[
                    "take_profit"
                ]
            )
        ),
        opened_at=(
            _datetime_from_text(
                payload["opened_at"]
            )
        ),
        short_mechanism=(
            payload.get(
                "short_mechanism"
            )
        ),
        short_financing_model=(
            payload.get(
                "short_financing_model"
            )
        ),
        execution_profile=(
            ExecutionProfile.REALISTIC_V2
        ),
        execution_quality_at_entry=(
            ExecutionQuality(
                payload[
                    "execution_quality_at_entry"
                ]
            )
        ),
        status=PositionStatus(
            payload["status"]
        ),
        closed_at=(
            _datetime_from_text(
                payload.get(
                    "closed_at"
                )
            )
        ),
        exit_execution_id=(
            payload.get(
                "exit_execution_id"
            )
        ),
        exit_price=(
            None
            if payload.get(
                "exit_price"
            )
            is None
            else float(
                payload[
                    "exit_price"
                ]
            )
        ),
        pending_exit_reason=(
            payload.get(
                "pending_exit_reason"
            )
        ),
        pending_since=(
            _datetime_from_text(
                payload.get(
                    "pending_since"
                )
            )
        ),
    )


class RealisticPaperStateStore:
    """
    Atomic JSON persistence for REALISTIC_V2 positions.

    This store is deliberately separate from the
    existing LEGACY data/live_state files.

    No default path is provided intentionally.
    The caller must explicitly select the state file.
    """

    def __init__(
        self,
        path,
        *,
        clock: Clock | None = None,
    ):
        self.path = Path(
            path
        )

        self.clock = (
            clock
            or SystemClock()
        )

    def load_positions(
        self,
    ):
        if not self.path.exists():
            return {}

        with self.path.open(
            "r",
            encoding="utf-8-sig",
        ) as handle:
            payload = json.load(
                handle
            )

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "State payload must be an object"
            )

        if (
            payload.get(
                "schema_version"
            )
            != _SCHEMA_VERSION
        ):
            raise ValueError(
                "Unsupported state schema version"
            )

        if (
            payload.get(
                "execution_profile"
            )
            != ExecutionProfile.REALISTIC_V2.value
        ):
            raise ValueError(
                "State file must use REALISTIC_V2"
            )

        records = payload.get(
            "positions",
            [],
        )

        if not isinstance(
            records,
            list,
        ):
            raise ValueError(
                "positions must be a list"
            )

        positions = {}

        for record in records:
            position = (
                _position_from_dict(
                    record
                )
            )

            if (
                position.status
                is PositionStatus.CLOSED
            ):
                raise ValueError(
                    "Closed positions must not "
                    "remain in active state"
                )

            if (
                position.asset_id
                in positions
            ):
                raise ValueError(
                    "Duplicate asset position "
                    f"{position.asset_id}"
                )

            positions[
                position.asset_id
            ] = position

        return positions

    def save_positions(
        self,
        positions,
    ):
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        records = []

        for asset_id in sorted(
            positions
        ):
            position = (
                positions[
                    asset_id
                ]
            )

            if (
                position.asset_id
                != asset_id
            ):
                raise ValueError(
                    "Position mapping key "
                    "does not match asset_id"
                )

            if (
                position.status
                is PositionStatus.CLOSED
            ):
                continue

            records.append(
                _position_to_dict(
                    position
                )
            )

        payload = {
            "schema_version": (
                _SCHEMA_VERSION
            ),
            "execution_profile": (
                ExecutionProfile
                .REALISTIC_V2
                .value
            ),
            "updated_at": (
                _datetime_to_text(
                    self.clock.now()
                )
            ),
            "positions": records,
        }

        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=str(
                    self.path.parent
                ),
                prefix=(
                    f".{self.path.name}."
                ),
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_path = Path(
                    handle.name
                )

                json.dump(
                    payload,
                    handle,
                    indent=2,
                    sort_keys=True,
                )

                handle.write(
                    "\n"
                )

                handle.flush()

                os.fsync(
                    handle.fileno()
                )

            os.replace(
                temp_path,
                self.path,
            )

        except Exception:
            if (
                temp_path is not None
                and temp_path.exists()
            ):
                try:
                    temp_path.unlink()
                except OSError:
                    pass

            raise
