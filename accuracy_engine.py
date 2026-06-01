import sqlite3
from datetime import datetime

from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS accuracy_history(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    rolling_accuracy REAL
)
""")

cur.execute("""
SELECT success
FROM evaluations
ORDER BY id DESC
LIMIT 30
""")

rows = cur.fetchall()

if rows:

    correct = sum(r[0] for r in rows)
    total = len(rows)

    accuracy = round(correct / total * 100, 2)

    cur.execute("""
    INSERT INTO accuracy_history(
        timestamp,
        rolling_accuracy
    )
    VALUES(?,?)
    """,(
        datetime.utcnow().isoformat(),
        accuracy
    ))

    conn.commit()

    print(f"Rolling accuracy={accuracy}%")
else:
    print("No evaluation data")
