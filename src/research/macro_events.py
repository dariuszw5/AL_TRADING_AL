from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import html
import os
import re
from pathlib import Path
import xml.etree.ElementTree as ET

import requests

from src.research.event_store import DailyJsonlStore


DEFAULT_FEEDS = (
    ("FED", "https://www.federalreserve.gov/feeds/press_all.xml"),
    ("ECB", "https://www.ecb.europa.eu/rss/press.html"),
)


@dataclass(frozen=True)
class MacroEvent:
    event_id: str
    source: str
    title: str
    url: str | None
    published: str | None
    tags: tuple[str, ...]

    def as_dict(self) -> dict:
        payload = asdict(self)
        payload["tags"] = list(self.tags)
        return payload


def _text(element, names: tuple[str, ...]) -> str | None:
    for child in element.iter():
        local = child.tag.split("}")[-1].lower()
        if local in names and child.text:
            value = html.unescape(child.text).strip()
            if value:
                return value
    return None


def _classify(source: str, title: str) -> tuple[str, ...]:
    text = title.lower()
    tags = {source.lower()}
    rules = {
        "rates": ("rate", "rates", "stóp", "interest", "monetary policy"),
        "inflation": ("inflation", "cpi", "pce", "prices"),
        "employment": ("employment", "jobs", "labor", "labour", "unemployment"),
        "growth": ("gdp", "growth", "activity", "recession"),
        "liquidity": ("liquidity", "balance sheet", "asset purchases", "qt", "qe"),
        "banking": ("bank", "financial stability", "stress"),
    }
    for tag, needles in rules.items():
        if any(needle in text for needle in needles):
            tags.add(tag)
    return tuple(sorted(tags))


class MacroEventCollector:
    def __init__(self, data_dir: str | Path, timeout_seconds: float = 8.0):
        self.data_dir = Path(data_dir)
        self.timeout_seconds = float(timeout_seconds)
        self.store = DailyJsonlStore(self.data_dir / "logs", "macro_events", 90)
        raw_feeds = os.getenv("AL_TRADING_MACRO_FEEDS", "").strip()
        if raw_feeds:
            feeds = []
            for item in raw_feeds.split(","):
                if "=" not in item:
                    continue
                source, url = item.split("=", 1)
                if source.strip() and url.strip():
                    feeds.append((source.strip().upper(), url.strip()))
            self.feeds = tuple(feeds) or DEFAULT_FEEDS
        else:
            self.feeds = DEFAULT_FEEDS

    def collect(self) -> list[dict]:
        seen = {event.get("event_id") for event in self.store.read_recent(limit=3000, days=90)}
        new_events: list[dict] = []
        for source, url in self.feeds:
            try:
                response = requests.get(
                    url,
                    timeout=self.timeout_seconds,
                    headers={"User-Agent": "AL-Trading-Agent-Research/1.0"},
                )
                response.raise_for_status()
                root = ET.fromstring(response.content)
            except Exception as exc:
                self.store.append({
                    "event_type": "MACRO_PROVIDER_ERROR",
                    "source": source,
                    "url": url,
                    "error": f"{type(exc).__name__}: {exc}",
                })
                continue

            entries = [node for node in root.iter()
                       if node.tag.split("}")[-1].lower() in {"item", "entry"}]
            for entry in entries[:50]:
                title = _text(entry, ("title",))
                if not title:
                    continue
                link = _text(entry, ("link", "id"))
                if link is None:
                    for child in entry.iter():
                        if child.tag.split("}")[-1].lower() == "link":
                            link = child.attrib.get("href")
                            if link:
                                break
                published = _text(entry, ("pubdate", "published", "updated", "date"))
                event_id = hashlib.sha256(
                    f"{source}|{title}|{link or ''}|{published or ''}".encode("utf-8")
                ).hexdigest()[:24]
                if event_id in seen:
                    continue
                event = MacroEvent(
                    event_id=event_id,
                    source=source,
                    title=re.sub(r"\s+", " ", title),
                    url=link,
                    published=published,
                    tags=_classify(source, title),
                ).as_dict()
                event["event_type"] = "MACRO_EVENT"
                new_events.append(event)
                seen.add(event_id)

        if new_events:
            self.store.append_many(new_events)
        return new_events

    def recent(self, limit: int = 50) -> list[dict]:
        return [row for row in self.store.read_recent(limit=limit * 3, days=30)
                if row.get("event_type") == "MACRO_EVENT"][-limit:]

    def recent_tags(self, limit: int = 30) -> list[str]:
        tags: set[str] = set()
        for event in self.recent(limit=limit):
            tags.update(str(tag) for tag in event.get("tags", []))
        return sorted(tags)
