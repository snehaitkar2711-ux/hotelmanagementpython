"""Manager actions."""

import sqlite3

from database import create_user, list_users


def manager_menu(user) -> None:
    while True:
        print("\n--- Manager ---")
        print("1. Add waiter")
        print("2. List waiters")
        print("3. Log out")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            username = input("New waiter username: ").strip()
            password = input("New waiter password (at least 8 characters): ")
            try:
                create_user(username, password, "waiter", user["id"])
                print(f"Waiter '{username}' created.")
            except (ValueError, sqlite3.IntegrityError) as error:
                print(f"Could not create waiter: {error}")
        elif choice == "2":
            waiters = list_users("waiter")
            if not waiters:
                print("No waiters have been added yet.")
            for waiter in waiters:
                print(
                    f"ID {waiter['id']} | {waiter['username']} | "
                    f"created {waiter['created_at']}"
                )
        elif choice == "3":
            return
        else:
            print("Choose 1, 2, or 3.")