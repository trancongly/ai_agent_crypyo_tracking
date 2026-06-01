import sqlite3
from datetime import datetime

from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS market_journal(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    lesson TEXT
)
""")

cur.execute("""
SELECT
    setup_name,
    wins,
    losses,
    winrate
FROM setups
ORDER BY winrate DESC
LIMIT 5
""")

rows = cur.fetchall()

for row in rows:

    lesson = (
        f"Setup={row[0]}, "
        f"Winrate={row[3]}%, "
        f"Wins={row[1]}, "
        f"Losses={row[2]}"
    )

    cur.execute("""
    INSERT INTO market_journal(
        timestamp,
        lesson
    )
    VALUES(?,?)
    """,(
        datetime.utcnow().isoformat(),
        lesson
    ))

conn.commit()

print("Journal updated")
