# ADR-0007 — Synthetic shorts

Date: 2026-09-16
Status: Proposed / accepted for design only

## Context

The historical strategy can emit SELL with no long position.

A spot reference price does not imply real short-selling capability.

BTC spot requires another mechanism such as margin/futures.

Equity shorts require borrow availability and financing.

## Decision

REALISTIC_V2 always consults AssetConfig.

If:
`allow_short == False`

then:
`REJECTED / SHORT_NOT_SUPPORTED`

Synthetic shorts:

realistic_paper:
- rejected

research_paper:
- may be permitted when AssetConfig explicitly selects SYNTHETIC
- mandatory labels:
  - SYNTHETIC_SHORT
  - FINANCING_NOT_MODELLED

No automatic fallback to synthetic short is permitted.

LEGACY_V1 historical SELL semantics remain unchanged for regression.

## Consequences

Paper results no longer silently describe synthetic spot shorts as
real-market executions.

This is an execution-semantics decision and therefore requires the
Phase 08 HARD STOP before implementation.
