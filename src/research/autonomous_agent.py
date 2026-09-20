from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import threading
import time

from src.agent.ai_manager import AIPaperManager
from src.agent.live_state_store import LiveStateStore
from src.data.assets import RESEARCH_ASSETS, SUPPORTED_ASSETS, get_asset
from src.research.event_store import DailyJsonlStore
from src.research.macro_events import MacroEventCollector
from src.research.market_scanner import OpportunityScanner


class AutonomousResearchAgent:
    """24/7 real-data research plus virtual paper trading."""

    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = Path(
            data_dir or os.getenv("AL_TRADING_DATA_DIR", "data/live_state")
        )
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_store = LiveStateStore(self.data_dir / "research_state.json")
        self.system_log = DailyJsonlStore(self.data_dir / "logs", "system_events", 30)
        self.macro = MacroEventCollector(self.data_dir)
        self.scanner = OpportunityScanner(self.data_dir)
        self.ai = AIPaperManager(self.data_dir / "ai_paper.json", assets=[])
        self.scan_interval = max(60, int(os.getenv("AL_TRADING_SCAN_SECONDS", "600")))
        self.macro_interval = max(60, int(os.getenv("AL_TRADING_MACRO_SECONDS", "600")))
        self.paper_interval = max(30, int(os.getenv("AL_TRADING_PAPER_SECONDS", "60")))
        self._next_scan = 0.0
        self._next_macro = 0.0
        self._next_paper = 0.0
        self._opportunities: list[dict] = []
        self._last_scan: dict | None = None
        self._last_macro_error: str | None = None
        self._last_scan_error: str | None = None
        self._last_paper_error: str | None = None
        self._stop = threading.Event()

    def _asset_specs(self, opportunities: list[dict]):
        """All curated app markets plus dynamic research opportunities."""
        assets = []
        seen = set()

        for asset in (*SUPPORTED_ASSETS, *RESEARCH_ASSETS):
            if asset.symbol in seen:
                continue
            assets.append(asset)
            seen.add(asset.symbol)

        for row in opportunities:
            symbol = str(row.get("symbol", "")).strip()
            if not symbol or symbol in seen:
                continue
            try:
                asset = get_asset(symbol, allow_dynamic_binance=True)
            except ValueError:
                continue
            assets.append(asset)
            seen.add(asset.symbol)

        return tuple(assets)

    def _persist_state(self, ai_state: dict | None = None) -> dict:
        now = datetime.now(timezone.utc)
        scan = self._last_scan or {}
        state = {
            "version": 1,
            "mode": "AUTONOMOUS_RESEARCH_PAPER",
            "paper_only": True,
            "real_orders": False,
            "updated_at": now.isoformat(),
            "updated_at_unix": now.timestamp(),
            "top_n": len(self._opportunities),
            "opportunities": self._opportunities,
            "universe_count": scan.get("universe_count", 0),
            "crypto_universe_count": scan.get("crypto_universe_count", 0),
            "connected_non_crypto_count": scan.get("connected_non_crypto_count", 0),
            "preselected_count": scan.get("preselected_count", 0),
            "available_by_class": scan.get("available_by_class", {}),
            "selected_by_class": scan.get("selected_by_class", {}),
            "selection_policy": scan.get("selection_policy", {}),
            "macro_events": self.macro.recent(limit=30),
            "ai": ai_state or self.ai.state,
            "errors": {
                "scanner": self._last_scan_error,
                "macro": self._last_macro_error,
                "paper": self._last_paper_error,
            },
            "schedules": {
                "scan_seconds": self.scan_interval,
                "macro_seconds": self.macro_interval,
                "paper_seconds": self.paper_interval,
            },
        }
        self.state_store.save(state)
        return state

    def run_once(self) -> dict:
        now = time.time()
        ai_state = self.ai.state

        if now >= self._next_macro:
            try:
                self.macro.collect()
                self._last_macro_error = None
            except Exception as exc:
                self._last_macro_error = f"{type(exc).__name__}: {exc}"
                self.system_log.append({
                    "event_type": "MACRO_COLLECTION_FAILED",
                    "error": self._last_macro_error,
                })
            self._next_macro = now + self.macro_interval

        if now >= self._next_scan:
            try:
                self._last_scan = self.scanner.scan(self.macro.recent_tags())
                self._opportunities = list(self._last_scan.get("opportunities", []))
                self.ai.assets = self._asset_specs(self._opportunities)
                self._last_scan_error = None
                self.system_log.append({
                    "event_type": "OPPORTUNITY_SCAN",
                    "universe_count": self._last_scan.get("universe_count", 0),
                    "selected": [row.get("symbol") for row in self._opportunities],
                    "selected_by_class": self._last_scan.get("selected_by_class", {}),
                })
            except Exception as exc:
                self._last_scan_error = f"{type(exc).__name__}: {exc}"
                self.system_log.append({
                    "event_type": "OPPORTUNITY_SCAN_FAILED",
                    "error": self._last_scan_error,
                })
            self._next_scan = now + self.scan_interval

        if now >= self._next_paper:
            if self.ai.assets:
                try:
                    ai_state = self.ai.run_once()
                    self._last_paper_error = None
                except Exception as exc:
                    self._last_paper_error = f"{type(exc).__name__}: {exc}"
                    self.system_log.append({
                        "event_type": "AI_PAPER_CYCLE_FAILED",
                        "error": self._last_paper_error,
                    })
            self._next_paper = now + self.paper_interval

        return self._persist_state(ai_state)

    def run_forever(self) -> None:
        self.system_log.append({
            "event_type": "AUTONOMOUS_AGENT_STARTED",
            "paper_only": True,
            "real_orders": False,
        })
        while not self._stop.is_set():
            started = time.monotonic()
            try:
                self.run_once()
            except Exception as exc:
                self.system_log.append({
                    "event_type": "AUTONOMOUS_AGENT_LOOP_ERROR",
                    "error": f"{type(exc).__name__}: {exc}",
                })
            elapsed = time.monotonic() - started
            self._stop.wait(max(1.0, min(10.0, 10.0 - elapsed)))
        self.system_log.append({"event_type": "AUTONOMOUS_AGENT_STOPPED"})

    def stop(self) -> None:
        self._stop.set()
