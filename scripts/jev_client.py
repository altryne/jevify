"""Small, fast TypeSafe System One client. Standard library only; copy it into a project or import it.

    from jev_client import JevClient
    client = JevClient()                                  # reads TYPESAFE_API_KEY
    answers = client.ask(state, questions)["answers"]     # one request
    results = client.ask_many(bodies, concurrency=16)     # many requests at once, results in input order
    client = JevClient(cache_dir=".jev-cache")            # reruns only send what is new or failed

Speed comes from three things, in this order:
1. Pack independent questions into one request. They run in parallel server-side and state is billed once.
2. Send the requests you still have concurrently (`ask_many`), over reused connections.
3. Stay under the account rate limits so nothing is spent on 429 backoff (`requests_per_minute`).

A failed request comes back as {"error": ...}. A failure is "not judged", never a negative answer.
Check https://docs.typesafe.ai/models for current limits and price before relying on the defaults.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Iterable

HOST = "api.typesafe.ai"
PATH = "/v1/systemone"
DEFAULT_MODEL = "jev-1.13.0"
KEY_ENV = "TYPESAFE_API_KEY"
KEY_URL = "https://console.typesafe.ai/settings/keys"
RETRY_STATUSES = {429, 529}


class MissingKey(RuntimeError):
    pass


def load_key(env_files: Iterable[str | Path] = (".env",)) -> str:
    """Return the key from the environment, else from a KEY=value line in the given env files.

    Looks only where it is told to. The value is never printed or logged.
    """
    key = os.environ.get(KEY_ENV)
    if key:
        return key
    for env_file in env_files:
        path = Path(env_file)
        if not path.is_file():
            continue
        for line in path.read_text().splitlines():
            name, _, value = line.strip().removeprefix("export ").partition("=")
            if name.strip() == KEY_ENV and value.strip():
                return value.strip().strip("\"'")
    raise MissingKey(
        f"{KEY_ENV} is not set. Create a key at {KEY_URL}, then `export {KEY_ENV}=...` "
        f"or add `{KEY_ENV}=...` to a git-ignored .env file."
    )


class JevClient:
    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL, timeout: float = 30.0,
                 retries: int = 3, requests_per_minute: int = 1200, env_files: Iterable[str | Path] = (".env",),
                 cache_dir: str | Path | None = None):
        self.api_key = api_key or load_key(env_files)
        self.model, self.timeout, self.retries = model, timeout, retries
        self._interval = 60.0 / requests_per_minute if requests_per_minute else 0.0
        self._pace_lock, self._next_start = threading.Lock(), 0.0
        self._local = threading.local()
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _pace(self) -> None:
        """Space request starts evenly so a burst does not trip the requests-per-minute limit."""
        if not self._interval:
            return
        with self._pace_lock:
            now = time.monotonic()
            start = max(now, self._next_start)
            self._next_start = start + self._interval
        if start > now:
            time.sleep(start - now)

    def _connection(self, fresh: bool = False) -> http.client.HTTPSConnection:
        if fresh or getattr(self._local, "connection", None) is None:
            self._local.connection = http.client.HTTPSConnection(HOST, timeout=self.timeout)
        return self._local.connection

    def ask(self, state: Any, questions: dict[str, Any], model: str | None = None) -> dict[str, Any]:
        """One request. Returns the response plus `seconds`, or {"error": ..., "status": ...}."""
        payload = json.dumps({"model": model or self.model, "state": state, "questions": questions}, sort_keys=True)
        cached = self.cache_dir / f"{hashlib.sha256(payload.encode()).hexdigest()}.json" if self.cache_dir else None
        if cached and cached.exists():
            return {**json.loads(cached.read_text()), "seconds": 0.0, "cached": True}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        last_error: dict[str, Any] = {"error": "not attempted"}
        for attempt in range(self.retries + 1):
            self._pace()
            started = time.perf_counter()
            try:
                connection = self._connection()
                connection.request("POST", PATH, body=payload, headers=headers)
                response = connection.getresponse()
                text = response.read().decode(errors="replace")
            except (OSError, http.client.HTTPException) as error:
                self._connection(fresh=True)
                last_error = {"error": f"{type(error).__name__}: {error}"}
            else:
                if response.status == 200:
                    try:
                        result = json.loads(text)
                    except json.JSONDecodeError:
                        return {"error": "Malformed JSON response; request was not judged.", "status": 200}
                    if not isinstance(result, dict) or not isinstance(result.get("answers"), dict):
                        return {"error": "Missing answers in response; request was not judged.", "status": 200}
                    if cached:                       # only successes are stored, so failures are retried next run
                        cached.write_text(json.dumps(result))
                    return {**result, "seconds": time.perf_counter() - started}
                last_error = {"error": "Provider rejected the request; response body omitted to protect submitted data.",
                              "status": response.status}
                if response.status not in RETRY_STATUSES:
                    return last_error
                retry_after = response.getheader("Retry-After", "")
                if attempt < self.retries and retry_after.replace(".", "", 1).isdigit():
                    time.sleep(min(30.0, float(retry_after)))
                    continue
            if attempt < self.retries:
                time.sleep(min(8.0, 0.25 * 2**attempt) * (0.5 + random.random()))
        return last_error

    def ask_many(self, bodies: list[dict[str, Any]], concurrency: int = 16) -> list[dict[str, Any]]:
        """Send request bodies ({"state", "questions", optional "model"}) concurrently. Results keep input order."""
        def one(body: dict[str, Any]) -> dict[str, Any]:
            return self.ask(body["state"], body["questions"], body.get("model"))
        with ThreadPoolExecutor(max_workers=max(1, min(concurrency, len(bodies) or 1))) as pool:
            return list(pool.map(one, bodies))


def chunk(items: list[Any], size: int) -> list[list[Any]]:
    """Split candidates into request-sized groups."""
    return [items[start:start + size] for start in range(0, len(items), size)]
