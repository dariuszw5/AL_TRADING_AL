from src.agent.geopolitical_analyst import GeopoliticalAnalyst, classify_article


def test_historical_analogues_raise_energy_and_agriculture_risk():
    analyst = GeopoliticalAnalyst()
    event = {
        'title': 'Pipeline attack disrupts oil and grain shipping',
        'tags': {'conflict', 'energy_supply', 'supply_chain'},
        'regions': {'europe'},
        'severity': .9,
    }
    result = analyst.assess([event], {'energy', 'agriculture', 'crypto'})
    assert result['asset_risk']['energy']['level'] in {'ELEVATED', 'CRITICAL'}
    assert result['asset_risk']['agriculture']['allow_new_entries'] is False
    assert 'ukraine-2022' in result['asset_risk']['energy']['historical_analogues']


def test_unrelated_headline_is_not_converted_to_a_market_signal():
    assert classify_article('Local sports team wins a match') is None


def test_assessment_is_research_only_and_explainable():
    result = GeopoliticalAnalyst().assess([], {'stock'})
    assert result['mode'] == 'RESEARCH_ONLY'
    assert result['asset_risk']['stock']['level'] == 'NORMAL'
    assert result['asset_risk']['stock']['allow_new_entries'] is True
