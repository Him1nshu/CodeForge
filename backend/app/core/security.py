"""API-key authorization helpers.

Optional: when a project (or the global settings) has an api key, requests for
that project must present X-API-Key with the matching value. Storage keeps only
a sha256 digest. When no key is configured, access is open (evaluation default).
"""

import hashlib
import secrets


def hash_api_key(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def verify_api_key(plain: str, key_hash: str) -> bool:
    return secrets.compare_digest(hash_api_key(plain), key_hash)
