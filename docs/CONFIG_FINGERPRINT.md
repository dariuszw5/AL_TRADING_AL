# Global Configuration Fingerprint

Phase 09 A.11 adds a global configuration fingerprint without changing
the existing `PaperBroker.config_hash_for()` / `Execution.config_hash`
contract.

The global fingerprint includes:

- normalized AssetRegistry;
- asset_registry_hash;
- existing execution_config_hash;
- paper_mode;
- Phase 09 feature flags.

The AssetRegistry is sorted by canonical asset_id and serialized through
the existing asset_payload() contract before deterministic JSON hashing.

Phase 09 flags recorded in the fingerprint:

- AL_TRADING_REALISTIC_V2_ENABLED
- AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED
- AL_TRADING_FX_ENABLED
- AL_TRADING_PLN_ACCOUNTING_ENABLED

The new PLN accounting flag is fail-closed and defaults to false.

SQLite is not implemented in Phase 09, so A.11 does not invent or enable
a SQLite feature flag.

The REALISTIC_V2 deterministic benchmark records both hashes separately:

- execution_config_hash
- global_config_hash

and additionally records:

- asset_registry_hash
- paper_mode
- feature_flags
- metadata_schema

A.11 does not modify PaperBroker hash semantics, Execution persistence,
execution journal semantics, recovery/reconciliation, LEGACY_V1,
frozen strategy parameters, existing assertions, live_state, or data.

Rollback: revert the A.11 commit. No state migration is required.
