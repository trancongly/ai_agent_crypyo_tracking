import sqlite3

from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
SELECT *
FROM snapshots
ORDER BY id DESC
LIMIT 1
""")

snapshot = cur.fetchone()

cur.execute("""
SELECT lesson
FROM market_journal
ORDER BY id DESC
LIMIT 10
""")

lessons = cur.fetchall()

memory = "\n".join(
    [x[0] for x in lessons]
)

prompt = f"""
You are a crypto trading analyst.

Latest market snapshot:

{snapshot}

Long term memory:

{memory}

Predict next 4h movement.

Return JSON:
{{
 "direction":"UP/DOWN",
 "confidence":0.0,
 "setup":"..."
}}
"""

with open("latest_prompt.txt","w") as f:
    f.write(prompt)

print("Prompt generated")
