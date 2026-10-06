"""Gemini budget: < 15 requests/minute, < 250K tokens/minute, daily cap per model, fallback to the next model (offline, zero token)."""
import pytest
from langchain_core.messages import AIMessage

from lab import gemini
from lab.gemini import GeminiFallbackChat, RateLimiter, classify_error


class Clock:
    def __init__(self):
        self.t = 1_000_000.0
        self.slept = 0.0

    def now(self):
        return self.t

    def sleep(self, s):
        self.slept += s
        self.t += s


def make(tmp_path, rpm=14):
    c = Clock()
    return RateLimiter(path=tmp_path / "u.json", rpm=rpm, clock=c.now, sleep=c.sleep, log=lambda m: None), c


def test_never_more_than_fourteen_requests_in_a_minute(tmp_path):
    lim, c = make(tmp_path, rpm=40)          # asking for 40 is clamped to 14
    stamps = []
    for _ in range(45):
        assert lim.acquire(["gemini-3.5-flash-lite"]) == "gemini-3.5-flash-lite"
        stamps.append(c.t)
    for i, t in enumerate(stamps):
        assert sum(1 for s in stamps if t - 60 < s <= t) <= 14, i


def test_token_budget_per_minute(tmp_path):
    lim, c = make(tmp_path)
    stamps = []
    for _ in range(12):
        lim.acquire(["gemini-3.5-flash-lite"])
        lim.record_tokens(100_000)           # each request uses 100K tokens
        stamps.append(c.t)
    for t in stamps:
        assert sum(100_000 for s in stamps if t - 60 < s <= t) <= 250_000


def test_daily_cap_switches_to_next_model(tmp_path):
    lim, _ = make(tmp_path)
    chain = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
    got = [lim.acquire(chain) for _ in range(505)]
    assert got.count("gemini-3.5-flash-lite") == 499 and got[499] == "gemini-3.1-flash-lite"     # 500 RPD quota, 1 spare


def test_all_models_exhausted_returns_none(tmp_path):
    lim, _ = make(tmp_path)
    for _ in range(499):
        lim.acquire(["gemini-3.5-flash-lite"])
    assert lim.acquire(["gemini-3.5-flash-lite"]) is None


def test_budget_survives_a_new_process(tmp_path):
    lim, c = make(tmp_path)
    for _ in range(3):
        lim.acquire(["gemini-3.5-flash-lite"])
    lim2 = RateLimiter(path=tmp_path / "u.json", rpm=14, clock=c.now, sleep=c.sleep, log=lambda m: None)
    assert lim2.usage()["counts"]["gemini-3.5-flash-lite"] == 3 and len(lim2.usage()["recent"]) == 3


def test_new_quota_day_resets_the_counts(tmp_path):
    lim, c = make(tmp_path)
    for _ in range(499):
        lim.acquire(["gemini-3.5-flash-lite"])
    c.t += 30 * 3600
    assert lim.acquire(["gemini-3.5-flash-lite"]) == "gemini-3.5-flash-lite"


def test_classify_errors():
    daily = Exception("429 RESOURCE_EXHAUSTED. Quota exceeded for metric GenerateRequestsPerDayPerProjectPerModel-FreeTier")
    minute = Exception("429 RESOURCE_EXHAUSTED. Quota exceeded ... PerMinute ... Please retry in 41.2s")
    assert classify_error(daily)[0] == "daily"
    assert classify_error(minute)[0] == "minute" and classify_error(minute)[1] >= 41
    assert classify_error(Exception("404 NOT_FOUND model is not found"))[0] == "missing"
    assert classify_error(Exception("503 UNAVAILABLE"))[0] == "transient"
    assert classify_error(ValueError("bad schema"))[0] == "other"


def test_chat_model_falls_back_when_a_model_is_exhausted(tmp_path, monkeypatch):
    lim, _ = make(tmp_path)
    monkeypatch.setattr(gemini, "_LIMITER", lim)
    used = []

    class Fake:
        def __init__(self, name):
            self.name = name

        def invoke(self, messages, **kw):
            used.append(self.name)
            if self.name == "gemini-3.5-flash":
                raise Exception("429 RESOURCE_EXHAUSTED GenerateRequestsPerDayPerProjectPerModel-FreeTier")
            return AIMessage(content="ok", usage_metadata={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2})

    model = GeminiFallbackChat(models=["gemini-3.5-flash", "gemini-3.6-flash"])
    monkeypatch.setattr(GeminiFallbackChat, "_inner", lambda self, name: Fake(name))
    assert model.invoke("hi").content == "ok"
    assert used == ["gemini-3.5-flash", "gemini-3.6-flash"]
    assert model.invoke("again").content == "ok" and used[-1] == "gemini-3.6-flash" and "gemini-3.5-flash" not in used[2:]


def test_chat_model_raises_when_everything_is_used_up(tmp_path, monkeypatch):
    lim, _ = make(tmp_path)
    monkeypatch.setattr(gemini, "_LIMITER", lim)
    for _ in range(499):
        lim.acquire(["gemini-3.5-flash-lite"])
    with pytest.raises(RuntimeError, match="used up"):
        GeminiFallbackChat(models=["gemini-3.5-flash-lite"]).invoke("hi")


def test_hung_call_times_out_and_is_retried_on_the_next_model(tmp_path, monkeypatch):
    import time
    lim, _ = make(tmp_path)
    monkeypatch.setattr(gemini, "_LIMITER", lim)
    monkeypatch.setattr(gemini, "REQUEST_TIMEOUT", 0.2)

    class Fake:
        def __init__(self, name):
            self.name = name

        def invoke(self, messages, **kw):
            if self.name == "gemini-3.5-flash-lite":
                time.sleep(2)
            return AIMessage(content="ok")

    monkeypatch.setattr(GeminiFallbackChat, "_inner", lambda self, name: Fake(name))
    model = GeminiFallbackChat(models=["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"], max_attempts=1)
    assert model.invoke("hi").content == "ok"
