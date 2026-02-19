"""Tests for ResponseCache."""
import time
import pytest
from aip_proxy.cache import ResponseCache


def test_cache_disabled():
    cache = ResponseCache(enabled=False)
    req = {"model": "gpt-4", "messages": [{"role": "user", "content": "hi"}], "temperature": 0}
    cache.put(req, {"choices": [{"message": {"content": "hello"}}]})
    assert cache.get(req) is None


def test_cache_hit():
    cache = ResponseCache(enabled=True, ttl=60)
    req = {"model": "gpt-4", "messages": [{"role": "user", "content": "hi"}], "temperature": 0}
    resp = {"choices": [{"message": {"content": "hello"}}]}
    cache.put(req, resp)
    result = cache.get(req)
    assert result == resp


def test_cache_miss():
    cache = ResponseCache(enabled=True, ttl=60)
    req = {"model": "gpt-4", "messages": [{"role": "user", "content": "hi"}], "temperature": 0}
    assert cache.get(req) is None


def test_cache_skip_nonzero_temperature():
    cache = ResponseCache(enabled=True, ttl=60)
    req = {"model": "gpt-4", "messages": [{"role": "user", "content": "hi"}], "temperature": 0.7}
    resp = {"choices": [{"message": {"content": "hello"}}]}
    cache.put(req, resp)
    # Should not be cached because temperature > 0
    assert cache.get(req) is None


def test_cache_ttl_expiry():
    cache = ResponseCache(enabled=True, ttl=1)
    req = {"model": "gpt-4", "messages": [{"role": "user", "content": "hi"}], "temperature": 0}
    resp = {"choices": [{"message": {"content": "hello"}}]}
    cache.put(req, resp)
    assert cache.get(req) == resp
    time.sleep(1.1)
    assert cache.get(req) is None


def test_cache_eviction():
    cache = ResponseCache(enabled=True, ttl=60, max_size=2)
    for i in range(3):
        req = {"model": "gpt-4", "messages": [{"role": "user", "content": f"msg{i}"}], "temperature": 0}
        cache.put(req, {"id": i})
    assert cache.get_stats()["entries"] <= 2
    assert cache.get_stats()["evictions"] >= 1


def test_cache_stats():
    cache = ResponseCache(enabled=True, ttl=60)
    req = {"model": "gpt-4", "messages": [{"role": "user", "content": "hi"}], "temperature": 0}
    cache.put(req, {"ok": True})
    cache.get(req)  # hit
    cache.get({"model": "gpt-4", "messages": [{"role": "user", "content": "other"}], "temperature": 0})  # miss
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
