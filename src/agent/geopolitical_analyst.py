"""Historical geopolitical analogue model for research-only market filtering.

It is deliberately an explainable nearest-neighbour model.  A news item is
mapped to a small event vector and compared with dated historical scenarios.
The output is a risk assessment, never an order instruction or price target.
"""
from collections import defaultdict
from datetime import datetime, timezone
import math
import re


# Curated benchmark of widely documented shocks.  Values are qualitative
# realised stress labels (0..1), not reconstructed prices or trading returns.
# New observations can be appended after an offline historical review.
HISTORICAL_SCENARIOS = (
    {'id': 'crimea-2014', 'date': '2014-03-01', 'tags': {'conflict', 'sanctions'},
     'regions': {'europe', 'russia'}, 'severity': 0.75,
     'stress': {'energy': .72, 'metal': .55, 'forex': .50, 'stock': .45, 'crypto': .20}},
    {'id': 'brexit-2016', 'date': '2016-06-23', 'tags': {'trade', 'election'},
     'regions': {'europe', 'uk'}, 'severity': 0.65,
     'stress': {'forex': .82, 'stock': .50, 'index': .55, 'metal': .35}},
    {'id': 'trade-war-2018', 'date': '2018-03-22', 'tags': {'trade', 'sanctions'},
     'regions': {'us', 'china'}, 'severity': 0.60,
     'stress': {'stock': .60, 'index': .65, 'agriculture': .72, 'metal': .45}},
    {'id': 'covid-2020', 'date': '2020-03-11', 'tags': {'pandemic', 'supply_chain'},
     'regions': {'global'}, 'severity': 1.0,
     'stress': {'stock': .95, 'index': .95, 'energy': .95, 'forex': .62, 'crypto': .82, 'metal': .58}},
    {'id': 'oil-shock-2020', 'date': '2020-04-20', 'tags': {'energy_supply', 'supply_chain'},
     'regions': {'global'}, 'severity': .92,
     'stress': {'energy': .98, 'stock': .52, 'forex': .35, 'metal': .35}},
    {'id': 'ukraine-2022', 'date': '2022-02-24', 'tags': {'conflict', 'sanctions', 'energy_supply'},
     'regions': {'europe', 'russia'}, 'severity': .95,
     'stress': {'energy': .92, 'agriculture': .90, 'metal': .72, 'forex': .62, 'stock': .58, 'index': .60, 'crypto': .50}},
    {'id': 'bank-stress-2023', 'date': '2023-03-10', 'tags': {'financial_stress', 'monetary'},
     'regions': {'us', 'europe'}, 'severity': .72,
     'stress': {'stock': .70, 'index': .72, 'forex': .42, 'crypto': .56, 'metal': .48}},
    {'id': 'red-sea-2023', 'date': '2023-12-18', 'tags': {'conflict', 'supply_chain', 'energy_supply'},
     'regions': {'middle_east', 'global'}, 'severity': .62,
     'stress': {'energy': .70, 'agriculture': .40, 'forex': .30, 'stock': .32}},
)


KEYWORDS = {
    'conflict': ('war', 'attack', 'missile', 'military', 'invasion', 'conflict', 'wojna', 'atak'),
    'sanctions': ('sanction', 'embargo', 'tariff', 'cło', 'sankcj'),
    'energy_supply': ('oil', 'gas', 'energy', 'pipeline', 'ropa', 'gaz'),
    'supply_chain': ('shipping', 'port', 'supply chain', 'transport', 'canal', 'łańcuch dostaw'),
    'financial_stress': ('bank', 'default', 'liquidity', 'debt crisis', 'bankruct'),
    'monetary': ('interest rate', 'central bank', 'inflation', 'stopy procentowe', 'inflacja'),
    'trade': ('trade', 'export', 'import', 'trade deal', 'handel'),
    'election': ('election', 'vote', 'referendum', 'wybory'),
    'pandemic': ('pandemic', 'covid', 'epidemic', 'pandemia'),
}


def classify_article(title, region='global'):
    """Create a reproducible event feature record from one news headline."""
    text = title.lower()
    tags = {
        tag for tag, terms in KEYWORDS.items()
        if any(re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text) for term in terms)
    }
    if not tags:
        return None
    severity = min(1.0, .25 + .14 * len(tags) + (.25 if 'conflict' in tags else 0))
    return {'title': title, 'tags': tags, 'regions': {region or 'global'}, 'severity': severity}


class GeopoliticalAnalyst:
    def __init__(self, scenarios=HISTORICAL_SCENARIOS):
        self.scenarios = tuple(scenarios)

    @staticmethod
    def _similarity(event, scenario):
        tags = event['tags']
        scenario_tags = scenario['tags']
        union = tags | scenario_tags
        tag_score = len(tags & scenario_tags) / len(union) if union else 0.0
        region_score = .25 if event['regions'] & scenario['regions'] else 0.0
        severity_score = max(0.0, 1 - abs(event['severity'] - scenario['severity'])) * .25
        return round(.5 * tag_score + region_score + severity_score, 4)

    def assess(self, events, asset_types):
        """Return weighted historical stress by asset class with audit details."""
        impacts = defaultdict(float)
        explanations = defaultdict(list)
        accepted = []
        for event in events:
            if not event or not event.get('tags'):
                continue
            normal = {**event, 'tags': set(event['tags']), 'regions': set(event.get('regions', {'global'}))}
            matches = sorted(
                ((self._similarity(normal, scenario), scenario) for scenario in self.scenarios),
                key=lambda pair: pair[0], reverse=True,
            )[:3]
            matches = [(similarity, scenario) for similarity, scenario in matches if similarity >= .25]
            if not matches:
                continue
            accepted.append({'title': normal.get('title', ''), 'tags': sorted(normal['tags']),
                             'severity': normal['severity'],
                             'matches': [{'id': s['id'], 'similarity': score} for score, s in matches]})
            for asset_type in asset_types:
                score = sum(similarity * scenario['stress'].get(asset_type, 0)
                            for similarity, scenario in matches) / sum(score for score, _ in matches)
                impacts[asset_type] = max(impacts[asset_type], round(score * normal['severity'], 3))
                explanations[asset_type].append(matches[0][1]['id'])
        risk = {}
        for asset_type in asset_types:
            score = impacts[asset_type]
            level = 'CRITICAL' if score >= .65 else 'ELEVATED' if score >= .42 else 'NORMAL'
            risk[asset_type] = {
                'score': score, 'level': level, 'allow_new_entries': level == 'NORMAL',
                'historical_analogues': sorted(set(explanations[asset_type])),
            }
        return {
            'mode': 'RESEARCH_ONLY',
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'events_considered': accepted,
            'asset_risk': risk,
            'note': 'Ocena analogii historycznych; nie jest prognozą ceny ani poleceniem transakcji.',
        }
