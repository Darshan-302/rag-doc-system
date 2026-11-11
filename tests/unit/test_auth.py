"""Tests for src/security/auth.py."""

import pytest
from fastapi import HTTPException

from src.config import settings
from src.security.auth import authorize, parse_api_keys, require_tenant_access


def test_parse_api_keys():
    keys = parse_api_keys(" k1=a,b ; k2=* ;; k1=c ")
    assert keys == {"k1": frozenset({"a", "b", "c"}), "k2": frozenset({"*"})}
    assert parse_api_keys("") == {}


@pytest.mark.parametrize("bad", ["justakey", "k=", "=tenant", "k=,"])
def test_parse_api_keys_rejects_malformed(bad):
    with pytest.raises(ValueError):
        parse_api_keys(bad)


KEYS = {"ka": frozenset({"a"}), "root": frozenset({"*"})}


def status(key, tenant):
    try:
        authorize(key, tenant, KEYS)
    except HTTPException as e:
        return e.status_code
    return 200


def test_authorize_outcomes():
    assert status(None, "a") == 401
    assert status("", "a") == 401
    assert status("wrong", "a") == 401
    assert status("ka", "a") == 200
    assert status("ka", "b") == 403
    assert status("root", "anything") == 200


def test_authorize_uses_constant_time_compare(monkeypatch):
    import hmac

    from src.security import auth

    calls = []
    real = hmac.compare_digest
    monkeypatch.setattr(auth.hmac, "compare_digest", lambda a, b: calls.append(1) or real(a, b))
    status("ka", "a")
    assert len(calls) == len(KEYS)  # compared against every key, no early exit


@pytest.mark.asyncio
async def test_dependency_respects_settings(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "API_KEYS", "ka=a")
    assert await require_tenant_access("a", "ka") == "a"
    with pytest.raises(HTTPException) as e:
        await require_tenant_access("b", "ka")
    assert e.value.status_code == 403
    monkeypatch.setattr(settings, "API_KEYS", "garbage")
    with pytest.raises(HTTPException) as e:
        await require_tenant_access("a", "ka")
    assert e.value.status_code == 401
    monkeypatch.setattr(settings, "AUTH_ENABLED", False)
    assert await require_tenant_access("a", None) == "a"


@pytest.mark.asyncio
async def test_dependency_rejects_bad_tenant_format(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ENABLED", False)
    with pytest.raises(HTTPException) as e:
        await require_tenant_access("bad tenant!", None)
    assert e.value.status_code == 400
