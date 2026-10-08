"""Short, scope-keyed local endpoint probes. Infrastructure failure is not escalation."""

from dataclasses import dataclass, field
import hashlib
import threading
import time

from .profiles import is_local_runtime, resolve_profile


@dataclass
class Availability:
    available: bool
    reason: str = ""
    runtime: dict = field(default_factory=dict, repr=False)


_CACHE = {}
_LOCK = threading.Lock()


def _probe(profile, runtime):
    import httpx
    # Cloud credentials are resolved by Hermes. Do not spend a completion just
    # to check each execution; Test Profile supplies the explicit completion probe.
    if not is_local_runtime(runtime):
        return Availability(True, runtime=runtime)
    url = str(runtime.get("base_url", "")).rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {runtime['api_key']}"} if runtime.get("api_key") else {}
    try:
        response = httpx.get(url, headers=headers, timeout=2, follow_redirects=False, trust_env=False)
        if response.status_code in (401, 403):
            return Availability(False, "authentication_error")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            return Availability(False, "provider_unavailable")
        models = {str(row.get("id", "")) for row in payload["data"] if isinstance(row, dict)}
        if profile.model not in models:
            return Availability(False, "model_not_found")
    except (httpx.HTTPError, ValueError, TypeError):
        return Availability(False, "provider_unavailable")
    return Availability(True, runtime=runtime)


def check_profile(profile, settings, *, force=False):
    from hermes_constants import hermes_home_key
    from hermes_cli.config import load_config_readonly
    # Config changes invalidate the credential-free cache key; runtime credentials
    # are never retained in the availability cache or diagnostics.
    config = load_config_readonly()
    try:
        runtime = resolve_profile(profile)
    except (ValueError, RuntimeError, OSError):
        return Availability(False, "provider_unavailable")
    fingerprint = hashlib.sha256(repr((config.get("providers"), config.get("custom_providers"),
                                      runtime.get("base_url"), runtime.get("api_key"))).encode()).hexdigest()
    key = (hermes_home_key(), profile.provider, profile.model, fingerprint)
    with _LOCK:
        cached = _CACHE.get(key)
        if not force and cached and cached[0] > time.monotonic():
            return Availability(cached[1], cached[2], runtime if cached[1] else {})
    result = _probe(profile, runtime)
    duration = settings["cache_seconds" if result.available else "failure_cooldown_seconds"]
    with _LOCK:
        expired = [k for k, v in _CACHE.items() if v[0] <= time.monotonic()]
        for old in expired:
            del _CACHE[old]
        _CACHE[key] = (time.monotonic() + duration, result.available, result.reason)
    return result
