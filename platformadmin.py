"""Platform admin actions."""

import sqlite3

from database import create_user, list_users


def platform_admin_menu(user) -> None:
    while True:
        print("\n--- Platform Admin ---")
        print("1. Add manager")
        print("2. List accounts")
        print("3. Log out")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            username = input("New manager username: ").strip()
            password = input("New manager password (at least 8 characters): ")
            try:
                create_user(username, password, "manager", user["id"])
                print(f"Manager '{username}' created.")
            except (ValueError, sqlite3.IntegrityError) as error:
                print(f"Could not create manager: {error}")
        elif choice == "2":
            for account in list_users():
                print(
                    f"ID {account['id']} | {account['role']} | "
                    f"{account['username']} | created {account['created_at']}"
                )
        elif choice == "3":
            return
        else:
            print("Choose 1, 2, or 3.")