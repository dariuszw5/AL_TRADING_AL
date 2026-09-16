# ADR-0004 — USDT conversion path

Date: 2026-09-16
Status: Accepted for design

## Context

Crypto assets in the current project are quoted in USDT.

USDT can deviate from USD.

The Phase 07 empirical probe observed:
- USDT-USD price 0.99933
- bid 0.99932
- ask 0.99933

Therefore a permanent 1 USDT = 1 USD assumption would be incorrect.

## Decision

Canonical path:

USDT -> USD -> PLN

USDT/USD:
real market-data leg.

USD/PLN:
- NBP reference for future reference accounting
- approved MTM source for future market-value display

Store both legs and the complete path.

## Consequences

A USDT depeg affects PLN valuation instead of being hidden.

If either required conversion leg is unavailable, the system must
degrade FX quality rather than substitute 1.0.
