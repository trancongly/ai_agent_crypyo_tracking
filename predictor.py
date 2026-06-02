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


# loop
for symbol in SYMBOLS:

    snapshot_data = get_snapshots(symbol)

    data_by_tf = {}
    for tf in ["1d", "4h", "1h"]:
        rows = snapshot_data.get(tf, [])
        
        csv_lines = ["rsi,volume,bb_upper,bb_mid,bb_lower"]
        
        for row in rows:
            rsi      = round(row[5], 2)
            volume   = round(row[6], 2)
            bb_upper = round(row[7], 4)
            bb_mid   = round(row[8], 4)
            bb_lower = round(row[9], 4)
            
            line = f"{rsi},{volume},{bb_upper},{bb_mid},{bb_lower}"
            csv_lines.append(line)
        
        data_by_tf[tf] = "\n".join(csv_lines)

    if snapshot_data.get("1h"):
        current_price = round(snapshot_data["1h"][0][4], 4)
    else:
        current_price = "Unknown"

    prompt = f"""
    You are an expert crypto trader. Analyze the following rsi, volume, Bollinger band data in 1d time frame
{data_by_tf["1d"]}
4h time frame 
{data_by_tf["4h"]}
1h time frame 
{data_by_tf["1h"]}

Data order is DESC.

Current price is 
{current_price}

Instructions:
- Predict short-term movement direction.
- Identify the nearest key resistance and support levels.

- Do not explain any thing.

Return ONLY valid JSON:
{{
  "probability": 60,
  "direction": "bullish",
  "resistance": 0,
  "support": 0
}}"""

    print(f"{prompt}")
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        text = response.text.strip()
        text = text.replace("```json", "").replace("```", "").strip()

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
        VALUES(datetime('now'), ?, '4h', ?, ?, ?, ?, 'pending')
        """, (
            symbol,
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
