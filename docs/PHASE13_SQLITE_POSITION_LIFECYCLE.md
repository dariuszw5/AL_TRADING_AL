# PHASE 13 A.13 — SQLITE POSITION LIFECYCLE CONTRACT

The existing save_position_idempotent method remains insert-only.

A.13 adds a separate close_position_idempotent(payload) operation for the
single lifecycle transition OPEN -> CLOSED.

The close operation requires an existing OPEN position, a persisted exit
execution for the same asset, preserved immutable entry identity, and
explicit exit price / exit execution / close timestamp.

Exact replay is idempotent. Conflicting replay fails closed. The method
requires atomic_cycle and rollback restores the OPEN row.

This phase was tested on temporary SQLite databases only.

data/live/trading.db was not modified.
HALT was not cleared.
Runtime SQLite wiring was not performed.
Trading was not activated.

Next: A.14 temporary open/close/financial/restart integration.
