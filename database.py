"""SQLite storage and application entry point for the hotel management app."""

import hashlib
import hmac
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional


DATABASE_PATH = Path(__file__).with_name("hotel_management.db")
ROLES = ("platformadmin", "manager", "waiter")
_PASSWORD_ITERATIONS = 310_000


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Open a database connection with foreign-key checks and close it afterward."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database() -> None:
    """Create the tables used by the application if they do not exist."""
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('platformadmin', 'manager', 'waiter')),
                created_by INTEGER REFERENCES users(id),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


def hash_password(password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
    """Return a PBKDF2 password hash and its salt, both hex-encoded."""
    salt = salt or secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PASSWORD_ITERATIONS
    )
    return password_hash.hex(), salt.hex()


def verify_password(password: str, password_hash: str, salt_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    candidate_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate_hash, password_hash)


def create_user(
    username: str, password: str, role: str, created_by: Optional[int] = None
) -> int:
    """Create a role account and return its ID."""
    username = username.strip()
    if not username:
        raise ValueError("Username cannot be empty.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if role not in ROLES:
        raise ValueError("Invalid account role.")

    password_hash, password_salt = hash_password(password)
    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (username, password_hash, password_salt, role, created_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, password_hash, password_salt, role, created_by),
        )
        return int(cursor.lastrowid)


def authenticate(username: str, password: str) -> Optional[sqlite3.Row]:
    with connect() as connection:
        user = connection.execute(
            "SELECT * FROM users WHERE username = ?", (username.strip(),)
        ).fetchone()
    if user is None or not verify_password(
        password, user["password_hash"], user["password_salt"]
    ):
        return None
    return user


def list_users(
    role: Optional[str] = None, created_by: Optional[int] = None
) -> list[sqlite3.Row]:
    with connect() as connection:
        if role and created_by is not None:
            return list(
                connection.execute(
                    "SELECT id, username, role, created_at FROM users "
                    "WHERE role = ? AND created_by = ? ORDER BY username",
                    (role, created_by),
                )
            )
        if role:
            return list(
                connection.execute(
                    "SELECT id, username, role, created_at FROM users "
                    "WHERE role = ? ORDER BY username",
                    (role,),
                )
            )
        if created_by is not None:
            return list(
                connection.execute(
                    "SELECT id, username, role, created_at FROM users "
                    "WHERE created_by = ? ORDER BY role, username",
                    (created_by,),
                )
            )
        return list(
            connection.execute(
                "SELECT id, username, role, created_at FROM users ORDER BY role, username"
            )
        )


def bootstrap_platform_admin() -> None:
    """Create the initial admin account on the first run."""
    with connect() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'platformadmin'"
        ).fetchone()[0]
    if count:
        return

    print("Create the first platform admin account.")
    while True:
        username = input("Admin username: ").strip()
        password = input("Admin password (at least 8 characters): ")
        try:
            create_user(username, password, "platformadmin")
            print("Platform admin created. Please log in.\n")
            return
        except (ValueError, sqlite3.IntegrityError) as error:
            print(f"Could not create admin: {error}")


def main() -> None:
    initialize_database()
    bootstrap_platform_admin()

    while True:
        print("\n=== Hotel Management ===")
        print("1. Log in")
        print("2. Exit")
        choice = input("Choose an option: ").strip()

        if choice == "2":
            print("Goodbye.")
            return
        if choice != "1":
            print("Choose 1 or 2.")
            continue

        username = input("Username: ").strip()
        password = input("Password: ")
        user = authenticate(username, password)
        if user is None:
            print("Invalid username or password.")
            continue

        print(f"\nWelcome, {user['username']} ({user['role']}).")
        if user["role"] == "platformadmin":
            from platformadmin import platform_admin_menu

            platform_admin_menu(user)
        elif user["role"] == "manager":
            from manager import manager_menu

            manager_menu(user)
        elif user["role"] == "waiter":
            from waiter import waiter_menu

            waiter_menu(user)


if __name__ == "__main__":
    main()