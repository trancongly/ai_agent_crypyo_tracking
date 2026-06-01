import sqlite3
import requests

from config import *

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

msg = ""

for symbol in SYMBOLS:

    cur.execute("""
    SELECT
    probability,
    direction,
    resistance,
    support
    FROM predictions
    WHERE symbol=?
    ORDER BY id DESC
    LIMIT 1
    """,(symbol,))

    p = cur.fetchone()

    if not p:
        continue

    cur.execute("""
    SELECT
    COUNT(*),
    SUM(
    CASE
    WHEN status='success'
    THEN 1
    ELSE 0
    END
    )
    FROM predictions
    WHERE symbol=?
    """,(symbol,))

    stats = cur.fetchone()

    total = stats[0] or 0
    wins = stats[1] or 0

    accuracy = 0

    if total:
        accuracy = wins / total * 100

    msg += f"""
{symbol}

Direction: {p[1]}
Probability: {p[0]}%

Resistance: {p[2]}
Support: {p[3]}

Model Accuracy:
{accuracy:.1f}%

------------------
"""

r = requests.post(
    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
    data={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg
    }
)

conn.close()

print(r.status_code)
print(r.text)
