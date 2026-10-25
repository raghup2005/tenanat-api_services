
import hashlib
import secrets


def generate_api_key() -> str:
    """Generate a cryptographically secure API key."""
    return f"tsk_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """Return the SHA-256 hash of an API key."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """Verify an API key against its stored hash."""
    return secrets.compare_digest(
        hash_api_key(api_key),
        stored_hash,
    )
