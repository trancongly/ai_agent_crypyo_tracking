import sqlite3
import requests
import pandas as pd
import pandas_ta as ta
from datetime import datetime, UTC

from config import *

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

    return df

for symbol in SYMBOLS:

    for tf in TIMEFRAMES:

        df = get_data(symbol, tf)

        bb = ta.bbands(df["close"])
        rsi = ta.rsi(df["close"])

        latest = df.iloc[-1]
        bb_upper_col = next(c for c in bb.columns if c.startswith("BBU_"))
        bb_mid_col   = next(c for c in bb.columns if c.startswith("BBM_"))
        bb_lower_col = next(c for c in bb.columns if c.startswith("BBL_"))

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
            """,(
                datetime.now(UTC).isoformat(),
                symbol,
                tf,
                float(latest["close"]),
                float(rsi.iloc[-1]),
                float(latest["volume"]),
                float(bb.iloc[-1][bb_upper_col]),
                float(bb.iloc[-1][bb_mid_col]),
                float(bb.iloc[-1][bb_lower_col])
            ))

conn.commit()
conn.close()

print("Collector finished")
