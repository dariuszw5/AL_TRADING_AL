from __future__ import annotations

import os
import threading

import uvicorn

from src.research.autonomous_agent import AutonomousResearchAgent


def main():
    agent = AutonomousResearchAgent()
    thread = threading.Thread(
        target=agent.run_forever,
        name="autonomous-research-paper",
        daemon=True,
    )
    thread.start()

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "app.backend.main:app",
        host="0.0.0.0",
        port=port,
        log_level=os.getenv("LOG_LEVEL", "info"),
        proxy_headers=True,
    )


if __name__ == "__main__":
    main()
