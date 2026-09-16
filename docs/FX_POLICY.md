# FX POLICY

Status: Phase 07 research/design
Date reviewed: 2026-09-16

This document defines FX source policy only.

Phase 07 does NOT:
- book PLN into the portfolio
- change execution semantics
- change LEGACY_V1
- assume USDT equals USD
- implement CurrencyConverter

## Empirical evidence

Evidence:
`docs/evidence/PHASE07_SESSION_FX_PROBE_2026-09-16.json`

Observed on 2026-09-16:

NBP Table A:
- USD/PLN: 3.7639
- EUR/PLN: 4.3435
- effective date: 2026-09-16

Yahoo:
- USDPLN=X: 3.7779
- EURPLN=X: 4.3586
- EURUSD=X: 1.1541
- exchangeDataDelayedBy: unavailable in observed responses

Coinbase Exchange:
- USDT-USD price: 0.99933
- bid: 0.99932
- ask: 0.99933

The Coinbase observation demonstrates why the system must not use
an unconditional 1 USDT = 1 USD conversion.

## Source roles

### Referential accounting

Primary reference:
NBP Table A.

Use:
- USD -> PLN reference
- EUR -> PLN reference

Quality:
DAILY_REFERENCE

NBP Table A is not an intraday/live FX feed.

For future realized-PnL accounting, the applicable NBP table and its
effective date must be stored permanently with the accounting record.

Required metadata:
- fx_provider
- fx_table
- fx_effective_date
- fx_rate
- fx_path

Historical realized values must never be silently recalculated using
a newer rate.

### MTM / presentation

Candidate source:
Yahoo chart source for:
- USDPLN=X
- EURPLN=X

Status:
UNOFFICIAL / DEGRADED_BY_DESIGN

Quality ceiling:
STALE_PRONE

Reason:
the empirical probe returned last-price data but did not provide a
reliable `exchangeDataDelayedBy` value.

A Yahoo quote must never be labelled LIVE solely because the HTTP
request succeeded.

## USDT conversion

Canonical conversion path:

USDT -> USD -> PLN

USDT -> USD:
Coinbase Exchange public USDT-USD market-data reference.

USD -> PLN:
- future realized/reference accounting: NBP Table A
- future MTM display: approved MTM USD/PLN source

Never use:
USDT = USD unconditionally.

The conversion record must preserve both legs.

Example metadata:

fx_path = "USDT->USD->PLN"
usdt_usd_provider = "coinbase_exchange"
usd_pln_provider = "nbp_table_a" or approved MTM provider

## EUR conversion

Canonical path:

EUR -> PLN

Reference accounting:
NBP Table A EUR/PLN.

MTM:
approved EUR/PLN market-data source with freshness metadata.

## FX freshness states

The future CurrencyConverter must expose:

FX_FRESH
- quote age <= configured freshness threshold

FX_STALE
- quote older than the freshness threshold
- but not older than 96 hours
- show PLN with a visible FX_STALE label
- show quote age

FX_UNAVAILABLE
- no valid conversion path
- or required FX quote age > 96 hours
- display PLN as UNAVAILABLE

The 96-hour boundary follows MASTER_SPEC.

## Weekend policy

Crypto continues trading during weekends while fiat FX normally does
not.

Therefore the system must not disable the entire crypto portfolio just
because USD/PLN is not producing a fresh weekend quote.

Policy:

1. Keep the last valid FX observation.
2. Preserve its original provider timestamp.
3. Never refresh its timestamp artificially.
4. Once older than the configured freshness threshold, classify it
   FX_STALE.
5. Keep showing MTM PLN only with the FX_STALE label and quote age.
6. At age > 96 hours classify FX_UNAVAILABLE.
7. A new fresh quote returns the path to FX_FRESH.

Weekend thresholds must be configurable separately from normal
business-day thresholds.

No numeric freshness threshold is frozen in Phase 07. It must be
measured and accepted before Phase 09 implementation.

## Conversion cost

KNOWN_LIMITATION: FX_CONVERSION_COST_NOT_MODELLED

Phase 07 does not pretend that PLN/USD/EUR conversion is costless.

A later execution/accounting phase must either model the conversion
cost or preserve this limitation explicitly.

## Source classifications

NBP Table A:
- role: reference accounting
- FX_QUALITY: DAILY_REFERENCE

Yahoo USDPLN=X / EURPLN=X:
- role: MTM research candidate
- API: UNOFFICIAL / DEGRADED_BY_DESIGN
- FX_QUALITY ceiling: STALE_PRONE

Coinbase USDT-USD:
- role: USDT/USD market reference
- empirically confirmed bid/ask/last in Phase 07

## Fail-closed rules

The converter must not:
- substitute 1.0 when a leg is missing
- silently use an expired rate
- convert with a future timestamp
- silently replace USDT with USD
- relabel DAILY_REFERENCE as LIVE
- hide the FX path from accounting metadata

## Phase boundary

Implementation of PLN accounting is Phase 09 work and remains subject
to the MASTER_SPEC HARD STOP rules.

This file is policy and research only.
