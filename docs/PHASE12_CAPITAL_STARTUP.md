# Phase 12 A.5 — Capital Feature Flag and Startup Fingerprint

HARD STOP 12A requires the new capital-admission semantics to remain
fail-closed behind:

`AL_TRADING_CAPITAL_ADMISSION_ENABLED`

and requires Phase 12 to have its own auditable startup fingerprint without
changing `PaperBroker.config_hash_for()` or Phase 10 startup metadata format.

A.5 implements only those controls. It still does not wire capital admission
into the execution runtime.

## Feature flag

`CapitalAdmissionFeatureFlags.from_env()` defaults to disabled.

Accepted true values: `1`, `true`, `yes`, `on`.

Accepted false values: empty string, `0`, `false`, `no`, `off`.

Unknown values fail closed.

## Phase 12 startup schema

A.5 introduces:

`phase12-capital-admission-v1`

The Phase 12 metadata preserves the execution config hash, Phase 10 global
config hash, asset-registry hash, paper mode, Phase 10 flags, Phase 10 runtime
policy and Phase 10 limitations.

It adds a separate Phase 12 hash over the Phase 10 global config hash, the new
capital-admission flag and the approved capital policy. The Phase 10 metadata
object and file format are not mutated.

## Fingerprinted capital policy

The policy records:

- controlled asset `BTCUSDT`,
- capital source `PHASE11_SETTLED_CASH_PLN`,
- exact capital-limit formula,
- `max_exposure_percent` resolved from the asset registry,
- gross entry exposure in PLN,
- REAL_BOOK ASK plus the existing slippage model,
- explicit `USDT->USD->PLN`,
- required FX freshness `FX_FRESH`,
- `ENTRY_FEE_SETTLED_AT_REALIZATION`,
- OPEN does not mutate settled cash,
- EXIT is not blocked by capital admission,
- no margin, collateral, leverage or new short-financing semantics.

A.5 does not modify runtime execution behavior or persist a new startup file.
