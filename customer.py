"""Customer records stored in the shared SQLite database."""

from database import connect


def add_customer(
    waiter_id: int, name: str, phone: str, email: str = "", notes: str = ""
) -> int:
    name = name.strip()
    phone = phone.strip()
    if not name:
        raise ValueError("Customer name cannot be empty.")
    if not phone:
        raise ValueError("Customer phone cannot be empty.")

    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO customers (name, phone, email, notes, created_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, phone, email.strip(), notes.strip(), waiter_id),
        )
        return int(cursor.lastrowid)


def list_customers(waiter_id: int | None = None):
    with connect() as connection:
        if waiter_id is None:
            return list(
                connection.execute(
                    """
                    SELECT customers.id, customers.name, customers.phone,
                           customers.email, customers.notes, customers.created_at,
                           users.username AS waiter_name
                    FROM customers
                    JOIN users ON users.id = customers.created_by
                    ORDER BY customers.created_at DESC, customers.id DESC
                    """
                )
            )
        return list(
            connection.execute(
                """
                SELECT id, name, phone, email, notes, created_at
                FROM customers
                WHERE created_by = ?
                ORDER BY created_at DESC, id DESC
                """,
                (waiter_id,),
            )
        )