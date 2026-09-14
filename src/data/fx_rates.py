"""Public indicative conversion rates; no authentication or order endpoints."""
import math
import time
import requests


def fetch_pln_rates(currencies):
    response = requests.get('https://api.coinbase.com/v2/exchange-rates',
                            params={'currency': 'USD'}, timeout=15)
    response.raise_for_status()
    data = response.json()['data']
    if data['currency'] != 'USD':
        raise ValueError('Unexpected FX base currency')
    raw = data['rates']
    pln = float(raw['PLN'])
    rates = {'PLN': 1.0}
    for currency in set(currencies) - {'PLN'}:
        denominator = 1.0 if currency == 'USD' else float(raw[currency])
        if not math.isfinite(denominator) or denominator <= 0:
            raise ValueError(f'Invalid FX rate: {currency}')
        rate = pln / denominator
        if not math.isfinite(rate) or rate <= 0:
            raise ValueError(f'Invalid PLN rate: {currency}')
        rates[currency] = rate
    return {'rates': rates, 'received_at': int(time.time() * 1000),
            'source': 'Coinbase indicative exchange rates', 'currency': 'PLN'}
