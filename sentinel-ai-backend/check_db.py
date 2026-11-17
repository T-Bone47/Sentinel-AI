import sqlite3
import os

db_path = 'sentinel.db'
if not os.path.exists(db_path):
    print('DB not found')
    exit()

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cur.fetchall()

reps = {
    'â€”': '—',
    'Â·': '·',
    'â€™': '’',
    'â€œ': '“',
    'â€': '”',
    'â€¦': '…',
    'Ã—': '×',
    'âŒ˜': '⌘'
}

found = False
for table in tables:
    table_name = table[0]
    cur.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cur.fetchall() if col[2] in ('TEXT', 'VARCHAR', 'STRING')]
    
    for col in columns:
        for bad_char, good_char in reps.items():
            cur.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {col} LIKE ?", ('%' + bad_char + '%',))
            count = cur.fetchone()[0]
            if count > 0:
                print(f"Fixing {count} instances in {table_name}.{col}")
                cur.execute(f"UPDATE {table_name} SET {col} = REPLACE({col}, ?, ?)", (bad_char, good_char))
                found = True

if found:
    conn.commit()
    print("Fixed mojibake in DB")
else:
    print("No mojibake found in DB")

conn.close()
