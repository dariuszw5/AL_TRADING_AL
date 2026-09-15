"""Safe account-demo readiness configuration; it cannot submit an order."""
import os


def paper_broker_readiness(environment=None):
    env = environment or os.environ
    provider = env.get('AL_TRADING_PAPER_BROKER', 'none').lower()
    enabled = env.get('AL_TRADING_PAPER_EXECUTION', 'false').lower() == 'true'
    if provider not in {'none', 'ibkr'}:
        return {'provider': provider, 'ready': False, 'execution_enabled': False,
                'reason': 'Nieobsługiwany dostawca konta demo'}
    if provider == 'none':
        return {'provider': 'none', 'ready': False, 'execution_enabled': False,
                'reason': 'Brak skonfigurowanego konta demo'}
    # Credentials are intentionally not read here. They belong in the VM secret
    # store only after a separately reviewed adapter is implemented.
    return {'provider': 'ibkr', 'ready': False, 'execution_enabled': False,
            'requested_execution': enabled,
            'reason': 'Integracja z API IBKR nie jest jeszcze zatwierdzona; pozostaje paper-only lokalnie'}
