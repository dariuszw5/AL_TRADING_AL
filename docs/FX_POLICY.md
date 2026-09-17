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
- PLN=X (canonical project symbol for USD/PLN)
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
- quote age < configured freshness threshold

FX_STALE
- quote age >= configured freshness threshold
- but not older than 96 hours
- show PLN with a visible FX_STALE label
- show quote age

FX_UNAVAILABLE
- no valid conversion path
- or required FX quote age > 96 hours
- display PLN as UNAVAILABLE

The 96-hour boundary follows MASTER_SPEC.

At exactly 96 hours the quote remains `FX_STALE`; only age strictly greater than 96 hours is `FX_UNAVAILABLE`.

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

Yahoo PLN=X / EURPLN=X:
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

## Phase 09 A.4 provider implementation

The FX provider layer now contains three isolated adapters.

### NBP Table A

Implemented for:

- USD/PLN
- EUR/PLN

Classification:

`DAILY_REFERENCE`

The adapter preserves:

- NBP table number,
- effective date,
- rate,
- provider identity.

Important limitation:

The NBP response used by this project does not expose a reliable
intraday publication timestamp.

Therefore the adapter deliberately stores:

`provider_timestamp = None`

and labels the quote:

- `REFERENCE_ACCOUNTING_ONLY`
- `PUBLICATION_TIMESTAMP_UNAVAILABLE`

The system must not invent a publication time or use this
DAILY_REFERENCE as ordinary fresh intraday MTM.

### Yahoo PLN FX

Implemented candidates:

- `PLN=X` for USD/PLN,
- `EURPLN=X` for EUR/PLN.

Classification ceiling:

`STALE_PRONE`

Permanent labels include:

- `UNOFFICIAL`
- `DEGRADED_BY_DESIGN`

A successful request or `exchangeDataDelayedBy=0` does not upgrade
Yahoo to `LIVE`.

Provider timestamp comes from `regularMarketTime` when available.
If it is missing, the quote remains timestamp-unavailable and the
freshness layer fails closed.

### Coinbase USDT/USD

Implemented from public `USDT-USD` level-1 book data.

The provider preserves:

- bid,
- ask,
- provider timestamp,
- provider identity.

Reference conversion rate:

`(bid + ask) / 2`

The midpoint is a reporting/reference rate only. It is not a claim
that real FX conversion executes without cost.

`KNOWN_LIMITATION: FX_CONVERSION_COST_NOT_MODELLED`

### Deterministic testing

Provider tests use repository JSON fixtures and injected HTTP clients.

Offline tests perform zero network access.

The default live adapters use only Python standard-library HTTP
facilities and add no dependency.

### Phase boundary

A.4 still does not:

- book realized PLN,
- update cash PLN,
- modify REALISTIC_V2 runtime,
- modify LEGACY_V1,
- migrate persistence,
- introduce SQLite.

## Phase 09 A.6 realized source selection

Realized FX evidence selection is deterministic and fail-closed.

### NBP DAILY_REFERENCE

The verified NBP Table A response used by this project does not expose
a reliable intraday publication timestamp.

Therefore the selector never invents such a timestamp.

For a daily reference:

- effective_date after the trade-close date is never eligible,
- a same-day table is eligible only when the system actually observed
  that table no later than the trade close,
- a table with an earlier effective_date may be used as the known
  prior daily reference,
- among eligible references the latest effective_date is selected,
- ambiguity on the selected effective_date fails closed.

This avoids retroactively using a same-day NBP table that the system
first learned about after the transaction had already closed.

It also avoids pretending that effective_date is an intraday
publication timestamp.

The maximum permitted age of a daily reference remains configurable.
A.6 does not freeze the production threshold.

### Timestamped market FX legs

For timestamped market evidence, including Coinbase USDT/USD:

    provider_timestamp <= closed_at

The newest eligible quote is selected.

A quote newer than the transaction close is never used.

The maximum market quote age remains configurable.
A.6 does not freeze the production threshold.

### Canonical realized paths

    PLN
    USD -> PLN
    EUR -> PLN
    USDT -> USD -> PLN

The complete evidence selected here is passed to the immutable
RealizedFxBooker introduced in Phase 09 A.5.

### Accounting interpretation

NBP remains DAILY_REFERENCE.

A prior-day NBP middle rate is not described as an executable FX rate
at the exact trade-close instant.

If a same-day table was actually observed before the trade close, its
use is auditable through observed_at.

No synthetic NBP publication timestamp is created.

KNOWN_LIMITATION: FX_CONVERSION_COST_NOT_MODELLED

### Phase boundary

A.6 does not:

- update paper cash,
- update equity PLN,
- create a financial ledger,
- modify PaperBroker,
- modify REALISTIC_V2 runtime,
- modify LEGACY_V1,
- change frozen strategy parameters,
- migrate JSON state,
- introduce SQLite,
- add a dependency.

## Phase 09 A.12 accepted production freshness policy

The read-only empirical probe on 2026-09-17 observed:

- Yahoo `PLN=X`: current quote available,
- Yahoo `USDPLN=X`: same observed USD/PLN value as `PLN=X`,
- Yahoo `EURPLN=X`: current quote available,
- median observed Yahoo chart cadence: 1 hour,
- observed weekend Yahoo gap: 49 hours,
- `exchangeDataDelayedBy`: unavailable/None,
- Coinbase USDT-USD bid/ask available,
- NBP Table A USD/PLN and EUR/PLN available.

Project canonical Yahoo symbol for USD/PLN is:

`PLN=X`

`USDPLN=X` was empirically observed to resolve to the same USD/PLN
value on 2026-09-17, but it is not the canonical project symbol.

Accepted production freshness defaults:

- weekday `max_fx_age`: 2 hours,
- weekend `max_fx_age`: 2 hours,
- hard unavailable boundary: strictly greater than 96 hours.

The measured normal Yahoo cadence is one hour. A two-hour threshold
allows one missed hourly update while still detecting a genuinely stale
feed quickly.

The weekend policy does not make a Friday quote fresh for the whole
weekend. Once the quote reaches two hours of age it becomes `FX_STALE`;
indicative PLN MTM may remain visible with stale label and age until the
existing 96-hour hard-unavailable boundary.

Weekday and weekend thresholds remain separately configurable even
though their accepted defaults are currently equal.

### Future timestamps

The strict rule remains unchanged:

- any `provider_timestamp > now` is `FX_UNAVAILABLE`,
- reason: `FUTURE_FX_TIMESTAMP`.

The A.12 probe printed Coinbase provider clock age around `-1.4s`, but
the probe captured its `NOW` value before the sequential network
requests. That observation therefore does not prove provider clock skew
and is not evidence for adding a future-timestamp tolerance.

No clock-skew grace is introduced in A.12.
