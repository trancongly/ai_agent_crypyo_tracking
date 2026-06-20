import pandas as pd


def calculate_atr_metrics(df, period=14, trend_lookback=5):
    """
    Calculate ATR metrics from OHLC data.

    Parameters
    ----------
    df : pandas.DataFrame
        Must contain: high, low, close
    period : int, default=14
        ATR calculation period.
    trend_lookback : int, default=5
        Number of bars used to determine ATR trend.

    Returns
    -------
    dict
        {
            "atr14": float,
            "atr_pct": float,
            "atr_trend": str
        }
    """

    high = df["high"]
    low = df["low"]
    close = df["close"]

    prev_close = close.shift(1)

    true_range = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    # Wilder ATR
    atr = true_range.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    current_atr = atr.iloc[-1]
    current_close = close.iloc[-1]

    atr_pct = current_atr / current_close * 100

    if len(atr) < trend_lookback + 1:
        atr_trend = "neutral"
    else:
        historical_atr = atr.iloc[-trend_lookback - 1]

        if historical_atr == 0:
            atr_trend = "neutral"
        else:
            change_pct = (
                (current_atr - historical_atr)
                / historical_atr
                * 100
            )

            if change_pct > 5:
                atr_trend = "rising"
            elif change_pct < -5:
                atr_trend = "falling"
            else:
                atr_trend = "neutral"

    return {
        "atr14": round(float(current_atr), 5),
        "atr_pct": round(float(atr_pct), 2),
        "atr_trend": atr_trend,
    }

