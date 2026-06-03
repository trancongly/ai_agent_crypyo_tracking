import sqlite3
import json
import time
import numpy as np
import joblib

from google import genai
from rsi_analyzer import check_rsi_trend
from rsi_analyzer import PivotState
from rsi_analyzer import detect_divergence
from rsi_analyzer import ml_divergence

try:
    from config import *
except ImportError:
    GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"
    DB_PATH = "crypto_data.db"
    TIMEFRAMES = ["1d", "4h", "1h"]
    SYMBOLS = ["BTCUSDT", "ETHUSDT"]

# ==========================================
# DATABASE + CLIENT
# ==========================================
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception:
    client = None

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    timeframe TEXT,
    timestamp INTEGER,
    price REAL,
    rsi REAL,
    volume REAL,
    bb_upper REAL,
    bb_mid REAL,
    bb_lower REAL
)
""")
conn.commit()

# ==========================================
# GET DATA
# ==========================================
def get_snapshots(symbol):
    data = {}
    for tf in TIMEFRAMES:
        cur.execute("""
            SELECT * FROM snapshots
            WHERE symbol=? AND timeframe=?
            ORDER BY id DESC
            LIMIT 30
        """, (symbol, tf))
        data[tf] = cur.fetchall()
    return data

# ==========================================
# FEATURE BUILD (OPTIMIZED FOR CSV)
# ==========================================
def build_features(rows):
    if not rows or len(rows) < 10:
        return None

    rsis = [float(r[5]) for r in rows]
    vols = [float(r[6]) for r in rows]
    prices = [float(r[4]) for r in rows]

    latest = rows[0]

    current_price = float(latest[4])
    rsi_trend = check_rsi_trend(rsis)
    print(rsi_trend)
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

    bbw = ((bb_upper - bb_lower) / bb_mid) * 100 if bb_mid > 0 else 0

    if bb_upper != bb_lower:
        bb_position = ((current_price - bb_lower) / (bb_upper - bb_lower)) * 100
        bb_position = max(0, min(100, bb_position))
    else:
        bb_position = 50

    csv_row = f"{current_rsi:.2f},{rsi_slope_5:.2f},{rsi_slope_10:.2f},{volume_ratio:.2f},{volume_slope_5:.0f},{volume_trend},{bbw:.2f},{bb_position:.0f}"

    return {
        "csv_row": csv_row,
        "rsi": list(reversed(rsis)),
        "price": list(reversed(prices))
    }

# ==========================================
# MAIN LOOP
# ==========================================
for symbol in SYMBOLS:
    try:
        snapshot_data = get_snapshots(symbol)
        data_by_tf = {}

        for tf in ["1d", "4h", "1h"]:
            data_by_tf[tf] = build_features(snapshot_data.get(tf, []))

        if not data_by_tf["1d"] and not data_by_tf["4h"] and not data_by_tf["1h"]:
            continue

        csv_lines = []
        for tf in ["1d", "4h", "1h"]:
            if data_by_tf[tf]:
                csv_lines.append(f"{tf.upper()},{data_by_tf[tf]['csv_row']}")
            else:
                csv_lines.append(f"{tf.upper()},,,,,,,")
        
        csv_data = "\n".join(csv_lines)

        div = "none"
        ml_div = "none"

        if data_by_tf["1h"]:
            close = np.array(data_by_tf["1h"]["price"][-50:])
            rsi = np.array(data_by_tf["1h"]["rsi"][-50:])

            price_state = PivotState()
            rsi_state = PivotState()

            price_state.update(close)
            rsi_state.update(rsi)

            div = detect_divergence(price_state, rsi_state)
            ml_div = ml_divergence(close, rsi)

        current_price = (
            round(snapshot_data["1h"][0][4], 6)
            if snapshot_data.get("1h") and len(snapshot_data["1h"]) > 0 else "Unknown"
        )

        prompt = f"""
You are an expert crypto trader. Analyze market data for {symbol} (Current Price: {current_price}).

Data (CSV):
TF,RSI,RSI_Slope5,RSI_Slope10,Vol_Ratio,Vol_Slope5,Vol_Trend,BBW,BB_Pos
{csv_data}

Divergence:
Rule-based: {div}
ML-based: {ml_div}

Tasks:
1. Predict next 4h direction.
2. Identify resistance.
3. Identify support.

Return JSON ONLY:
{{
    "probability": 0,
    "direction": "bullish",
    "resistance": 0,
    "support": 0
}}
"""
        print(prompt)
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

        time.sleep(60)

    except Exception as e:
        print(symbol, e)

conn.close()

