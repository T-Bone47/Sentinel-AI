import psycopg

passwords = ["postgres", "root", "admin", "123456", "password", "sentinel", "", "1234"]
users = ["postgres", "sentinel"]

found = False
for u in users:
    for p in passwords:
        try:
            conn_str = f"postgresql://{u}:{p}@localhost:5432/postgres"
            with psycopg.connect(conn_str) as conn:
                print(f"SUCCESS! Connected with user='{u}', password='{p}'")
                found = True
                break
        except Exception:
            pass
    if found:
        break

if not found:
    print("Could not connect with common passwords. PostgreSQL password is set independently on host.")
