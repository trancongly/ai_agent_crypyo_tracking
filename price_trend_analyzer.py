from datetime import datetime

def calculate_market_structure(df, lookback=30):
    """
    Calculate market structure metrics from OHLCV data.

    Args:
        df: DataFrame with columns:
            time, open, high, low, close, volume
        lookback: Number of candles to analyze

    Returns:
        dict containing market structure features
    """

    recent = df.tail(lookback).copy()

    for col in ["open", "high", "low", "close", "volume"]:
        recent[col] = recent[col].astype(float)

    # High and low within lookback window
    high_idx = recent["high"].idxmax()
    low_idx = recent["low"].idxmin()

    high_price = float(recent.loc[high_idx, "high"])
    low_price = float(recent.loc[low_idx, "low"])

    high_time = datetime.fromtimestamp(
    int(recent.loc[high_idx, "time"]) / 1000
).strftime("%Y-%m-%d %H:%M:%S")

    low_time = datetime.fromtimestamp(
    int(recent.loc[low_idx, "time"]) / 1000
).strftime("%Y-%m-%d %H:%M:%S")

    # Relative positions inside lookback window
    high_pos = recent.index.get_loc(high_idx)
    low_pos = recent.index.get_loc(low_idx)

    # Current market price
    current_close = float(recent["close"].iloc[-1])

    # Market direction based on order of extreme points
    if low_pos < high_pos:
        direction = "low_to_high"
    else:
        direction = "high_to_low"

    # Number of candles between high and low
    bars_between_high_low = abs(high_pos - low_pos)

    # Number of candles since high and low occurred
    days_since_high = len(recent) - 1 - high_pos
    days_since_low = len(recent) - 1 - low_pos

    # Total price range percentage
    range_pct = (
        (high_price - low_price)
        / low_price
        * 100
    )

    # Current position inside the lookback range
    if high_price > low_price:
        price_position_30d = (
            (current_close - low_price)
            / (high_price - low_price)
        )
    else:
        price_position_30d = 0.0

    # Distance from lookback high
    distance_from_high_pct = (
        (high_price - current_close)
        / high_price
        * 100
    )

    # Distance from lookback low
    distance_from_low_pct = (
        (current_close - low_price)
        / low_price
        * 100
    )

    return {
        "high_price": round(high_price, 8),
        "high_time": high_time,

        "low_price": round(low_price, 8),
        "low_time": low_time,

        "current_close": round(current_close, 8),

        "direction": direction,

        "bars_between_high_low": int(bars_between_high_low),

        "days_since_high": int(days_since_high),
        "days_since_low": int(days_since_low),

        "range_pct": round(float(range_pct), 2),

        "price_position_30d":
            round(float(price_position_30d), 4),

        "distance_from_high_pct":
            round(float(distance_from_high_pct), 2),

        "distance_from_low_pct":
            round(float(distance_from_low_pct), 2)
    }
