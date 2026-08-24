"""Quick verification of the auth module. Run with: python test_auth.py"""

import os
import time

os.environ["JWT_SECRET"] = "test-secret-not-for-production"
os.environ["JWT_EXPIRY_MINUTES"] = "30"

import auth


def check(label, condition):
    print(("PASS  " if condition else "FAIL  ") + label)
    assert condition, label


# Hashing
h = auth.hash_password("correct horse battery staple")
check("hash is not plaintext", "correct horse" not in h)
check("hash uses bcrypt format", h.startswith("$2b$"))
check("correct password verifies", auth.verify_password("correct horse battery staple", h))
check("wrong password rejected", not auth.verify_password("wrong", h))
check("same password hashes differently (unique salt)",
      auth.hash_password("abc") != auth.hash_password("abc"))
check("garbage hash rejected safely", not auth.verify_password("abc", "not-a-hash"))

try:
    auth.hash_password("x" * 100)
    check("over-length password rejected", False)
except ValueError:
    check("over-length password rejected", True)

# Tokens
token = auth.generate_token("viewer", auth.ROLE_VIEWER)
payload = auth.decode_token(token)
check("token round-trips username", payload["sub"] == "viewer")
check("token round-trips role", payload["role"] == auth.ROLE_VIEWER)
check("token carries expiry", "exp" in payload)

try:
    auth.generate_token("someone", "superuser")
    check("invalid role rejected", False)
except ValueError:
    check("invalid role rejected", True)

# Tampering
tampered = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
try:
    auth.decode_token(tampered)
    check("tampered signature rejected", False)
except auth.AuthError:
    check("tampered signature rejected", True)

# Expiry
os.environ["JWT_EXPIRY_MINUTES"] = "0"
short = auth.generate_token("viewer", auth.ROLE_VIEWER)
time.sleep(1)
try:
    auth.decode_token(short)
    check("expired token rejected", False)
except auth.AuthError:
    check("expired token rejected", True)
os.environ["JWT_EXPIRY_MINUTES"] = "30"

# Missing secret
saved = os.environ.pop("JWT_SECRET")
try:
    auth.generate_token("viewer", auth.ROLE_VIEWER)
    check("missing secret fails loudly", False)
except RuntimeError:
    check("missing secret fails loudly", True)
os.environ["JWT_SECRET"] = saved

# Role checks
p = auth.decode_token(auth.generate_token("analyst", auth.ROLE_ANALYST))
check("has_role accepts matching role", auth.has_role(p, auth.ROLE_ANALYST, auth.ROLE_ADMIN))
check("has_role rejects non-matching role", not auth.has_role(p, auth.ROLE_ADMIN))

print("\nAll checks passed.")
