"""Small, fast TypeSafe System One client. Standard library only; copy it into a project or import it.

    from jev_client import JevClient
    client = JevClient()                                  # reads TYPESAFE_API_KEY, else OPENROUTER_API_KEY
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
OPENROUTER_HOST = "openrouter.ai"
OPENROUTER_PATH = "/api/v1/systemone"
OPENROUTER_KEY_ENV = "OPENROUTER_API_KEY"
OPENROUTER_MODELS = {"jev-1.13.0": "typesafe/jev-1.13"}  # OpenRouter rejects TypeSafe's bare ids with HTTP 400
RETRY_STATUSES = {429, 529}


class MissingKey(RuntimeError):
    pass


def find_key(name: str, env_files: Iterable[str | Path] = (".env",)) -> str | None:
    """Return the named key from the environment, else from a NAME=value line in the given env files."""
    key = os.environ.get(name)
    if key:
        return key
    for env_file in env_files:
        path = Path(env_file)
        if not path.is_file():
            continue
        for line in path.read_text().splitlines():
            found, _, value = line.strip().removeprefix("export ").partition("=")
            value = value.strip().strip("\"'")
            if found.strip() == name and value:
                return value
    return None


def load_key(env_files: Iterable[str | Path] = (".env",)) -> str:
    """Return TYPESAFE_API_KEY from the environment, else from the given env files.

    Looks only where it is told to. The value is never printed or logged.
    """
    key = find_key(KEY_ENV, env_files)
    if key:
        return key
    raise MissingKey(
        f"{KEY_ENV} is not set. Create a key at {KEY_URL}, then `export {KEY_ENV}=...` "
        f"or add `{KEY_ENV}=...` to a git-ignored .env file. {OPENROUTER_KEY_ENV} also works."
    )


class JevClient:
    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL, timeout: float = 30.0,
                 retries: int = 3, requests_per_minute: int = 1200, env_files: Iterable[str | Path] = (".env",),
                 cache_dir: str | Path | None = None, openrouter: bool | None = None):
        """`openrouter=None` uses TypeSafe unless no TypeSafe key is found and OPENROUTER_API_KEY is."""
        if openrouter is None and not api_key:
            try:
                api_key, openrouter = load_key(env_files), False
            except MissingKey:
                api_key = find_key(OPENROUTER_KEY_ENV, env_files)
                if not api_key:
                    raise
                openrouter = True
        elif openrouter and not api_key:
            api_key = find_key(OPENROUTER_KEY_ENV, env_files)
            if not api_key:
                raise MissingKey(f"{OPENROUTER_KEY_ENV} is not set.")
        self.api_key = api_key or load_key(env_files)
        self.openrouter = bool(openrouter)
        self.host, self.path = (OPENROUTER_HOST, OPENROUTER_PATH) if self.openrouter else (HOST, PATH)
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
            self._local.connection = http.client.HTTPSConnection(self.host, timeout=self.timeout)
        return self._local.connection

    def ask(self, state: Any, questions: dict[str, Any], model: str | None = None) -> dict[str, Any]:
        """One request. Returns the response plus `seconds`, or {"error": ..., "status": ...}."""
        model = model or self.model
        if self.openrouter:
            model = OPENROUTER_MODELS.get(model, model)
        payload = json.dumps({"model": model, "state": state, "questions": questions}, sort_keys=True)
        cached = self.cache_dir / f"{hashlib.sha256(payload.encode()).hexdigest()}.json" if self.cache_dir else None
        if cached and cached.exists():
            try:
                return {**json.loads(cached.read_text()), "seconds": 0.0, "cached": True}
            except (OSError, json.JSONDecodeError, TypeError):
                pass                             # an unreadable entry is a miss; the request is sent again
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        last_error: dict[str, Any] = {"error": "not attempted"}
        for attempt in range(self.retries + 1):
            self._pace()
            started = time.perf_counter()
            try:
                connection = self._connection()
                connection.request("POST", self.path, body=payload, headers=headers)
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
                    missing = sorted(set(questions) - set(result["answers"]))
                    if missing:              # keep the answers that came back, but never cache a partial result
                        return {**result, "seconds": time.perf_counter() - started, "missing": missing}
                    if cached:                       # only complete successes are stored, so failures are retried next run
                        partial = cached.with_name(f"{cached.name}.{os.getpid()}.{threading.get_ident()}.tmp")
                        partial.write_text(json.dumps(result))
                        os.replace(partial, cached)  # readers see the whole entry or none
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
