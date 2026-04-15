import os
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "onlinestore"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
    )


def create_tables(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                customer_id SERIAL PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                product_id SERIAL PRIMARY KEY,
                product_name TEXT NOT NULL,
                price NUMERIC(10, 2) NOT NULL CHECK (price >= 0)
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id SERIAL PRIMARY KEY,
                customer_id INT NOT NULL REFERENCES customers(customer_id),
                order_date TIMESTAMP NOT NULL DEFAULT NOW(),
                total_amount NUMERIC(10, 2) NOT NULL DEFAULT 0
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS order_items (
                order_item_id SERIAL PRIMARY KEY,
                order_id INT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
                product_id INT NOT NULL REFERENCES products(product_id),
                quantity INT NOT NULL CHECK (quantity > 0),
                subtotal NUMERIC(10, 2) NOT NULL CHECK (subtotal >= 0)
            );
            """
        )
    conn.commit()


def seed_data(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO customers (first_name, last_name, email)
            VALUES (%s, %s, %s)
            ON CONFLICT (email) DO NOTHING;
            """,
            ("Lara", "Dolina", "Lara@kvartir.net"),
        )
        cur.execute(
            """
            INSERT INTO products (product_name, price)
            VALUES
                ('Laptop', 1200.00),
                ('Mouse', 25.00),
                ('Keyboard', 70.00)
            ON CONFLICT DO NOTHING;
            """
        )
    conn.commit()


def place_order_transaction(conn, customer_id, items):
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO orders (customer_id, order_date, total_amount)
                VALUES (%s, NOW(), 0)
                RETURNING order_id;
                """,
                (customer_id,),
            )
            order_id = cur.fetchone()[0]

            for product_id, quantity in items:
                cur.execute(
                    "SELECT price FROM products WHERE product_id = %s FOR UPDATE;",
                    (product_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise ValueError(f"Product {product_id} not found")

                price = Decimal(row[0])
                subtotal = price * quantity

                cur.execute(
                    """
                    INSERT INTO order_items (order_id, product_id, quantity, subtotal)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (order_id, product_id, quantity, subtotal),
                )

            cur.execute(
                """
                UPDATE orders
                SET total_amount = (
                    SELECT COALESCE(SUM(subtotal), 0)
                    FROM order_items
                    WHERE order_id = %s
                )
                WHERE order_id = %s;
                """,
                (order_id, order_id),
            )
    return order_id


def update_customer_email_transaction(conn, customer_id, new_email):
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE customers
                SET email = %s
                WHERE customer_id = %s;
                """,
                (new_email, customer_id),
            )
            if cur.rowcount == 0:
                raise ValueError(f"Customer {customer_id} not found")


def add_product_transaction(conn, product_name, price):
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO products (product_name, price)
                VALUES (%s, %s)
                RETURNING product_id;
                """,
                (product_name, price),
            )
            product_id = cur.fetchone()[0]
    return product_id


def print_current_state(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM customers ORDER BY customer_id;")
        customers = cur.fetchall()
        cur.execute("SELECT * FROM products ORDER BY product_id;")
        products = cur.fetchall()
        cur.execute("SELECT * FROM orders ORDER BY order_id;")
        orders = cur.fetchall()
        cur.execute("SELECT * FROM order_items ORDER BY order_item_id;")
        order_items = cur.fetchall()

    print("\nCustomers:")
    for row in customers:
        print(row)

    print("\nProducts:")
    for row in products:
        print(row)

    print("\nOrders:")
    for row in orders:
        print(row)

    print("\nOrderItems:")
    for row in order_items:
        print(row)


def main():
    conn = get_connection()
    try:
        create_tables(conn)
        seed_data(conn)

        print("Scenario 1: place order")
        order_id = place_order_transaction(conn, customer_id=1, items=[(1, 1), (2, 2)])
        print(f"Order created: {order_id}")

        print("\nScenario 2: update customer email")
        update_customer_email_transaction(conn, customer_id=1, new_email="Lara.new@kvartir.net")
        print("Email updated")

        print("\nScenario 3: add new product")
        new_product_id = add_product_transaction(conn, "Headphones", Decimal("150.00"))
        print(f"New product created: {new_product_id}")

        print_current_state(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
