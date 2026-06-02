import sqlite3
import json
import time

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

# get snapshots by timeframe

def get_snapshots(symbol):
    data ={}

    for tf in TIMEFRAMES:
        cur.execute("""
        SELECT * 
        FROM snapshots
        WHERE symbol=? AND timeframe=?
        ORDER BY id DESC
        LIMIT 30
        """, (symbol, tf))

        rows = cur.fetchall()

        data[tf] = rows
    return data

#loop
for symbol in SYMBOLS:

    snapshot_data = get_snapshots(symbol)

    prompt = f"""
You are an expert crypto trader using multiple timeframe analysis.
Market snapshots (group by timeframe):

{json.dumps(snapshot_data, indent=2)}

Instructions:
- Determine overall trend from 1d timeframe
- Refine struct using 4h timeframe
- Predict short-term movement on 1h timeframe
- Identify nearest resistance and support
- Do not explain any thing

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

        time.sleep(60)

        print(f"{symbol}: prediction saved")

    except Exception as e:
        print(f"{symbol}: {e}")

conn.commit()
conn.close()

print("Predictor finished")
