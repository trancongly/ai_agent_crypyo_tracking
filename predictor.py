import sqlite3
import json

from google import genai

from config import *

# Gemini client
client = genai.Client(
    api_key=GEMINI_API_KEY
)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS predictions(
id INTEGER PRIMARY KEY,
timestamp TEXT,
symbol TEXT,
timeframe TEXT,
probability REAL,
direction TEXT,
resistance REAL,
support REAL,
status TEXT
)
""")

for symbol in SYMBOLS:

    cur.execute("""
    SELECT *
    FROM snapshots
    WHERE symbol=?
    ORDER BY id DESC
    LIMIT 10
    """,(symbol,))

    rows = cur.fetchall()

    prompt = f"""
Analyze the following crypto market snapshots:

{rows}

Return ONLY valid JSON:

{{
  "probability": 60,
  "direction": "bullish",
  "resistance": 0,
  "support": 0
}}
"""

    try:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        text = response.text.strip()

        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

        data = json.loads(text)

        cur.execute("""
        INSERT INTO predictions(
            timestamp,
            symbol,
            timeframe,
            probability,
            direction,
            resistance,
            support,
            status
        )
        VALUES(
            datetime('now'),
            ?,?,
            ?,?,?,?,
            'pending'
        )
        """,(
            symbol,
            "4h",
            float(data["probability"]),
            str(data["direction"]),
            float(data["resistance"]),
            float(data["support"])
        ))

        print(f"{symbol}: prediction saved")

    except Exception as e:
        print(f"{symbol}: {e}")

conn.commit()
conn.close()

print("Predictor finished")
