"""HTTP helpers with an on-disk cache, retries and a bounded thread pool.

PokeAPI serves one JSON document per resource, so a full build makes ~3,700
small requests. Every response is cached on disk (sharded by hash prefix), so
editing a cleaning step never re-downloads anything, and an interrupted first
build resumes where it stopped.
"""

from __future__ import annotations

import atexit
import hashlib
import json
import os
import sys
import threading
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = Path(os.environ.get("PPC_CACHE_DIR", ROOT / "data_cache"))
USER_AGENT = "pokemon-power-creep/0.1 (build-time data loader; python-httpx)"

# PokeAPI's data changes only when new games or forms are added.
DEFAULT_MAX_AGE = timedelta(days=30)
# Parallel requests. PokeAPI has no published rate limit since it moved to a CDN,
# but its fair-use policy asks clients to cache and not hammer it.
WORKERS = int(os.environ.get("POKEAPI_WORKERS", "6"))

# Status codes worth retrying: rate limiting and transient server errors.
RETRY_STATUS = {429, 500, 502, 503, 504}


class NotFound(Exception):
    """The resource does not exist."""


def log(*args: object) -> None:
    """Loaders write data to stdout, so all diagnostics must go to stderr."""
    print(*args, file=sys.stderr, flush=True)


def _cache_path(url: str, suffix: str) -> Path:
    digest = hashlib.sha256(url.encode()).hexdigest()[:20]
    return CACHE_DIR / digest[:2] / f"{digest}{suffix}"


def cached_path(url: str, suffix: str = ".json") -> Path | None:
    """Where ``fetch`` stored this URL, or None if it was never downloaded."""
    path = _cache_path(url, suffix)
    return path if path.exists() else None


_client: httpx.Client | None = None
_client_lock = threading.Lock()


def _get_client() -> httpx.Client:
    """One client per process (it is thread-safe), so requests reuse TLS connections."""
    global _client
    with _client_lock:
        if _client is None:
            _client = httpx.Client(follow_redirects=True, limits=httpx.Limits(max_connections=WORKERS + 2))
            atexit.register(_client.close)
    return _client


def fetch(
    url: str,
    *,
    max_age: timedelta | None = DEFAULT_MAX_AGE,
    suffix: str = ".json",
    retries: int = 5,
    timeout: float = 60.0,
) -> bytes:
    """GET ``url`` and return the body, using the disk cache when fresh.

    ``max_age=None`` caches forever.
    """
    path = _cache_path(url, suffix)
    if path.exists() and (max_age is None or time.time() - path.stat().st_mtime < max_age.total_seconds()):
        return path.read_bytes()

    hdrs = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"}
    delay = 2.0
    for attempt in range(1, retries + 1):
        try:
            resp = _get_client().get(url, headers=hdrs, timeout=timeout)
            if resp.status_code == 404:
                raise NotFound(f"404 for {url}")
            if resp.status_code in RETRY_STATUS:
                raise httpx.HTTPStatusError(f"{resp.status_code}", request=resp.request, response=resp)
            resp.raise_for_status()
            data = resp.content
            break
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            if attempt == retries:
                raise
            retry_after = getattr(getattr(exc, "response", None), "headers", {}).get("Retry-After")
            wait = float(retry_after) if retry_after and retry_after.isdigit() else delay
            log(f"  retry {attempt}/{retries} for {url} in {wait:.0f}s ({exc})")
            time.sleep(wait)
            delay *= 2

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.{threading.get_ident()}.part")
    tmp.write_bytes(data)
    tmp.replace(path)
    return data


def fetch_json(url: str, **kwargs) -> dict:
    return json.loads(fetch(url, **kwargs))


def fetch_many(urls: Iterable[str], *, label: str = "requests", **kwargs) -> list[dict]:
    """``fetch_json`` for many URLs in parallel; results keep the input order.

    Logs progress only for the URLs that actually hit the network.
    """
    urls = list(urls)
    todo = sum(1 for u in urls if cached_path(u) is None)
    if todo:
        log(f"{label}: {todo:,} of {len(urls):,} not cached, downloading with {WORKERS} workers")
    done = 0
    lock = threading.Lock()
    t0 = time.time()

    def one(url: str) -> dict:
        nonlocal done
        out = fetch_json(url, **kwargs)
        with lock:
            done += 1
            if todo and done % 250 == 0:
                log(f"  {label}: {done:,}/{len(urls):,} ({time.time() - t0:.0f}s)")
        return out

    if todo == 0:
        return [fetch_json(u, **kwargs) for u in urls]
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        return list(pool.map(one, urls))
