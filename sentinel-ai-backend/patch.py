import sqlite3

conn = sqlite3.connect('sentinel.db')
conn.execute('PRAGMA writable_schema = 1')
tables = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table'").fetchall()
for name, sql in tables:
    if sql and 'now()' in sql:
        new_sql = sql.replace('now()', 'CURRENT_TIMESTAMP')
        conn.execute("UPDATE sqlite_master SET sql = ? WHERE type = 'table' AND name = ?", (new_sql, name))
conn.commit()
conn.execute('PRAGMA writable_schema = 0')
conn.close()
