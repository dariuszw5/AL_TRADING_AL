from src.agent.probability_calibration import calibration_report
from src.broker.paper_readiness import paper_broker_readiness


def test_calibration_groups_forecasts_without_tuning_a_model():
    report = calibration_report([
        {'confidence_probability': .8, 'profit': 2},
        {'confidence_probability': .8, 'profit': -1},
        {'confidence_probability': .6, 'profit': 1},
        {'confidence_probability': None, 'profit': 100},
    ])
    assert report['closed_forecasts'] == 3
    assert report['brier_score'] is not None
    assert report['ready'] is False


def test_broker_readiness_cannot_enable_execution():
    result = paper_broker_readiness({
        'AL_TRADING_PAPER_BROKER': 'ibkr',
        'AL_TRADING_PAPER_EXECUTION': 'true',
    })
    assert result['provider'] == 'ibkr'
    assert result['execution_enabled'] is False
