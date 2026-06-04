import sqlite3
import requests
import pandas as pd
import pandas_ta as ta
from datetime import datetime, UTC

from config import *

from rsi_features import ml_divergence
from rsi_features import calculate_rsi_features

from price_trend_analyzer import calculate_market_structure

from bb_analyzer import BollingerStructureAnalyzer

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

        rsi = ta.rsi(df["close"], length=6)
        # Market structure only on 1D
        if tf == "1d":
            market_features = calculate_market_structure(
            df=df,
            rsi=rsi,
            lookback=30
        )

            print("\n=== 1D Market Structure ===")
            print(market_features)


        if tf == "4h":
            analyzer = BollingerStructureAnalyzer()
            result = analyzer.analyze(df.tail(90))

            print("\n=== 4H BB Structure ===")
            print(result)

        if tf == "1h":
            ml_rsi = ml_divergence(df["close"], rsi)

            print("\n=== 1H RSI Structure ===")
            print(ml_rsi)   
            rsi_features = calculate_rsi_features(rsi)
            print(rsi_features)   


print("Collector finished")
