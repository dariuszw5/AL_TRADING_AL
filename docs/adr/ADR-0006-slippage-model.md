# ADR-0006 — REALISTIC_V2 slippage model

Date: 2026-09-16
Status: Proposed / accepted for design only

## Context

REALISTIC_V2 requires explicit slippage.

A stochastic model would add nondeterminism and calibration complexity
before sufficient execution evidence exists.

## Decision

Initial model:
`FixedBpsSlippage`

Properties:
- deterministic
- adverse to the trader
- configured explicitly
- included in config_hash
- applied after selecting executable bid/ask
- no profitability-driven calibration

BUY:
price increases by configured bps.

SELL:
price decreases by configured bps.

No production slippage value is frozen by this ADR.

## Consequences

Tests and benchmarks remain deterministic.

The model is intentionally simple and may later be replaced by an
evidence-based model through a separate reviewed change.
