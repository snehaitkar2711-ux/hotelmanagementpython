"""Waiter actions."""

from customer import add_customer, list_customers


def waiter_menu(user) -> None:
    while True:
        print("\n--- Waiter ---")
        print("1. Add customer")
        print("2. List customers I added")
        print("3. Log out")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            name = input("Customer name: ").strip()
            phone = input("Customer phone: ").strip()
            email = input("Customer email (optional): ").strip()
            notes = input("Notes (optional): ").strip()
            try:
                add_customer(user["id"], name, phone, email, notes)
                print(f"Customer '{name}' saved.")
            except ValueError as error:
                print(f"Could not add customer: {error}")
        elif choice == "2":
            customers = list_customers(user["id"])
            if not customers:
                print("You have not added any customers yet.")
            for customer in customers:
                print(
                    f"ID {customer['id']} | {customer['name']} | "
                    f"{customer['phone']} | {customer['email']} | "
                    f"{customer['created_at']}"
                )
        elif choice == "3":
            return
        else:
            print("Choose 1, 2, or 3.")