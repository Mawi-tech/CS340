"""
Authentication and authorization utilities.

Provides password hashing, JSON Web Token issuance and verification, and the
role definitions used by the REST layer's access-control decorators. This
module deliberately holds no database logic so that it can be unit tested
without a running MongoDB instance.
"""

import os
import datetime

import bcrypt
import jwt

# Role names used throughout the application. Ordered least to most privileged.
ROLE_VIEWER = "viewer"
ROLE_ANALYST = "analyst"
ROLE_ADMIN = "admin"

VALID_ROLES = (ROLE_VIEWER, ROLE_ANALYST, ROLE_ADMIN)

# bcrypt truncates input past 72 bytes. Rejecting longer passwords outright is
# safer than accepting one that is only partially verified at login.
MAX_PASSWORD_BYTES = 72

# Cost factor for bcrypt. Higher is slower and more resistant to offline
# cracking; 12 is a reasonable balance for an application of this size.
BCRYPT_ROUNDS = 12


class AuthError(Exception):
    """Raised when credentials or a token fail validation."""


def _get_secret():
    """Return the JWT signing secret from the environment.

    Fails loudly rather than falling back to a hardcoded default, so that a
    misconfigured deployment cannot silently run with a publicly known key.
    """
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET is not set. Refusing to start without a signing key."
        )
    return secret


def _get_token_lifetime():
    """Return the token lifetime as a timedelta."""
    minutes = int(os.environ.get("JWT_EXPIRY_MINUTES", "30"))
    return datetime.timedelta(minutes=minutes)


def hash_password(plaintext):
    """Hash a plaintext password with bcrypt and return the encoded hash.

    The returned value contains the salt and cost factor, so no separate salt
    column is required.
    """
    if not isinstance(plaintext, str) or not plaintext:
        raise ValueError("Password must be a non-empty string.")

    encoded = plaintext.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError(
            "Password exceeds %d bytes and cannot be safely hashed."
            % MAX_PASSWORD_BYTES
        )

    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(encoded, salt).decode("utf-8")


def verify_password(plaintext, stored_hash):
    """Return True if the plaintext password matches the stored hash.

    bcrypt.checkpw performs a constant-time comparison, which avoids leaking
    information about the hash through response timing.
    """
    if not plaintext or not stored_hash:
        return False

    encoded = plaintext.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        return False

    try:
        return bcrypt.checkpw(encoded, stored_hash.encode("utf-8"))
    except ValueError:
        # Raised when the stored value is not a valid bcrypt hash.
        return False


def generate_token(username, role):
    """Issue a signed JWT for an authenticated user.

    The payload carries only the username and role. No sensitive data is
    placed in the token, since a JWT payload is encoded rather than encrypted
    and can be read by anyone holding the token.
    """
    if role not in VALID_ROLES:
        raise ValueError("Unknown role: %s" % role)

    issued_at = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": username,
        "role": role,
        "iat": issued_at,
        "exp": issued_at + _get_token_lifetime(),
    }
    return jwt.encode(payload, _get_secret(), algorithm="HS256")


def decode_token(token):
    """Validate a JWT and return its payload.

    The algorithm is pinned to HS256. Allowing the token itself to dictate the
    algorithm would permit an attacker to submit an unsigned "none" token and
    have it accepted.
    """
    if not token:
        raise AuthError("No token supplied.")

    try:
        return jwt.decode(token, _get_secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired.")
    except jwt.InvalidTokenError:
        raise AuthError("Token is invalid.")


def has_role(payload, *allowed_roles):
    """Return True if the token payload carries one of the allowed roles."""
    return payload.get("role") in allowed_roles
