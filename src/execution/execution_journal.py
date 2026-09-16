from __future__ import annotations

import importlib
import json
import os
from dataclasses import (
    fields,
    is_dataclass,
)
from datetime import (
    datetime,
    timezone,
)
from enum import Enum
from pathlib import Path

from src.core.clock import (
    Clock,
    SystemClock,
)


_SCHEMA_VERSION = 1

_ALLOWED_MODULES = {
    "src.execution.models",
    "src.data.market_data",
    "src.market.market_session",
    "src.data.assets",
}


def _datetime_text(
    value,
):
    if value.tzinfo is None:
        raise ValueError(
            "Journal datetime must be timezone-aware"
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


def _parse_datetime(
    value,
):
    result = datetime.fromisoformat(
        str(value).replace(
            "Z",
            "+00:00",
        )
    )

    if result.tzinfo is None:
        raise ValueError(
            "Journal datetime must be timezone-aware"
        )

    return result.astimezone(
        timezone.utc
    )


def _class_path(
    value,
):
    cls = type(value)

    return (
        f"{cls.__module__}:"
        f"{cls.__qualname__}"
    )


def _load_class(
    path,
):
    module_name, class_name = (
        path.split(
            ":",
            1,
        )
    )

    if (
        module_name
        not in _ALLOWED_MODULES
    ):
        raise ValueError(
            "Journal class module is not allowed: "
            f"{module_name}"
        )

    module = importlib.import_module(
        module_name
    )

    target = module

    for part in class_name.split(
        "."
    ):
        target = getattr(
            target,
            part,
        )

    return target


def _encode(
    value,
):
    if value is None:
        return None

    # Enum must be checked before str/int.
    # Our execution enums derive from str, Enum.
    # Checking primitives first would serialize them
    # as plain strings and destroy their type across
    # a restart.
    if isinstance(
        value,
        Enum,
    ):
        return {
            "__enum__": (
                _class_path(
                    value
                )
            ),
            "value": (
                _encode(
                    value.value
                )
            ),
        }

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    if isinstance(
        value,
        datetime,
    ):
        return {
            "__datetime__": (
                _datetime_text(
                    value
                )
            )
        }

    if is_dataclass(
        value
    ):
        return {
            "__dataclass__": (
                _class_path(
                    value
                )
            ),
            "fields": {
                field.name: _encode(
                    getattr(
                        value,
                        field.name,
                    )
                )
                for field in fields(
                    value
                )
            },
        }

    if isinstance(
        value,
        tuple,
    ):
        return {
            "__tuple__": [
                _encode(item)
                for item in value
            ]
        }

    if isinstance(
        value,
        list,
    ):
        return [
            _encode(item)
            for item in value
        ]

    if isinstance(
        value,
        dict,
    ):
        return {
            str(key): _encode(
                item
            )
            for key, item
            in value.items()
        }

    raise TypeError(
        "Unsupported journal value: "
        f"{type(value).__name__}"
    )


def _decode(
    value,
):
    if not isinstance(
        value,
        (
            dict,
            list,
        ),
    ):
        return value

    if isinstance(
        value,
        list,
    ):
        return [
            _decode(item)
            for item in value
        ]

    if "__datetime__" in value:
        return _parse_datetime(
            value[
                "__datetime__"
            ]
        )

    if "__enum__" in value:
        cls = _load_class(
            value[
                "__enum__"
            ]
        )

        return cls(
            _decode(
                value["value"]
            )
        )

    if "__tuple__" in value:
        return tuple(
            _decode(item)
            for item
            in value[
                "__tuple__"
            ]
        )

    if "__dataclass__" in value:
        cls = _load_class(
            value[
                "__dataclass__"
            ]
        )

        kwargs = {
            name: _decode(
                item
            )
            for name, item
            in value[
                "fields"
            ].items()
        }

        return cls(
            **kwargs
        )

    return {
        key: _decode(
            item
        )
        for key, item
        in value.items()
    }


class RealisticExecutionJournal:
    """
    Append-only REALISTIC_V2 write-ahead journal.

    PREPARED is fsync'd before broker processing.
    COMMITTED is written only after runtime state
    persistence succeeds.

    An unresolved PREPARED record is intentionally
    fail-closed after restart.
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

    def _append(
        self,
        payload,
    ):
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        )

        with self.path.open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                encoded
            )

            handle.write(
                "\n"
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

    def _scan(
        self,
    ):
        prepared = {}
        committed = {}
        order_sequence = []

        if not self.path.exists():
            return (
                prepared,
                committed,
                order_sequence,
            )

        with self.path.open(
            "r",
            encoding="utf-8-sig",
        ) as handle:
            for line_number, line in enumerate(
                handle,
                start=1,
            ):
                line = line.strip()

                if not line:
                    continue

                try:
                    record = json.loads(
                        line
                    )

                except json.JSONDecodeError as exc:
                    raise ValueError(
                        "Invalid execution journal "
                        f"JSON at line {line_number}"
                    ) from exc

                if (
                    record.get(
                        "schema_version"
                    )
                    != _SCHEMA_VERSION
                ):
                    raise ValueError(
                        "Unsupported execution "
                        "journal schema"
                    )

                record_type = (
                    record.get(
                        "record_type"
                    )
                )

                client_id = str(
                    record.get(
                        "client_order_id"
                    )
                )

                fingerprint = str(
                    record.get(
                        "order_fingerprint"
                    )
                )

                if (
                    not client_id
                    or client_id == "None"
                    or not fingerprint
                    or fingerprint == "None"
                ):
                    raise ValueError(
                        "Invalid journal identity"
                    )

                if (
                    record_type
                    == "PREPARED"
                ):
                    previous = (
                        prepared.get(
                            client_id
                        )
                    )

                    if (
                        previous is not None
                        and previous[
                            "order_fingerprint"
                        ]
                        != fingerprint
                    ):
                        raise ValueError(
                            "Conflicting PREPARED "
                            f"record for {client_id}"
                        )

                    if previous is None:
                        prepared[
                            client_id
                        ] = record

                        order_sequence.append(
                            client_id
                        )

                elif (
                    record_type
                    == "COMMITTED"
                ):
                    original = (
                        prepared.get(
                            client_id
                        )
                    )

                    if original is None:
                        raise ValueError(
                            "COMMITTED record has "
                            "no PREPARED record"
                        )

                    if (
                        original[
                            "order_fingerprint"
                        ]
                        != fingerprint
                    ):
                        raise ValueError(
                            "Journal fingerprint "
                            "mismatch"
                        )

                    previous = (
                        committed.get(
                            client_id
                        )
                    )

                    if previous is not None:
                        continue

                    committed[
                        client_id
                    ] = record

                else:
                    raise ValueError(
                        "Unknown journal record type"
                    )

        return (
            prepared,
            committed,
            order_sequence,
        )

    def prepare(
        self,
        *,
        order,
        order_fingerprint,
    ):
        (
            prepared,
            committed,
            _,
        ) = self._scan()

        client_id = (
            order.client_order_id
        )

        existing = (
            prepared.get(
                client_id
            )
        )

        if existing is not None:
            if (
                existing[
                    "order_fingerprint"
                ]
                != order_fingerprint
            ):
                raise ValueError(
                    "Journal idempotency conflict "
                    f"for {client_id}"
                )

            return

        if client_id in committed:
            return

        self._append(
            {
                "schema_version": (
                    _SCHEMA_VERSION
                ),
                "record_type": (
                    "PREPARED"
                ),
                "recorded_at": (
                    _datetime_text(
                        self.clock.now()
                    )
                ),
                "client_order_id": (
                    client_id
                ),
                "asset_id": (
                    order.asset_id
                ),
                "order_fingerprint": (
                    order_fingerprint
                ),
                "order": _encode(
                    order
                ),
            }
        )

    def commit(
        self,
        *,
        broker_result,
        order_fingerprint,
    ):
        (
            prepared,
            committed,
            _,
        ) = self._scan()

        client_id = (
            broker_result
            .order
            .client_order_id
        )

        if client_id in committed:
            return

        original = prepared.get(
            client_id
        )

        if original is None:
            raise ValueError(
                "Cannot COMMIT without PREPARED "
                f"record for {client_id}"
            )

        if (
            original[
                "order_fingerprint"
            ]
            != order_fingerprint
        ):
            raise ValueError(
                "Journal COMMIT fingerprint "
                "does not match PREPARED"
            )

        self._append(
            {
                "schema_version": (
                    _SCHEMA_VERSION
                ),
                "record_type": (
                    "COMMITTED"
                ),
                "recorded_at": (
                    _datetime_text(
                        self.clock.now()
                    )
                ),
                "client_order_id": (
                    client_id
                ),
                "asset_id": (
                    broker_result
                    .order
                    .asset_id
                ),
                "order_fingerprint": (
                    order_fingerprint
                ),
                "broker_result": (
                    _encode(
                        broker_result
                    )
                ),
            }
        )

    def unresolved_client_order_ids(
        self,
    ):
        (
            prepared,
            committed,
            sequence,
        ) = self._scan()

        return tuple(
            client_id
            for client_id
            in sequence
            if client_id
            not in committed
        )

    def unresolved_assets(
        self,
    ):
        (
            prepared,
            committed,
            sequence,
        ) = self._scan()

        assets = []

        for client_id in sequence:
            if client_id in committed:
                continue

            asset_id = str(
                prepared[
                    client_id
                ][
                    "asset_id"
                ]
            )

            if asset_id not in assets:
                assets.append(
                    asset_id
                )

        return tuple(
            assets
        )

    def has_unresolved_asset(
        self,
        asset_id,
    ):
        return (
            str(asset_id)
            in self.unresolved_assets()
        )

    def committed_results(
        self,
    ):
        (
            _,
            committed,
            sequence,
        ) = self._scan()

        results = []

        for client_id in sequence:
            record = (
                committed.get(
                    client_id
                )
            )

            if record is None:
                continue

            results.append(
                _decode(
                    record[
                        "broker_result"
                    ]
                )
            )

        return tuple(
            results
        )

    def restore_broker(
        self,
        broker,
    ):
        for result in (
            self.committed_results()
        ):
            broker.restore_idempotency_result(
                result
            )
