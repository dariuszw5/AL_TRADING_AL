"""Independent paper AI portfolios; no shared funds or user-ledger writes."""
from pathlib import Path
from src.agent.ai_manager import AIPaperManager, MINUTE, STOP, TAKE, FEE, SLIPPAGE
from src.data.assets import SUPPORTED_ASSETS


class AssetPaperManager(AIPaperManager):
    def _sweep_surplus(self, now_ms):
        # These separate simulation accounts never credit the shared PLN ledger.
        pass

    def _step(self, raw_markets, now_ms, errors=None):
        previous_cycle = self.state['last_cycle']
        state = super()._step(raw_markets, now_ms, errors)
        if now_ms > previous_cycle:
            state['equity_curve'] = (state.get('equity_curve', [1000.0]) + [state['equity']])[-10000:]
            bars = raw_markets.get(self.assets[0].symbol, [])
            closed = [bar for bar in bars if bar.timestamp + MINUTE <= now_ms]
            if closed:
                state['market_price'] = closed[-1].close
        return state


class IndependentPaperPortfolios:
    def __init__(self, directory='data/live_state', assets=SUPPORTED_ASSETS):
        self.managers = {
            asset.symbol: AssetPaperManager(Path(directory) / f'ai_asset_{asset.symbol}.json', assets=[asset])
            for asset in assets
        }

    def run_once(self):
        results = {}
        for symbol, manager in self.managers.items():
            try:
                results[symbol] = manager.run_once()['decision']
            except Exception as exc:
                results[symbol] = {'action': 'ERROR', 'reason': str(exc)}
        return results


def dashboard_state(state):
    """Adapt independent AI data to the existing per-market dashboard contract."""
    def position(p):
        quantity = p['allocation'] / (p['entry'] * (1 + SLIPPAGE) * (1 + FEE))
        return dict(side='BUY', entry_price=p['entry'], quantity=quantity,
                    stop_loss=p['entry'] * (1 - STOP), take_profit=p['entry'] * (1 + TAKE),
                    entry_timestamp=p['entry_timestamp'])

    trades = []
    for trade in state.get('trades', []):
        row = position(trade)
        gross = (trade['exit_price'] - trade['entry']) * row['quantity']
        row.update(exit_price=trade['exit_price'], exit_timestamp=trade['exit_timestamp'],
                   exit_reason=trade['reason'], profit=trade['profit'],
                   gross_profit=gross, fee=gross-trade['profit'])
        trades.append(row)
    p = state.get('position')
    return dict(available=True, version=state['version'], source='INDEPENDENT_AI_PAPER',
                last_processed_timestamp=state['last_cycle'], balance=state['balance'],
                peak_balance=state['peak'], market_price=state.get('market_price', 0),
                position=position(p) if p else None,
                position_candles=(p['last_timestamp']-p['entry_timestamp'])//MINUTE+1 if p else 0,
                risk_guard={'daily_loss': state['daily_loss']},
                equity_curve=state.get('equity_curve', [1000.0]), trade_manager_history=trades)
