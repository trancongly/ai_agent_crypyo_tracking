import sqlite3

from config import *
from setup_manager import update_setup

#update_setup(
#    prediction["setup"],
#    success
#)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
SELECT
id,
symbol,
resistance,
support,
direction
FROM predictions
WHERE status='pending'
""")

preds = cur.fetchall()

for pred in preds:

    pid = pred[0]
    symbol = pred[1]
    resistance = pred[2]
    support = pred[3]
    direction = pred[4]

    cur.execute("""
    SELECT price
    FROM snapshots
    WHERE symbol=?
    ORDER BY id DESC
    LIMIT 1
    """,(symbol,))

    row = cur.fetchone()

    if not row:
        continue

    current_price = row[0]

    result = "failed"

    if direction == "bullish":

        if current_price > resistance:
            result = "success"

    else:

        if current_price < support:
            result = "success"

    cur.execute("""
    UPDATE predictions
    SET status=?
    WHERE id=?
    """,(result,pid))

conn.commit()
conn.close()

print("Evaluator finished")
