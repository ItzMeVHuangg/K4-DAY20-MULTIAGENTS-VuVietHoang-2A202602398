"""Gemini (free tier) chat model with a request budget for gemini-3.5-flash-lite / gemini-3.1-flash-lite
(15 RPM, 250K TPM, 500 RPD each): at most 14 requests per minute, at most ~225K tokens per minute and a per-model
daily cap (500 RPD minus a safety margin). When a model has used up its day, the next model of the chain is used.

Used by `lab.model.make_model` when LAB_MODEL starts with `google_genai:`. The counters are kept in a small JSON
file (default `<repo>/.gemini_usage.json`, git-ignored) so that separate runs share the same budget.

Environment variables (all optional):
  LAB_FALLBACK_MODELS   comma separated model ids tried after LAB_MODEL (default: DEFAULT_CHAIN below)
  LAB_MAX_RPM           requests per minute over all models (default 14, never above 14)
  LAB_USAGE_FILE        path of the usage file
"""
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatGeneration, ChatResult

from .tasks import ROOT

# Free-tier daily quota (RPD) per model, read from Google AI Studio. Unknown models get 20.
DAILY_QUOTA = {
    "gemini-3.5-flash": 20,
    "gemini-3.6-flash": 20,
    "gemini-3.7-flash": 20,
    "gemini-3.8-flash": 20,
    "gemini-3-flash-preview": 20,
    "gemini-2.5-flash": 20,
    "gemini-2.5-flash-lite": 20,
    "gemini-3.1-flash-lite": 500,
    "gemini-3.5-flash-lite": 500,
}
# Order: best quality first, the models with a large daily quota last (they are the last resort).
DEFAULT_CHAIN = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
RPM_HARD_CAP = 14         # "< 15 requests per minute"
TPM_BUDGET = 225_000      # below the 250K tokens per minute of the free tier
TOKENS_PER_REQUEST_GUESS = 30_000   # reserved for a request whose size is not known yet
WINDOW_SECONDS = 62       # a little more than 60 s, to be safe with clock differences
RPD_MARGIN = 1            # stay below the daily quota (500 -> 499)
REQUEST_TIMEOUT = 150     # hard limit (s) for one API call; a hung call is treated as a transient error


def _quota_day(now: float) -> str:
    """Date of the quota day. Google resets daily quotas at midnight Pacific time."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.fromtimestamp(now, ZoneInfo("America/Los_Angeles")).date().isoformat()
    except Exception:  # noqa: BLE001  (no tzdata on this machine)
        return (datetime.fromtimestamp(now, timezone.utc) - timedelta(hours=8)).date().isoformat()


class RateLimiter:
    """Shared budget: requests per minute (all models together) and requests per day (per model)."""

    def __init__(self, path=None, rpm=None, clock=time.time, sleep=time.sleep, log=None):
        self.path = Path(path or os.getenv("LAB_USAGE_FILE") or ROOT / ".gemini_usage.json")
        want = rpm if rpm is not None else int(os.getenv("LAB_MAX_RPM", RPM_HARD_CAP))
        self.rpm = max(1, min(want, RPM_HARD_CAP))
        self.clock, self.sleep = clock, sleep
        self.log = log or (lambda msg: print(f"[gemini] {msg}", file=sys.stderr, flush=True))
        self.lock = threading.Lock()
        self.unavailable: set[str] = set()      # models that do not exist for this key (this process only)

    # ---- state file -------------------------------------------------------------------------------
    def _load(self, now: float) -> dict:
        try:
            state = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            state = {}
        day = _quota_day(now)
        if state.get("day") != day:
            state = {"day": day, "counts": {}, "exhausted": [], "recent": state.get("recent", [])}
        state.setdefault("counts", {})
        state.setdefault("exhausted", [])
        state["recent"] = [t for t in state.get("recent", []) if now - t < WINDOW_SECONDS]
        state["tokens"] = [e for e in state.get("tokens", []) if now - e[0] < WINDOW_SECONDS]
        return state

    def _save(self, state: dict) -> None:
        try:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(state), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError:
            pass    # the budget still holds in memory for this process

    @staticmethod
    def cap(model: str) -> int:
        return max(1, DAILY_QUOTA.get(model, 20) - RPD_MARGIN)

    # ---- public API -------------------------------------------------------------------------------
    def acquire(self, chain: list[str], exclude: set[str] = frozenset()) -> str | None:
        """Pick the first usable model of `chain`, wait for a free per-minute slot, count the request, return the model.
        Returns None when every model is exhausted (or excluded) for today."""
        with self.lock:
            while True:
                now = self.clock()
                state = self._load(now)
                name = next((m for m in chain if m not in exclude and m not in self.unavailable
                             and m not in state["exhausted"] and state["counts"].get(m, 0) < self.cap(m)), None)
                if name is None:
                    return None
                wait = 0.0
                if len(state["recent"]) >= self.rpm:
                    wait = state["recent"][-self.rpm] + WINDOW_SECONDS - now
                    reason = f"{self.rpm} requests/minute"
                used = sum(n for _, n in state["tokens"])
                if used + TOKENS_PER_REQUEST_GUESS > TPM_BUDGET and state["tokens"]:
                    # wait until enough old token usage leaves the 1-minute window
                    over, freed = used + TOKENS_PER_REQUEST_GUESS - TPM_BUDGET, 0
                    for t, n in state["tokens"]:
                        freed += n
                        if freed >= over:
                            wait = max(wait, t + WINDOW_SECONDS - now)
                            reason = f"{TPM_BUDGET // 1000}K tokens/minute"
                            break
                if wait > 0:
                    self.log(f"rate limit: waiting {wait:.0f}s ({reason})")
                    self.sleep(wait)
                    continue
                state["recent"].append(now)
                state["counts"][name] = state["counts"].get(name, 0) + 1
                self._save(state)
                return name

    def record_tokens(self, total: int) -> None:
        """Remember how many tokens the last response used (for the tokens-per-minute budget)."""
        if total <= 0:
            return
        with self.lock:
            now = self.clock()
            state = self._load(now)
            state["tokens"].append([now, int(total)])
            self._save(state)

    def mark_exhausted(self, model: str) -> None:
        """The API says the daily quota of `model` is used up: do not use it again today."""
        with self.lock:
            state = self._load(self.clock())
            if model not in state["exhausted"]:
                state["exhausted"].append(model)
            self._save(state)
        self.log(f"daily quota of {model} is used up, switching to the next model")

    def mark_unavailable(self, model: str) -> None:
        self.unavailable.add(model)
        self.log(f"{model} is not available for this key, switching to the next model")

    def cool_down(self, seconds: float) -> None:
        """The API asked us to slow down: block the next requests for `seconds`."""
        with self.lock:
            now = self.clock()
            state = self._load(now)
            state["recent"] = [now + seconds - WINDOW_SECONDS] * self.rpm
            self._save(state)

    def usage(self) -> dict:
        with self.lock:
            return self._load(self.clock())


def classify_error(exc: Exception) -> tuple[str, float]:
    """Map an API error to ('daily'|'minute'|'missing'|'transient'|'other', seconds to wait)."""
    text = f"{type(exc).__name__}: {exc}"
    low = text.lower()
    delay = 0.0
    m = re.search(r"retry(?:delay)?\W{1,12}(\d+(?:\.\d+)?)\s*s", low) or re.search(r"retry in (\d+(?:\.\d+)?)", low)
    if m:
        delay = float(m.group(1))
    if "429" in low or "resource_exhausted" in low or "quota" in low or "rate limit" in low:
        if "perday" in low.replace(" ", "").replace("_", "") or "per day" in low or "daily" in low:
            return "daily", delay
        return "minute", max(delay, 30.0)
    if "404" in low or "not_found" in low or "is not found" in low or "not supported for generatecontent" in low:
        return "missing", 0.0
    if any(c in low for c in ("500", "502", "503", "504", "unavailable", "overloaded", "deadline", "timed out", "timeout", "connect", "getaddrinfo", "network", "reset by peer")):
        return "transient", 10.0
    return "other", 0.0


_LIMITER: RateLimiter | None = None


def get_limiter() -> RateLimiter:
    global _LIMITER
    if _LIMITER is None:
        _LIMITER = RateLimiter()
    return _LIMITER


class GeminiFallbackChat(BaseChatModel):
    """Chat model that sends every request to the first Gemini model of `models` that still has budget."""

    models: list[str]
    temperature: float = 0.0
    bound_tools: list = []
    bound_kwargs: dict = {}
    max_attempts: int = 3          # attempts per model for transient errors

    @property
    def _llm_type(self) -> str:
        return "gemini-fallback"

    def bind_tools(self, tools, **kwargs):
        return self.model_copy(update={"bound_tools": list(tools), "bound_kwargs": dict(kwargs)})

    def _inner(self, name: str):
        from langchain_google_genai import ChatGoogleGenerativeAI
        m = ChatGoogleGenerativeAI(model=name, temperature=self.temperature, max_retries=0, timeout=180)
        return m.bind_tools(self.bound_tools, **self.bound_kwargs) if self.bound_tools else m

    def _call(self, name: str, messages, stop, kwargs):
        """One API call with a hard timeout (a hung call must not freeze the whole run)."""
        pool = ThreadPoolExecutor(max_workers=1)
        future = pool.submit(lambda: self._inner(name).invoke(messages, stop=stop, **kwargs))
        try:
            return future.result(timeout=REQUEST_TIMEOUT)
        except FutureTimeout:
            raise TimeoutError(f"{name}: no answer after {REQUEST_TIMEOUT}s (timed out)") from None
        finally:
            pool.shutdown(wait=False)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs: Any) -> ChatResult:
        limiter = get_limiter()
        skipped: set[str] = set()
        attempts: dict[str, int] = {}
        while True:
            name = limiter.acquire(self.models, exclude=skipped)
            if name is None:
                raise RuntimeError("All Gemini models are used up for today (request budget exhausted): " + ", ".join(self.models))
            try:
                ai = self._call(name, messages, stop, kwargs)
                limiter.record_tokens((ai.usage_metadata or {}).get("total_tokens", 0))
            except Exception as exc:  # noqa: BLE001
                kind, delay = classify_error(exc)
                if kind == "daily":
                    limiter.mark_exhausted(name)
                elif kind == "minute":
                    limiter.log(f"{name}: per-minute limit hit, cooling down {delay:.0f}s")
                    limiter.cool_down(delay)
                elif kind == "missing":
                    limiter.mark_unavailable(name)
                elif kind == "transient":
                    attempts[name] = attempts.get(name, 0) + 1
                    if attempts[name] >= self.max_attempts:
                        skipped.add(name)
                    limiter.sleep(delay * attempts[name])
                else:
                    raise
                continue
            if isinstance(ai.response_metadata, dict):
                ai.response_metadata.setdefault("model_name", name)
            return ChatResult(generations=[ChatGeneration(message=ai)])


def make_gemini_model(first: str, temperature: float = 0.0) -> GeminiFallbackChat:
    """`first` is tried first; then LAB_FALLBACK_MODELS (or DEFAULT_CHAIN) in order."""
    extra = [m.strip() for m in os.getenv("LAB_FALLBACK_MODELS", ",".join(DEFAULT_CHAIN)).split(",") if m.strip()]
    chain = [first] + [m for m in extra if m != first]
    return GeminiFallbackChat(models=chain, temperature=temperature)
