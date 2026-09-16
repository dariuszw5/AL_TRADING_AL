# ADR-0005 — Execution profiles

Date: 2026-09-16
Status: Proposed / accepted for design only

## Context

The frozen historical engine and a realistic paper engine cannot share
identical fill semantics.

Bid/ask, spread, slippage and STOP_GAP necessarily change outcomes.

## Decision

Maintain two explicit profiles.

LEGACY_V1:
- frozen backtest/regression semantics
- no paper-live
- no semantic changes

REALISTIC_V2:
- separate broker path
- executable bid/ask side
- spread
- slippage
- market sessions
- STOP_GAP
- EXIT_PENDING
- data-quality rejection

Every benchmark records the execution profile.

REALISTIC_V2 gets a separate benchmark and config_hash.

## Consequences

A difference between LEGACY_V1 and REALISTIC_V2 is expected and is
reported rather than optimized away.

Implementation requires explicit HARD STOP approval.
