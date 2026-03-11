import os
import psycopg2
from psycopg2 import sql

DATABASE_URL = "https://tolxnswlfybzwvewtpeo.supabase.co"

def delete_all_tables():
    conn = None

    try:
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is not set.")

        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        cursor = conn.cursor()

        # Fetch all table names in public schema
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE';
        """)

        tables = cursor.fetchall()

        if not tables:
            print("No tables found in public schema.")
            return

        for (table_name,) in tables:
            try:
                cursor.execute(
                    sql.SQL("DROP TABLE {} CASCADE").format(
                        sql.Identifier(table_name)
                    )
                )
                print(f"Dropped table: {table_name}")
            except Exception as e:
                print(f"Error dropping table {table_name}: {e}")

        conn.commit()
        print("\nAll tables deleted successfully.")

    except Exception as e:
        print("Database error:", e)

    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    delete_all_tables()