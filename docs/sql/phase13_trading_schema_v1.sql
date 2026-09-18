-- PHASE 13 SQLITE LEDGER SCHEMA V1
--
-- DESIGN ARTIFACT ONLY.
-- This file MUST NOT be applied to production/live data in Phase 13 A.2.
--
-- Financial decimal values are stored as canonical decimal TEXT.
-- Repository code must use Python Decimal and must not silently round
-- existing values during future migration.
--
-- Connection policy is defined outside this DDL:
--   journal_mode = WAL
--   busy_timeout configured
--   foreign_keys = ON
--   synchronous = FULL
--
-- One writer:
--   paper-live runtime
--
-- API:
--   read-only connection

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    migration_name TEXT NOT NULL UNIQUE,
    checksum_sha256 TEXT NOT NULL,
    applied_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS system_state (
    state_id INTEGER PRIMARY KEY
        CHECK (state_id = 1),

    cash_balance_pln TEXT NOT NULL,

    halted INTEGER NOT NULL DEFAULT 0
        CHECK (halted IN (0, 1)),

    halt_reason TEXT,

    last_processed_timestamp_utc TEXT,

    updated_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,

    client_order_id TEXT NOT NULL UNIQUE,

    asset_id TEXT NOT NULL,
    strategy_id TEXT,

    intent TEXT NOT NULL,
    side TEXT NOT NULL,

    quantity_native TEXT NOT NULL,

    signal_reference TEXT,

    source_timestamp_utc TEXT,
    created_at_utc TEXT NOT NULL,

    execution_profile TEXT NOT NULL,
    paper_mode TEXT NOT NULL,

    status TEXT NOT NULL,

    config_hash TEXT,

    order_fingerprint TEXT NOT NULL,

    raw_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_orders_asset_created
ON orders (
    asset_id,
    created_at_utc
);

CREATE INDEX IF NOT EXISTS idx_orders_source_timestamp
ON orders (
    asset_id,
    source_timestamp_utc
);

CREATE TABLE IF NOT EXISTS executions (
    execution_id TEXT PRIMARY KEY,

    order_id TEXT NOT NULL,

    asset_id TEXT NOT NULL,

    side TEXT NOT NULL,

    quantity_native TEXT NOT NULL,

    reference_price_native TEXT,
    execution_price_native TEXT NOT NULL,

    bid_native TEXT,
    ask_native TEXT,

    spread_native TEXT,
    slippage_native TEXT,

    fee_native TEXT,
    fee_pln TEXT,

    provider_timestamp_utc TEXT,
    execution_timestamp_utc TEXT NOT NULL,

    data_quality TEXT,
    execution_quality TEXT,
    session_quality TEXT,

    fx_path TEXT,
    fx_rate TEXT,
    fx_provider TEXT,
    fx_timestamp_utc TEXT,
    fx_quality TEXT,

    config_hash TEXT,

    raw_json TEXT,

    FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
);

CREATE INDEX IF NOT EXISTS idx_executions_order
ON executions (
    order_id
);

CREATE INDEX IF NOT EXISTS idx_executions_asset_time
ON executions (
    asset_id,
    execution_timestamp_utc
);

CREATE TABLE IF NOT EXISTS positions (
    position_id TEXT PRIMARY KEY,

    asset_id TEXT NOT NULL,

    side TEXT NOT NULL,

    quantity_native TEXT NOT NULL,

    entry_execution_id TEXT NOT NULL,

    exit_execution_id TEXT,

    entry_price_native TEXT NOT NULL,
    exit_price_native TEXT,

    stop_loss_native TEXT,
    take_profit_native TEXT,

    status TEXT NOT NULL,

    opened_at_utc TEXT NOT NULL,
    closed_at_utc TEXT,

    short_mechanism TEXT,
    short_financing_model TEXT,

    execution_profile TEXT,
    execution_quality_at_entry TEXT,

    unrealized_pnl_native TEXT,
    unrealized_pnl_pln TEXT,

    raw_json TEXT,

    FOREIGN KEY (entry_execution_id)
        REFERENCES executions(execution_id),

    FOREIGN KEY (exit_execution_id)
        REFERENCES executions(execution_id)
);

CREATE INDEX IF NOT EXISTS idx_positions_asset_status
ON positions (
    asset_id,
    status
);

CREATE TABLE IF NOT EXISTS portfolio_transactions (
    transaction_id TEXT PRIMARY KEY,

    transaction_type TEXT NOT NULL,

    amount_pln TEXT NOT NULL,

    asset_id TEXT,

    reference_type TEXT,
    reference_id TEXT,

    booked_at_utc TEXT NOT NULL,

    fx_pair TEXT,
    fx_path TEXT,
    fx_rate TEXT,
    fx_provider TEXT,
    fx_timestamp_utc TEXT,
    fx_quality TEXT,

    raw_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_type
ON portfolio_transactions (
    transaction_type
);

CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_reference
ON portfolio_transactions (
    reference_type,
    reference_id
);

CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_time
ON portfolio_transactions (
    booked_at_utc
);

CREATE TABLE IF NOT EXISTS trades (
    trade_id TEXT PRIMARY KEY,

    asset_id TEXT NOT NULL,

    position_id TEXT NOT NULL UNIQUE,

    entry_execution_id TEXT NOT NULL,

    exit_execution_id TEXT NOT NULL,

    quantity_native TEXT NOT NULL,

    realized_pnl_native TEXT NOT NULL,
    realized_pnl_pln TEXT NOT NULL,

    fees_pln TEXT,
    spread_cost_pln TEXT,
    slippage_pln TEXT,

    realized_fx_pair TEXT,
    realized_fx_path TEXT,
    realized_fx_rate TEXT,
    realized_fx_provider TEXT,
    realized_fx_timestamp_utc TEXT,
    realized_fx_quality TEXT,

    realized_transaction_id TEXT NOT NULL UNIQUE,

    opened_at_utc TEXT NOT NULL,
    closed_at_utc TEXT NOT NULL,

    raw_json TEXT,

    FOREIGN KEY (position_id)
        REFERENCES positions(position_id),

    FOREIGN KEY (entry_execution_id)
        REFERENCES executions(execution_id),

    FOREIGN KEY (exit_execution_id)
        REFERENCES executions(execution_id),

    FOREIGN KEY (realized_transaction_id)
        REFERENCES portfolio_transactions(transaction_id)
);

CREATE INDEX IF NOT EXISTS idx_trades_asset_closed
ON trades (
    asset_id,
    closed_at_utc
);

CREATE TABLE IF NOT EXISTS equity_snapshots (
    snapshot_id TEXT PRIMARY KEY,

    captured_at_utc TEXT NOT NULL,

    cash_balance_pln TEXT NOT NULL,
    equity_pln TEXT NOT NULL,

    realized_pnl_pln TEXT,
    unrealized_pnl_pln TEXT,

    exposure_pln TEXT,

    drawdown_pln TEXT,
    drawdown_percent TEXT,

    raw_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_equity_snapshots_time
ON equity_snapshots (
    captured_at_utc
);

CREATE TABLE IF NOT EXISTS asset_equity_snapshots (
    snapshot_id TEXT PRIMARY KEY,

    asset_id TEXT NOT NULL,

    captured_at_utc TEXT NOT NULL,

    position_value_native TEXT,
    position_value_pln TEXT,

    unrealized_pnl_native TEXT,
    unrealized_pnl_pln TEXT,

    exposure_pln TEXT,

    fx_path TEXT,
    fx_rate TEXT,
    fx_provider TEXT,
    fx_timestamp_utc TEXT,
    fx_quality TEXT,

    data_quality TEXT,
    execution_quality TEXT,

    raw_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_asset_equity_asset_time
ON asset_equity_snapshots (
    asset_id,
    captured_at_utc
);

CREATE TABLE IF NOT EXISTS ai_decisions (
    decision_id TEXT PRIMARY KEY,

    asset_id TEXT NOT NULL,
    strategy_id TEXT NOT NULL,

    decision_timestamp_utc TEXT NOT NULL,

    decision_type TEXT,
    decision_payload_json TEXT NOT NULL,

    correlation_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_ai_decisions_asset_strategy_time
ON ai_decisions (
    asset_id,
    strategy_id,
    decision_timestamp_utc
);

CREATE TABLE IF NOT EXISTS system_events (
    event_id TEXT PRIMARY KEY,

    event_timestamp_utc TEXT NOT NULL,

    level TEXT NOT NULL,
    event_type TEXT NOT NULL,

    asset_id TEXT,

    correlation_id TEXT,

    payload_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_system_events_type_time
ON system_events (
    event_type,
    event_timestamp_utc
);

CREATE INDEX IF NOT EXISTS idx_system_events_asset_time
ON system_events (
    asset_id,
    event_timestamp_utc
);
