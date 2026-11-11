"""Authentication and tenant isolation."""

import io

import pytest

from src.config import settings
from tests.integration.conftest import KEY_A, KEY_ADMIN, KEY_B, hdr

SECRET = b"The vault passphrase for project Zephyrine is marmalade sunrise."


def up(client, tenant, key, data=SECRET, name="secret.txt"):
    return client.post(f"/api/v1/{tenant}/documents/upload", headers=hdr(key), files={"file": (name, io.BytesIO(data))})


@pytest.mark.parametrize("method,path", [
    ("post", "/api/v1/tenant-a/query"),
    ("get", "/api/v1/tenant-a/documents"),
    ("delete", "/api/v1/tenant-a/documents/x"),
    ("post", "/api/v1/tenant-a/documents/upload"),
])
def test_missing_or_bad_key_is_401(env, method, path):
    client, *_ = env
    kwargs = {"json": {"query": "q"}} if path.endswith("query") else {}
    assert getattr(client, method)(path, **kwargs).status_code == 401
    assert getattr(client, method)(path, headers=hdr("nope"), **kwargs).status_code == 401


@pytest.mark.parametrize("method,path", [
    ("post", "/api/v1/tenant-b/query"),
    ("get", "/api/v1/tenant-b/documents"),
    ("delete", "/api/v1/tenant-b/documents/x"),
])
def test_valid_key_for_other_tenant_is_403(env, method, path):
    client, *_ = env
    kwargs = {"json": {"query": "q"}} if path.endswith("query") else {}
    assert getattr(client, method)(path, headers=hdr(KEY_A), **kwargs).status_code == 403


def test_tenant_a_cannot_see_tenant_b_chunks(env):
    client, _, store = env
    doc_id = up(client, "tenant-b", KEY_B).json()["document_id"]

    # query: tenant A (own key) finds nothing from B
    q = client.post("/api/v1/tenant-a/query", headers=hdr(KEY_A), json={"query": "vault passphrase Zephyrine"}).json()
    assert q["sources"] == []
    # ...while B sees it
    qb = client.post("/api/v1/tenant-b/query", headers=hdr(KEY_B), json={"query": "vault passphrase Zephyrine"}).json()
    assert qb["sources"][0]["document_id"] == doc_id

    # list
    assert client.get("/api/v1/tenant-a/documents", headers=hdr(KEY_A)).json()["total_count"] == 0

    # delete: A deleting B's document id (via A's own path) is a 404 and B's data survives
    assert client.delete(f"/api/v1/tenant-a/documents/{doc_id}", headers=hdr(KEY_A)).status_code == 404
    assert client.get("/api/v1/tenant-b/documents", headers=hdr(KEY_B)).json()["total_count"] == 1
    # and via B's path with A's key it is forbidden
    assert client.delete(f"/api/v1/tenant-b/documents/{doc_id}", headers=hdr(KEY_A)).status_code == 403
    assert client.get("/api/v1/tenant-b/documents", headers=hdr(KEY_B)).json()["total_count"] == 1


def test_same_content_in_two_tenants_stays_separate(env):
    client, *_ = env
    a = up(client, "tenant-a", KEY_A).json()["document_id"]
    b = up(client, "tenant-b", KEY_B).json()["document_id"]
    assert client.delete(f"/api/v1/tenant-a/documents/{a}", headers=hdr(KEY_A)).status_code == 200
    assert client.get("/api/v1/tenant-b/documents", headers=hdr(KEY_B)).json()["documents"][0]["document_id"] == b


def test_wildcard_key_reaches_all_tenants(env):
    client, *_ = env
    assert up(client, "tenant-a", KEY_ADMIN).status_code == 200
    assert client.get("/api/v1/tenant-a/documents", headers=hdr(KEY_ADMIN)).json()["total_count"] == 1
    assert client.get("/api/v1/tenant-b/documents", headers=hdr(KEY_ADMIN)).json()["total_count"] == 0


def test_invalid_tenant_id_is_400(env):
    client, *_ = env
    assert client.get("/api/v1/bad%20tenant/documents", headers=hdr(KEY_ADMIN)).status_code == 400


def test_auth_disabled_allows_unauthenticated(env, monkeypatch):
    client, *_ = env
    monkeypatch.setattr(settings, "AUTH_ENABLED", False)
    assert client.get("/api/v1/tenant-a/documents").status_code == 200


def test_auth_enabled_without_keys_denies_everything(env, monkeypatch):
    client, *_ = env
    monkeypatch.setattr(settings, "API_KEYS", "")
    assert client.get("/api/v1/tenant-a/documents", headers=hdr(KEY_A)).status_code == 401
