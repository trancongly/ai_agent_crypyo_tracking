import sqlite3
import json
import time

from google import genai

from config import *

client = genai.Client(api_key=GEMINI_API_KEY)

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

def get_snapshots(symbol):
    data = {}
    for tf in TIMEFRAMES:
        cur.execute("""
        SELECT *
        FROM snapshots
        WHERE symbol=?
        AND timeframe=?
        ORDER BY id DESC
        LIMIT 30
        """, (symbol, tf))
        data[tf] = cur.fetchall()
    return data

def build_features(rows):

    if len(rows) < 10:
        return "INSUFFICIENT_DATA"

    rsis = [float(r[5]) for r in rows]
    vols = [float(r[6]) for r in rows]

    latest = rows[0]

    current_price = float(latest[4])
    current_rsi = rsis[0]

    rsi_slope_5 = (rsis[0] - rsis[4]) / 5
    rsi_slope_10 = (rsis[0] - rsis[9]) / 10

    avg_volume = sum(vols) / len(vols)

    volume_ratio = vols[0] / avg_volume if avg_volume > 0 else 1
    volume_slope_5 = (vols[0] - vols[4]) / 5

    if volume_ratio > 1.5 and volume_slope_5 > 0:
        volume_trend = "strong_inflow"
    elif volume_ratio > 1.0 and volume_slope_5 > 0:
        volume_trend = "inflow"
    elif volume_ratio < 0.8 and volume_slope_5 < 0:
        volume_trend = "outflow"
    else:
        volume_trend = "neutral"

    bb_upper = float(latest[7])
    bb_mid = float(latest[8])
    bb_lower = float(latest[9])

    bbw = ((bb_upper - bb_lower) / bb_mid) * 100

    old = rows[4]

    old_bbw = (
        (float(old[7]) - float(old[9]))
        / float(old[8])
        * 100
    )

    if bbw > old_bbw * 1.05:
        bbw_trend = "expanding"
    elif bbw < old_bbw * 0.95:
        bbw_trend = "contracting"
    else:
        bbw_trend = "flat"

    if bb_upper != bb_lower:
        bb_position = (
            (current_price - bb_lower)
            / (bb_upper - bb_lower)
            * 100
        )
        bb_position = max(0, min(100, bb_position))
    else:
        bb_position = 50

    return f"""
RSI={current_rsi:.2f}
RSI_Slope_5={rsi_slope_5:.2f}
RSI_Slope_10={rsi_slope_10:.2f}

Volume_Ratio={volume_ratio:.2f}
Volume_Slope_5={volume_slope_5:.0f}
Volume_Trend={volume_trend}

BBW={bbw:.2f}
BBW_Trend={bbw_trend}

BB_Position={bb_position:.0f}
"""

for symbol in SYMBOLS:

    try:

        snapshot_data = get_snapshots(symbol)

        data_by_tf = {}

        for tf in ["1d", "4h", "1h"]:
            rows = snapshot_data.get(tf, [])
            data_by_tf[tf] = build_features(rows)

        if snapshot_data.get("1h"):
            current_price = round(snapshot_data["1h"][0][4], 6)
        else:
            current_price = "Unknown"

        prompt = f"""
You are an expert crypto trader.

Symbol={symbol}

1D
{data_by_tf["1d"]}

4H
{data_by_tf["4h"]}

1H
{data_by_tf["1h"]}

Current_Price={current_price}

Interpretation:

RSI:
- below 30 = oversold
- above 70 = overbought

RSI_Slope:
- positive = bullish momentum
- negative = bearish momentum

Volume_Ratio:
- >1 means above average volume
- >1.5 means significant volume

Volume_Trend:
- strong_inflow
- inflow
- neutral
- outflow

BBW_Trend:
- expanding = volatility increasing
- contracting = volatility decreasing

BB_Position:
- near 100 = near upper band
- near 0 = near lower band

Tasks:

1. Predict next 4h direction.
2. Identify nearest resistance.
3. Identify nearest support.

Return ONLY valid JSON:

{{
    "probability": 0,
    "direction": "bullish",
    "resistance": 0,
    "support": 0
}}
"""

        print(f"{prompt}")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=""
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
        VALUES(
            datetime('now'),
            ?,
            '4h',
            ?,
            ?,
            ?,
            ?,
            'pending'
        )
        """, (
            symbol,
            float(data["probability"]),
            str(data["direction"]),
            float(data["resistance"]),
            float(data["support"])
        ))

        conn.commit()

        print(f"{symbol}: {data['direction']} {data['probability']}%")

        time.sleep(5)

    except Exception as e:
        print(f"{symbol}: {e}")

conn.close()

print("Predictor finished")
