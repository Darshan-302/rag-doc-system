"""API-key authentication with per-key tenant authorisation.

Configuration (``API_KEYS`` setting / env var)::

    API_KEYS="key1=tenantA,tenantB;key2=*"

* entries are separated by ``;``, each is ``<key>=<tenants>``
* ``<tenants>`` is a comma-separated list of tenant ids, or ``*`` for all
* keys must not contain ``=`` or ``;`` (use long random strings, e.g.
  ``python -c "import secrets; print(secrets.token_urlsafe(32))"``)

Clients send the key in the ``X-API-Key`` header. A missing or unknown key is
rejected with 401; a valid key used on a tenant it is not authorised for gets
403. Set ``AUTH_ENABLED=false`` to disable authentication (local development
only). ``/health`` is never authenticated.
"""

import hashlib
import hmac
import logging
from typing import Dict, FrozenSet, Optional

from fastapi import Header, HTTPException, Path

from src.config import settings
from src.search.vector_store import TENANT_ID_RE

logger = logging.getLogger(__name__)

WILDCARD = "*"


def parse_api_keys(raw: str) -> Dict[str, FrozenSet[str]]:
    """Parse the API_KEYS setting into {key: allowed tenants}."""
    keys: Dict[str, FrozenSet[str]] = {}
    for entry in (raw or "").split(";"):
        entry = entry.strip()
        if not entry:
            continue
        key, sep, tenants = entry.partition("=")
        key = key.strip()
        allowed = frozenset(t.strip() for t in tenants.split(",") if t.strip())
        if not sep or not key or not allowed:
            raise ValueError("Invalid API_KEYS entry; expected 'key=tenantA,tenantB' or 'key=*'")
        keys[key] = allowed | keys.get(key, frozenset())
    return keys


def _digest(value: str) -> bytes:
    return hashlib.sha256(value.encode()).digest()


def authorize(api_key: Optional[str], tenant_id: str, keys: Dict[str, FrozenSet[str]]) -> None:
    """Raise HTTPException unless ``api_key`` may access ``tenant_id``."""
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header", headers={"WWW-Authenticate": "ApiKey"})
    candidate = _digest(api_key)
    allowed: Optional[FrozenSet[str]] = None
    # Compare against every configured key without early exit so timing does
    # not reveal which (or how many) keys match.
    for key, tenants in keys.items():
        if hmac.compare_digest(candidate, _digest(key)):
            allowed = tenants
    if allowed is None:
        raise HTTPException(status_code=401, detail="Invalid API key", headers={"WWW-Authenticate": "ApiKey"})
    if WILDCARD not in allowed and tenant_id not in allowed:
        raise HTTPException(status_code=403, detail="API key is not authorised for this tenant")


async def require_tenant_access(
    tenant_id: str = Path(...),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> str:
    """FastAPI dependency for ``/api/v1/{tenant_id}/...`` routes. Returns the tenant id."""
    if not TENANT_ID_RE.match(tenant_id):
        raise HTTPException(status_code=400, detail="Invalid tenant_id")
    if not settings.AUTH_ENABLED:
        return tenant_id
    try:
        keys = parse_api_keys(settings.API_KEYS)
    except ValueError:
        logger.error("API_KEYS is malformed; rejecting all requests")
        keys = {}
    authorize(x_api_key, tenant_id, keys)
    return tenant_id
