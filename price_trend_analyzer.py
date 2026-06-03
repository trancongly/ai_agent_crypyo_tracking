from datetime import datetime, timezone, timedelta


def calculate_market_structure(
    df,
    rsi,
    lookback=30,
    timezone_offset=7
):
    """
    Calculate market structure metrics.

    Args:
        df: DataFrame with columns:
            time, open, high, low, close, volume

        rsi: RSI Series aligned with df index

        lookback: Number of candles to analyze

        timezone_offset: Timezone offset in hours

    Returns:
        dict
    """

    recent = df.tail(lookback).copy()
    recent_rsi = rsi.tail(lookback).copy()

    for col in ["open", "high", "low", "close", "volume"]:
        recent[col] = recent[col].astype(float)

    # Find high and low points

    high_idx = recent["high"].idxmax()
    low_idx = recent["low"].idxmin()

    high_price = float(recent.loc[high_idx, "high"])
    low_price = float(recent.loc[low_idx, "low"])

    # Convert timestamps

    tz = timezone(timedelta(hours=timezone_offset))

    high_time = datetime.fromtimestamp(
        int(recent.loc[high_idx, "time"]) / 1000,
        tz=tz
    ).strftime("%Y-%m-%d")

    low_time = datetime.fromtimestamp(
        int(recent.loc[low_idx, "time"]) / 1000,
        tz=tz
    ).strftime("%Y-%m-%d")

    # Relative positions

    high_pos = recent.index.get_loc(high_idx)
    low_pos = recent.index.get_loc(low_idx)

    # Current values

    current_close = float(recent["close"].iloc[-1])
    current_volume = float(recent["volume"].iloc[-1])
    current_rsi = float(recent_rsi.iloc[-1])

    # Direction

    if low_pos < high_pos:
        direction = "low_to_high"
    else:
        direction = "high_to_low"

    # Time structure

    bars_between_high_low = abs(high_pos - low_pos)

    days_since_high = len(recent) - 1 - high_pos
    days_since_low = len(recent) - 1 - low_pos

    # Range

    range_pct = (
        (high_price - low_price)
        / low_price
        * 100
    )

    # Current position inside range

    if high_price > low_price:
        price_position_30d = (
            (current_close - low_price)
            / (high_price - low_price)
        )
    else:
        price_position_30d = 0.0

    # Distance metrics

    distance_from_high_pct = (
        (high_price - current_close)
        / high_price
        * 100
    )

    distance_from_low_pct = (
        (current_close - low_price)
        / low_price
        * 100
    )

    # RSI structure

    high_rsi = float(recent_rsi.loc[high_idx])
    low_rsi = float(recent_rsi.loc[low_idx])

    # Volume structure

    high_volume = float(recent.loc[high_idx, "volume"])
    low_volume = float(recent.loc[low_idx, "volume"])

    return {

        # Price structure

        "high_price": round(high_price, 8),
        "high_time": high_time,

        "low_price": round(low_price, 8),
        "low_time": low_time,

        "current_close": round(current_close, 8),

        "direction": direction,

        "bars_between_high_low":
            int(bars_between_high_low),

        "days_since_high":
            int(days_since_high),

        "days_since_low":
            int(days_since_low),

        "range_pct":
            round(float(range_pct), 2),

        "price_position_30d":
            round(float(price_position_30d), 4),

        "distance_from_high_pct":
            round(float(distance_from_high_pct), 2),

        "distance_from_low_pct":
            round(float(distance_from_low_pct), 2),

        # RSI structure

        "high_rsi":
            round(high_rsi, 2),

        "low_rsi":
            round(low_rsi, 2),

        "current_rsi":
            round(current_rsi, 2),

        # Volume structure

        "high_volume":
            int(high_volume),

        "low_volume":
            int(low_volume),

        "current_volume":
            int(current_volume)
    }
