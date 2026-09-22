"""Minimal Jev client over the OpenRouter passthrough.

Stdlib only, so this runs with no virtualenv and no installed dependencies.
If we later add the official typesafe-sdk, that's the point to create `.env`.
"""
from __future__ import annotations

import json
import pathlib
import time
import urllib.error
import urllib.request
from typing import Any

ENDPOINT = "https://openrouter.ai/api/alpha/decisions"
MODEL = "~typesafe/jev-latest"
_KEY_FILE = pathlib.Path(__file__).resolve().parents[2] / "apikey.openrouter.txt"

_RETRYABLE = {429, 500, 502, 503, 529}


def _key() -> str:
    return _KEY_FILE.read_text().strip()


class Jev:
    """Tracks cumulative cost and request count across a session."""

    def __init__(self) -> None:
        self.cost = 0.0
        self.requests = 0
        self.model_seen: str | None = None

    def ask(self, state: Any, questions: dict[str, dict], attempts: int = 4) -> dict:
        payload = json.dumps({"model": MODEL, "state": state, "questions": questions}).encode()
        req = urllib.request.Request(
            ENDPOINT,
            data=payload,
            headers={"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"},
        )
        last: Exception | None = None
        for i in range(attempts):
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    data = json.load(resp)
                break
            except urllib.error.HTTPError as e:
                last = e
                if e.code not in _RETRYABLE or i == attempts - 1:
                    raise
                time.sleep(2**i)
            except urllib.error.URLError as e:
                last = e
                if i == attempts - 1:
                    raise
                time.sleep(2**i)
        else:  # pragma: no cover
            raise RuntimeError(f"request failed: {last}")

        self.requests += 1
        self.cost += data.get("usage", {}).get("cost", 0.0)
        self.model_seen = data.get("model", self.model_seen)
        return data

    # -- convenience wrappers -------------------------------------------------

    def choice(self, state: Any, question: str, options: list[str], focus: str | None = None) -> dict:
        instr: Any = {"question": question, "focus": focus} if focus else question
        r = self.ask(state, {"q": {
            "type": "choice",
            "instructions": instr,
            "criteria": {o: None for o in options},
        }})
        return r["answers"]["q"]

    def nouls(self, state: Any, claims: dict[str, str]) -> dict[str, float]:
        """Many yes/no claims in ONE parallel request."""
        r = self.ask(state, {
            k: {"type": "noul", "instructions": v} for k, v in claims.items()
        })
        return {k: r["answers"][k]["noul"] for k in claims}

    def score(self, state: Any, question: str, levels: list[str]) -> dict:
        r = self.ask(state, {"q": {
            "type": "score", "instructions": question, "criteria": levels,
        }})
        return r["answers"]["q"]
