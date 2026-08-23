"""
Data access layer for application users.

Keeps all reads and writes against the users collection in one place so that
the REST layer never builds a user query itself.
"""

from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError

import auth


class UserService(object):
    """CRUD operations for the users collection."""

    COLLECTION = "users"

    def __init__(self, uri, database):
        self.client = MongoClient(uri)
        self.database = self.client[database]
        self.users = self.database[self.COLLECTION]

    def ensure_indexes(self):
        """Create the unique index on username.

        Enforcing uniqueness at the database level prevents a race between two
        concurrent registrations from producing duplicate accounts, which an
        application-level existence check alone would not catch.
        """
        self.users.create_index([("username", ASCENDING)], unique=True)

    def create_user(self, username, password, role):
        """Create a user with a hashed password. Returns the new user's id.

        Raises ValueError if the role is unknown or the username is taken.
        """
        if role not in auth.VALID_ROLES:
            raise ValueError("Unknown role: %s" % role)

        username = (username or "").strip().lower()
        if not username:
            raise ValueError("Username must not be empty.")

        document = {
            "username": username,
            "password_hash": auth.hash_password(password),
            "role": role,
            "active": True,
        }

        try:
            result = self.users.insert_one(document)
        except DuplicateKeyError:
            raise ValueError("Username '%s' already exists." % username)

        return result.inserted_id

    def authenticate(self, username, password):
        """Verify credentials and return the user's role.

        Raises auth.AuthError on any failure. The same message is used for an
        unknown username and a bad password so that the response cannot be used
        to enumerate valid accounts.
        """
        username = (username or "").strip().lower()
        record = self.users.find_one({"username": username})

        if record is None or not record.get("active", False):
            # Still run a hash comparison against a dummy value so that a
            # missing user and a wrong password take a similar amount of time.
            auth.verify_password(password or "", _DUMMY_HASH)
            raise auth.AuthError("Invalid username or password.")

        if not auth.verify_password(password, record.get("password_hash", "")):
            raise auth.AuthError("Invalid username or password.")

        return record["role"]

    def set_active(self, username, active):
        """Enable or disable an account without deleting it."""
        result = self.users.update_one(
            {"username": (username or "").strip().lower()},
            {"$set": {"active": bool(active)}},
        )
        return result.modified_count

    def close(self):
        self.client.close()


# Precomputed hash of an unused value, used to equalize login timing when the
# supplied username does not exist.
_DUMMY_HASH = (
    "$2b$12$C6UzMDM.H6dfI/f/IKcEeO3nCBl5rQ8pDhVCEcS9lTX9c8dHhx3Vy"
)
