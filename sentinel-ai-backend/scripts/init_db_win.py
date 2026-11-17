import psycopg
from psycopg import sql

# Connect to default 'postgres' database as postgres user
try:
    with psycopg.connect("postgresql://postgres:postgres@localhost:5432/postgres", autocommit=True) as conn:
        with conn.cursor() as cur:
            # Create role 'sentinel' if it doesn't exist
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname='sentinel'")
            if not cur.fetchone():
                cur.execute("CREATE USER sentinel WITH PASSWORD 'sentinel' SUPERUSER;")
                print("Created user 'sentinel'")
            else:
                cur.execute("ALTER USER sentinel WITH PASSWORD 'sentinel';")
                print("Updated password for user 'sentinel'")

            # Create database 'sentinel_ai' if it doesn't exist
            cur.execute("SELECT 1 FROM pg_database WHERE datname='sentinel_ai'")
            if not cur.fetchone():
                cur.execute("CREATE DATABASE sentinel_ai OWNER sentinel;")
                print("Created database 'sentinel_ai'")
            else:
                print("Database 'sentinel_ai' already exists")
except Exception as e:
    print("Database init failed:", e)
