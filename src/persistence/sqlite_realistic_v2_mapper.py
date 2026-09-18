from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from src.persistence.sqlite_injected_runtime import (
    InjectedCycleWrite,
)


class RealisticV2SQLiteMapperError(ValueError):
    pass


def _enum_text(value):
    raw = getattr(
        value,
        "value",
        value,
    )

    if raw is None:
        return None

    return str(raw).strip()


def _required_text(value, field_name):
    result = _enum_text(value)

    if not result:
        raise RealisticV2SQLiteMapperError(
            f"{field_name} is required"
        )

    return result


def _decimal_text(value, field_name):
    if value is None:
        raise RealisticV2SQLiteMapperError(
            f"{field_name} is required"
        )

    try:
        result = Decimal(
            str(value)
        )
    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ) as exc:
        raise RealisticV2SQLiteMapperError(
            f"{field_name} must be decimal"
        ) from exc

    if not result.is_finite():
        raise RealisticV2SQLiteMapperError(
            f"{field_name} must be finite"
        )

    return format(
        result,
        "f",
    )


def _optional_decimal_text(value):
    if value is None:
        return None

    return _decimal_text(
        value,
        "decimal value",
    )


def _datetime_text(value, field_name):
    if value is None:
        raise RealisticV2SQLiteMapperError(
            f"{field_name} is required"
        )

    if isinstance(
        value,
        datetime,
    ):
        if value.tzinfo is None:
            raise RealisticV2SQLiteMapperError(
                f"{field_name} must be timezone-aware"
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

    text = str(value).strip()

    if not text:
        raise RealisticV2SQLiteMapperError(
            f"{field_name} is required"
        )

    return text


def _required_mapping_value(
    mapping,
    field_name,
):
    if not isinstance(
        mapping,
        dict,
    ):
        raise RealisticV2SQLiteMapperError(
            "evidence resolver must return dict"
        )

    if field_name not in mapping:
        raise RealisticV2SQLiteMapperError(
            f"{field_name} evidence is required"
        )

    value = mapping[
        field_name
    ]

    if value is None:
        raise RealisticV2SQLiteMapperError(
            f"{field_name} evidence is required"
        )

    return value


def _canonical_identity_hash(identity):
    encoded = json.dumps(
        identity,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        encoded
    ).hexdigest()


class RealisticV2SQLiteMapper:
    """
    Maps the existing REALISTIC_V2 runtime/accounting result shape into
    Phase 13 SQLite payloads.

    No FX/PLN cost evidence is fabricated. Evidence absent from the
    runtime objects must be supplied by explicit resolver callbacks.
    """

    def __init__(
        self,
        *,
        order_fingerprint_resolver,
        execution_evidence_resolver,
        realized_evidence_resolver,
        strategy_id="REALISTIC_V2",
    ):
        if not callable(
            order_fingerprint_resolver
        ):
            raise TypeError(
                "order_fingerprint_resolver must be callable"
            )

        if not callable(
            execution_evidence_resolver
        ):
            raise TypeError(
                "execution_evidence_resolver must be callable"
            )

        if not callable(
            realized_evidence_resolver
        ):
            raise TypeError(
                "realized_evidence_resolver must be callable"
            )

        self.order_fingerprint_resolver = (
            order_fingerprint_resolver
        )
        self.execution_evidence_resolver = (
            execution_evidence_resolver
        )
        self.realized_evidence_resolver = (
            realized_evidence_resolver
        )
        self.strategy_id = _required_text(
            strategy_id,
            "strategy_id",
        )

    def _asset_result(
        self,
        *,
        asset_id,
        runtime_result,
    ):
        execution_cycle = getattr(
            runtime_result,
            "execution_cycle",
            runtime_result,
        )

        results = getattr(
            execution_cycle,
            "results",
            None,
        )

        if results is None:
            raise RealisticV2SQLiteMapperError(
                "runtime result has no execution results"
            )

        try:
            asset_result = results[
                asset_id
            ]
        except Exception as exc:
            raise RealisticV2SQLiteMapperError(
                "asset result is missing"
            ) from exc

        return asset_result

    def _accounting_result(
        self,
        *,
        asset_id,
        runtime_result,
    ):
        results = getattr(
            runtime_result,
            "accounting_results",
            None,
        )

        if results is None:
            raise RealisticV2SQLiteMapperError(
                "runtime result has no accounting_results"
            )

        try:
            return results[
                asset_id
            ]
        except Exception as exc:
            raise RealisticV2SQLiteMapperError(
                "accounting result is missing"
            ) from exc

    def _order_payload(
        self,
        *,
        order,
        execution,
        broker_status,
    ):
        fingerprint = _required_text(
            self.order_fingerprint_resolver(
                order
            ),
            "order_fingerprint",
        )

        provider_timestamp = (
            _datetime_text(
                getattr(
                    execution,
                    "provider_timestamp",
                    None,
                ),
                "execution.provider_timestamp",
            )
        )

        return {
            "order_id": _required_text(
                getattr(
                    order,
                    "order_id",
                    None,
                ),
                "order.order_id",
            ),
            "client_order_id": _required_text(
                getattr(
                    order,
                    "client_order_id",
                    None,
                ),
                "order.client_order_id",
            ),
            "asset_id": _required_text(
                getattr(
                    order,
                    "asset_id",
                    None,
                ),
                "order.asset_id",
            ),
            "strategy_id": self.strategy_id,
            "intent": _required_text(
                getattr(
                    order,
                    "intent",
                    None,
                ),
                "order.intent",
            ),
            "side": _required_text(
                getattr(
                    order,
                    "side",
                    None,
                ),
                "order.side",
            ),
            "quantity_native": _decimal_text(
                getattr(
                    order,
                    "quantity",
                    None,
                ),
                "order.quantity",
            ),
            "signal_reference": (
                _enum_text(
                    getattr(
                        order,
                        "signal_reference",
                        None,
                    )
                )
                or self.strategy_id
            ),
            "source_timestamp_utc": provider_timestamp,
            "created_at_utc": _datetime_text(
                getattr(
                    order,
                    "created_at",
                    None,
                ),
                "order.created_at",
            ),
            "execution_profile": _required_text(
                getattr(
                    order,
                    "execution_profile",
                    None,
                ),
                "order.execution_profile",
            ),
            "paper_mode": _required_text(
                getattr(
                    order,
                    "paper_mode",
                    None,
                ),
                "order.paper_mode",
            ),
            "status": broker_status,
            "config_hash": _required_text(
                getattr(
                    execution,
                    "config_hash",
                    None,
                ),
                "execution.config_hash",
            ),
            "order_fingerprint": fingerprint,
            "raw_json": {
                "source": "REALISTIC_V2_RUNTIME",
            },
        }

    def _execution_payload(
        self,
        *,
        execution,
        intent,
        realized_result,
    ):
        evidence = (
            self.execution_evidence_resolver(
                execution=execution,
                intent=intent,
                realized_result=realized_result,
            )
        )

        fee_pln = _decimal_text(
            _required_mapping_value(
                evidence,
                "fee_pln",
            ),
            "fee_pln",
        )

        fx_path = _required_text(
            _required_mapping_value(
                evidence,
                "fx_path",
            ),
            "fx_path",
        )

        fx_rate = _decimal_text(
            _required_mapping_value(
                evidence,
                "fx_rate",
            ),
            "fx_rate",
        )

        fx_provider = _required_text(
            _required_mapping_value(
                evidence,
                "fx_provider",
            ),
            "fx_provider",
        )

        fx_timestamp = _datetime_text(
            _required_mapping_value(
                evidence,
                "fx_timestamp_utc",
            ),
            "fx_timestamp_utc",
        )

        fx_quality = _required_text(
            _required_mapping_value(
                evidence,
                "fx_quality",
            ),
            "fx_quality",
        )

        return {
            "execution_id": _required_text(
                getattr(
                    execution,
                    "execution_id",
                    None,
                ),
                "execution.execution_id",
            ),
            "order_id": _required_text(
                getattr(
                    execution,
                    "order_id",
                    None,
                ),
                "execution.order_id",
            ),
            "asset_id": _required_text(
                getattr(
                    execution,
                    "asset_id",
                    None,
                ),
                "execution.asset_id",
            ),
            "side": _required_text(
                getattr(
                    execution,
                    "side",
                    None,
                ),
                "execution.side",
            ),
            "quantity_native": _decimal_text(
                getattr(
                    execution,
                    "quantity",
                    None,
                ),
                "execution.quantity",
            ),
            "reference_price_native": _decimal_text(
                getattr(
                    execution,
                    "reference_price",
                    None,
                ),
                "execution.reference_price",
            ),
            "execution_price_native": _decimal_text(
                getattr(
                    execution,
                    "execution_price",
                    None,
                ),
                "execution.execution_price",
            ),
            "bid_native": _decimal_text(
                getattr(
                    execution,
                    "bid",
                    None,
                ),
                "execution.bid",
            ),
            "ask_native": _decimal_text(
                getattr(
                    execution,
                    "ask",
                    None,
                ),
                "execution.ask",
            ),
            "spread_native": _decimal_text(
                getattr(
                    execution,
                    "spread",
                    None,
                ),
                "execution.spread",
            ),
            "slippage_native": _decimal_text(
                getattr(
                    execution,
                    "slippage",
                    None,
                ),
                "execution.slippage",
            ),
            "fee_native": _decimal_text(
                getattr(
                    execution,
                    "fee",
                    None,
                ),
                "execution.fee",
            ),
            "fee_pln": fee_pln,
            "provider_timestamp_utc": _datetime_text(
                getattr(
                    execution,
                    "provider_timestamp",
                    None,
                ),
                "execution.provider_timestamp",
            ),
            "execution_timestamp_utc": _datetime_text(
                getattr(
                    execution,
                    "execution_timestamp",
                    None,
                ),
                "execution.execution_timestamp",
            ),
            "data_quality": _required_text(
                getattr(
                    execution,
                    "data_quality",
                    None,
                ),
                "execution.data_quality",
            ),
            "execution_quality": _required_text(
                getattr(
                    execution,
                    "execution_quality",
                    None,
                ),
                "execution.execution_quality",
            ),
            "session_quality": _required_text(
                getattr(
                    execution,
                    "session_quality",
                    None,
                ),
                "execution.session_quality",
            ),
            "fx_path": fx_path,
            "fx_rate": fx_rate,
            "fx_provider": fx_provider,
            "fx_timestamp_utc": fx_timestamp,
            "fx_quality": fx_quality,
            "config_hash": _required_text(
                getattr(
                    execution,
                    "config_hash",
                    None,
                ),
                "execution.config_hash",
            ),
            "raw_json": {
                "source": "REALISTIC_V2_RUNTIME",
            },
        }

    def _position_payload(
        self,
        position,
    ):
        return {
            "position_id": _required_text(
                getattr(
                    position,
                    "position_id",
                    None,
                ),
                "position.position_id",
            ),
            "asset_id": _required_text(
                getattr(
                    position,
                    "asset_id",
                    None,
                ),
                "position.asset_id",
            ),
            "side": _required_text(
                getattr(
                    position,
                    "side",
                    None,
                ),
                "position.side",
            ),
            "quantity_native": _decimal_text(
                getattr(
                    position,
                    "quantity",
                    None,
                ),
                "position.quantity",
            ),
            "entry_execution_id": _required_text(
                getattr(
                    position,
                    "entry_execution_id",
                    None,
                ),
                "position.entry_execution_id",
            ),
            "exit_execution_id": (
                _enum_text(
                    getattr(
                        position,
                        "exit_execution_id",
                        None,
                    )
                )
                or None
            ),
            "entry_price_native": _decimal_text(
                getattr(
                    position,
                    "entry_price",
                    None,
                ),
                "position.entry_price",
            ),
            "exit_price_native": _optional_decimal_text(
                getattr(
                    position,
                    "exit_price",
                    None,
                )
            ),
            "stop_loss_native": _optional_decimal_text(
                getattr(
                    position,
                    "stop_loss",
                    None,
                )
            ),
            "take_profit_native": _optional_decimal_text(
                getattr(
                    position,
                    "take_profit",
                    None,
                )
            ),
            "status": _required_text(
                getattr(
                    position,
                    "status",
                    None,
                ),
                "position.status",
            ),
            "opened_at_utc": _datetime_text(
                getattr(
                    position,
                    "opened_at",
                    None,
                ),
                "position.opened_at",
            ),
            "closed_at_utc": (
                None
                if getattr(
                    position,
                    "closed_at",
                    None,
                ) is None
                else _datetime_text(
                    position.closed_at,
                    "position.closed_at",
                )
            ),
            "short_mechanism": getattr(
                position,
                "short_mechanism",
                None,
            ),
            "short_financing_model": getattr(
                position,
                "short_financing_model",
                None,
            ),
            "execution_profile": _required_text(
                getattr(
                    position,
                    "execution_profile",
                    None,
                ),
                "position.execution_profile",
            ),
            "execution_quality_at_entry": _required_text(
                getattr(
                    position,
                    "execution_quality_at_entry",
                    None,
                ),
                "position.execution_quality_at_entry",
            ),
            "unrealized_pnl_native": "0",
            "unrealized_pnl_pln": "0",
            "raw_json": {
                "source": "REALISTIC_V2_RUNTIME",
            },
        }

    def _realized_payloads(
        self,
        *,
        asset_id,
        position,
        execution,
        realized_result,
    ):
        accounting = getattr(
            realized_result,
            "accounting_record",
            None,
        )

        if accounting is None:
            raise RealisticV2SQLiteMapperError(
                "realized_result.accounting_record is required"
            )

        booking = getattr(
            realized_result,
            "fx_booking",
            None,
        )

        if booking is None:
            raise RealisticV2SQLiteMapperError(
                "realized_result.fx_booking is required"
            )

        evidence = (
            self.realized_evidence_resolver(
                asset_id=asset_id,
                position=position,
                execution=execution,
                realized_result=realized_result,
            )
        )

        fees_pln = _decimal_text(
            _required_mapping_value(
                evidence,
                "fees_pln",
            ),
            "fees_pln",
        )
        spread_cost_pln = _decimal_text(
            _required_mapping_value(
                evidence,
                "spread_cost_pln",
            ),
            "spread_cost_pln",
        )
        slippage_pln = _decimal_text(
            _required_mapping_value(
                evidence,
                "slippage_pln",
            ),
            "slippage_pln",
        )
        fx_pair = _required_text(
            _required_mapping_value(
                evidence,
                "fx_pair",
            ),
            "fx_pair",
        )
        fx_provider = _required_text(
            _required_mapping_value(
                evidence,
                "fx_provider",
            ),
            "fx_provider",
        )
        fx_timestamp = _datetime_text(
            _required_mapping_value(
                evidence,
                "fx_timestamp_utc",
            ),
            "fx_timestamp_utc",
        )
        fx_quality = _required_text(
            _required_mapping_value(
                evidence,
                "fx_quality",
            ),
            "fx_quality",
        )

        booking_provider = _required_text(
            getattr(
                booking,
                "fx_provider",
                None,
            ),
            "fx_booking.fx_provider",
        )

        if fx_provider != booking_provider:
            raise RealisticV2SQLiteMapperError(
                "realized FX provider evidence mismatch"
            )

        position_id = _required_text(
            getattr(
                position,
                "position_id",
                None,
            ),
            "position.position_id",
        )
        entry_execution_id = _required_text(
            getattr(
                position,
                "entry_execution_id",
                None,
            ),
            "position.entry_execution_id",
        )
        exit_execution_id = _required_text(
            getattr(
                position,
                "exit_execution_id",
                None,
            ),
            "position.exit_execution_id",
        )

        actual_exit_execution_id = _required_text(
            getattr(
                execution,
                "execution_id",
                None,
            ),
            "execution.execution_id",
        )

        if exit_execution_id != actual_exit_execution_id:
            raise RealisticV2SQLiteMapperError(
                "exit execution identity mismatch"
            )

        identity = {
            "asset_id": asset_id,
            "position_id": position_id,
            "entry_execution_id": entry_execution_id,
            "exit_execution_id": exit_execution_id,
        }

        identity_hash = _canonical_identity_hash(
            identity
        )

        trade_id = (
            "trade-"
            + identity_hash
        )
        transaction_id = (
            "realized-"
            + identity_hash
        )

        net_native = _decimal_text(
            getattr(
                accounting,
                "net_realized_pnl_native",
                None,
            ),
            "accounting_record.net_realized_pnl_native",
        )
        net_pln = _decimal_text(
            getattr(
                accounting,
                "net_realized_pnl_pln",
                None,
            ),
            "accounting_record.net_realized_pnl_pln",
        )
        fx_rate = _decimal_text(
            getattr(
                accounting,
                "fx_rate",
                None,
            ),
            "accounting_record.fx_rate",
        )
        fx_path = _required_text(
            getattr(
                accounting,
                "fx_path",
                None,
            ),
            "accounting_record.fx_path",
        )

        closed_at = _datetime_text(
            getattr(
                position,
                "closed_at",
                None,
            ),
            "position.closed_at",
        )

        trade = {
            "trade_id": trade_id,
            "asset_id": asset_id,
            "position_id": position_id,
            "entry_execution_id": entry_execution_id,
            "exit_execution_id": exit_execution_id,
            "quantity_native": _decimal_text(
                getattr(
                    position,
                    "quantity",
                    None,
                ),
                "position.quantity",
            ),
            "realized_pnl_native": net_native,
            "realized_pnl_pln": net_pln,
            "fees_pln": fees_pln,
            "spread_cost_pln": spread_cost_pln,
            "slippage_pln": slippage_pln,
            "realized_fx_pair": fx_pair,
            "realized_fx_path": fx_path,
            "realized_fx_rate": fx_rate,
            "realized_fx_provider": fx_provider,
            "realized_fx_timestamp_utc": fx_timestamp,
            "realized_fx_quality": fx_quality,
            "realized_transaction_id": transaction_id,
            "opened_at_utc": _datetime_text(
                getattr(
                    position,
                    "opened_at",
                    None,
                ),
                "position.opened_at",
            ),
            "closed_at_utc": closed_at,
            "raw_json": {
                "source": "REALISTIC_V2_RUNTIME",
                "identity_hash": identity_hash,
            },
        }

        transaction = {
            "transaction_id": transaction_id,
            "transaction_type": "REALIZED_PNL",
            "amount_pln": net_pln,
            "asset_id": asset_id,
            "reference_type": "TRADE",
            "reference_id": trade_id,
            "booked_at_utc": closed_at,
            "fx_pair": fx_pair,
            "fx_path": fx_path,
            "fx_rate": fx_rate,
            "fx_provider": fx_provider,
            "fx_timestamp_utc": fx_timestamp,
            "fx_quality": fx_quality,
            "raw_json": {
                "source": "REALISTIC_V2_RUNTIME",
                "identity_hash": identity_hash,
            },
        }

        return (
            trade,
            transaction,
        )

    def __call__(
        self,
        *,
        asset_id,
        runtime_result,
    ):
        asset_id = _required_text(
            asset_id,
            "asset_id",
        )

        asset_result = self._asset_result(
            asset_id=asset_id,
            runtime_result=runtime_result,
        )

        status = _required_text(
            getattr(
                asset_result,
                "status",
                None,
            ),
            "asset_result.status",
        )

        if status != "FILLED":
            return InjectedCycleWrite(
                intent="NOOP",
                processed_timestamp_utc=None,
                updated_at_utc=None,
            )

        broker_result = getattr(
            asset_result,
            "broker_result",
            None,
        )

        if broker_result is None:
            raise RealisticV2SQLiteMapperError(
                "FILLED result requires broker_result"
            )

        order = getattr(
            broker_result,
            "order",
            None,
        )
        execution = getattr(
            broker_result,
            "execution",
            None,
        )
        position = getattr(
            broker_result,
            "position",
            None,
        )

        if order is None:
            raise RealisticV2SQLiteMapperError(
                "broker_result.order is required"
            )
        if execution is None:
            raise RealisticV2SQLiteMapperError(
                "broker_result.execution is required"
            )
        if position is None:
            raise RealisticV2SQLiteMapperError(
                "broker_result.position is required"
            )

        intent = _required_text(
            getattr(
                order,
                "intent",
                None,
            ),
            "order.intent",
        ).upper()

        order_asset = _required_text(
            getattr(
                order,
                "asset_id",
                None,
            ),
            "order.asset_id",
        )
        execution_asset = _required_text(
            getattr(
                execution,
                "asset_id",
                None,
            ),
            "execution.asset_id",
        )
        position_asset = _required_text(
            getattr(
                position,
                "asset_id",
                None,
            ),
            "position.asset_id",
        )

        if (
            order_asset != asset_id
            or execution_asset != asset_id
            or position_asset != asset_id
        ):
            raise RealisticV2SQLiteMapperError(
                "runtime asset identity mismatch"
            )

        realized = None

        if intent == "EXIT":
            accounting_result = self._accounting_result(
                asset_id=asset_id,
                runtime_result=runtime_result,
            )

            error = getattr(
                accounting_result,
                "error",
                None,
            )

            if error is not None:
                raise RealisticV2SQLiteMapperError(
                    "accounting result contains error"
                )

            realized = getattr(
                accounting_result,
                "realized_result",
                None,
            )

            if realized is None:
                raise RealisticV2SQLiteMapperError(
                    "EXIT requires realized_result"
                )

        order_payload = self._order_payload(
            order=order,
            execution=execution,
            broker_status=status,
        )
        execution_payload = self._execution_payload(
            execution=execution,
            intent=intent,
            realized_result=realized,
        )
        position_payload = self._position_payload(
            position
        )

        processed_timestamp = (
            execution_payload[
                "execution_timestamp_utc"
            ]
        )

        if intent == "ENTRY":
            if position_payload["status"] != "OPEN":
                raise RealisticV2SQLiteMapperError(
                    "ENTRY requires OPEN position"
                )

            return InjectedCycleWrite(
                intent="ENTRY",
                processed_timestamp_utc=processed_timestamp,
                updated_at_utc=processed_timestamp,
                order=order_payload,
                execution=execution_payload,
                position=position_payload,
            )

        if intent == "EXIT":
            if position_payload["status"] != "CLOSED":
                raise RealisticV2SQLiteMapperError(
                    "EXIT requires CLOSED position"
                )

            (
                trade_payload,
                transaction_payload,
            ) = self._realized_payloads(
                asset_id=asset_id,
                position=position,
                execution=execution,
                realized_result=realized,
            )

            return InjectedCycleWrite(
                intent="EXIT",
                processed_timestamp_utc=processed_timestamp,
                updated_at_utc=processed_timestamp,
                reconciliation_event_id=(
                    "reconcile-"
                    + transaction_payload[
                        "transaction_id"
                    ]
                ),
                order=order_payload,
                execution=execution_payload,
                position=position_payload,
                trade=trade_payload,
                portfolio_transaction=transaction_payload,
            )

        raise RealisticV2SQLiteMapperError(
            "FILLED order intent must be ENTRY or EXIT"
        )
