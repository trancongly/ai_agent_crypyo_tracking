import sqlite3
import requests
import pandas as pd
import pandas_ta as ta
from datetime import datetime, UTC

from config import *

from price_trend_analyzer import calculate_market_structure

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS snapshots(
id INTEGER PRIMARY KEY,
timestamp TEXT,
symbol TEXT,
timeframe TEXT,
price REAL,
rsi REAL,
volume REAL,
bb_upper REAL,
bb_mid REAL,
bb_lower REAL
)
""")

def get_data(symbol, interval):

    url = "https://api.binance.com/api/v3/klines"

    r = requests.get(
        url,
        params={
            "symbol": symbol,
            "interval": interval,
            "limit": 100
        }
    )

    df = pd.DataFrame(r.json())

    df = df.iloc[:, :6]

    df.columns = [
        "time",
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]

    for c in ["open","high","low","close","volume"]:
        df[c] = df[c].astype(float)
    #print(df)
    return df


for symbol in SYMBOLS:

    for tf in TIMEFRAMES:

        df = get_data(symbol, tf)
        features = calculate_market_structure(df)

        print(features)

        bb = ta.bbands(df["close"])
        rsi = ta.rsi(df["close"], length=6)

        bb_upper_col = next(c for c in bb.columns if c.startswith("BBU_"))
        bb_mid_col   = next(c for c in bb.columns if c.startswith("BBM_"))
        bb_lower_col = next(c for c in bb.columns if c.startswith("BBL_"))

        df["rsi"] = rsi
        df["bb_upper"] = bb[bb_upper_col]
        df["bb_mid"] = bb[bb_mid_col]
        df["bb_lower"] = bb[bb_lower_col]

        for index, row in df.iterrows():
            
            if pd.isna(row["rsi"]) or pd.isna(row["bb_upper"]):
                continue

            candle_timestamp = datetime.fromtimestamp(row["time"] / 1000, tz=UTC).isoformat()

            cur.execute("""
                INSERT INTO snapshots(
                    timestamp,
                    symbol,
                    timeframe,
                    price,
                    rsi,
                    volume,
                    bb_upper,
                    bb_mid,
                    bb_lower
                )
                VALUES(?,?,?,?,?,?,?,?,?)
                """, (
                    candle_timestamp,
                    symbol,
                    tf,
                    float(row["close"]),
                    float(row["rsi"]),
                    float(row["volume"]),
                    float(row["bb_upper"]),
                    float(row["bb_mid"]),
                    float(row["bb_lower"])
                ))

conn.commit()
conn.close()

print("Collector finished")
