"""Small, failure-tolerant public-news collector for research-only use."""
import time
import requests

from src.agent.geopolitical_analyst import classify_article


class GeopoliticalFeed:
    """Reads public GDELT article metadata; no credentials or trading APIs."""
    URL = 'https://api.gdeltproject.org/api/v2/doc/doc'

    def __init__(self, ttl_seconds=900):
        self.ttl_seconds = ttl_seconds
        self._cached_at = 0.0
        self._cached = {'events': [], 'source': 'GDELT', 'issue': None}

    def fetch(self):
        if time.time() - self._cached_at < self.ttl_seconds:
            return self._cached
        try:
            response = requests.get(self.URL, params={
                'query': '(war OR sanctions OR oil OR gas OR tariff OR bank crisis)',
                'mode': 'artlist', 'format': 'json', 'maxrecords': 50, 'timespan': '1d',
            }, timeout=12, headers={'User-Agent': 'AL-Trading-Agent-Research/1.0'})
            response.raise_for_status()
            articles = response.json().get('articles', [])
            events = []
            for article in articles:
                event = classify_article(article.get('title', ''), article.get('sourcecountry', 'global'))
                if event:
                    events.append(event)
            self._cached = {'events': events[:20], 'source': 'GDELT article metadata', 'issue': None}
        except (ValueError, requests.RequestException) as error:
            # News failure must never turn into a fabricated safe-market signal.
            self._cached = {'events': [], 'source': 'GDELT article metadata', 'issue': str(error)}
        self._cached_at = time.time()
        return self._cached
