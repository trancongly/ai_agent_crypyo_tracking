import numpy as np
import joblib

# ==============================================================================
# PIVOT DETECTION
# ==============================================================================
def find_pivots(series, left=2, right=2):
    highs = []
    lows = []
    
    for i in range(left, len(series) - right):
        window = series[i-left:i+right+1]
        center = series[i]
        
        if center == max(window):
            highs.append((i, center))
        if center == min(window):
            lows.append((i, center))
            
    return highs, lows


# ==============================================================================
# FEATURE EXTRACTION (IMPROVED)
# ==============================================================================
def extract_features(close, rsi):
    close = np.array(close)
    rsi = np.array(rsi)
    
    # Detect pivots
    price_highs, price_lows = find_pivots(close)
    rsi_highs, rsi_lows = find_pivots(rsi)
    
    features = []
    
    # ==========================================================================
    # BULLISH SIDE (LOWS)
    # ==========================================================================
    if len(price_lows) >= 2 and len(rsi_lows) >= 2:
        (i1, p1), (i2, p2) = price_lows[-2:]
        (j1, r1), (j2, r2) = rsi_lows[-2:]
        
        # Structure
        price_delta_low = p2 - p1
        rsi_delta_low = r2 - r1
        
        features += [
            price_delta_low,
            rsi_delta_low,
            int(p2 < p1),   # lower low
            int(r2 > r1),   # higher low RSI
            i2 - i1,        # time distance
        ]
    else:
        features += [0, 0, 0, 0, 0]
        
    # ==========================================================================
    # BEARISH SIDE (HIGHS)
    # ==========================================================================
    if len(price_highs) >= 2 and len(rsi_highs) >= 2:
        (i1, p1), (i2, p2) = price_highs[-2:]
        (j1, r1), (j2, r2) = rsi_highs[-2:]
        
        price_delta_high = p2 - p1
        rsi_delta_high = r2 - r1
        
        features += [
            price_delta_high,
            rsi_delta_high,
            int(p2 > p1),   # higher high
            int(r2 < r1),   # lower high RSI
            i2 - i1,
        ]
    else:
        features += [0, 0, 0, 0, 0]
        
    # ==========================================================================
    # CONTEXT FEATURES
    # ==========================================================================
    if len(close) >= 20:
        trend = close[-1] - close[-20]
    else:
        trend = close[-1] - close[0]
        
    if len(rsi) >= 14:
        rsi_min = np.min(rsi[-14:])
        rsi_max = np.max(rsi[-14:])
    else:
        rsi_min = np.min(rsi)
        rsi_max = np.max(rsi)
        
    # slope
    if len(close) >= 5:
        price_slope = (close[-1] - close[-5]) / 5
        rsi_slope = (rsi[-1] - rsi[-5]) / 5
    else:
        price_slope = 0
        rsi_slope = 0
        
    features += [
        trend,
        rsi_min,
        rsi_max,
        price_slope,
        rsi_slope,
    ]
    
    return features


# ==============================================================================
# LOAD MODEL
# ==============================================================================
model = None
try:
    model = joblib.load("divergence_model.pkl")
except Exception:
    model = None


# ==============================================================================
# ML DIVERGENCE PREDICTION
# ==============================================================================
def ml_divergence(close, rsi):
    if model is None:
        return "none"
        
    try:
        feat = extract_features(close, rsi)
        pred = model.predict([feat])[0]
        
        mapping = {
            0: "bullish_divergence",
            1: "bearish_divergence",
            2: "none"
        }
        
        return mapping.get(pred, "none")
        
    except Exception:
        return "none"

#===========================
# RSI Features
#===========
def calculate_rsi_features(rsi, lookback=14):
    """
    Calculate RSI features for LLM market-state analysis.

    Parameters
    ----------
    rsi : array-like
        RSI series (oldest -> newest)
    lookback : int
        Window size for volatility/range statistics

    Returns
    -------
    dict
    """

    rsi = np.asarray(rsi, dtype=float)

    if len(rsi) < max(lookback, 11):
        raise ValueError(
            f"RSI series must contain at least {max(lookback, 11)} values"
        )

    recent = rsi[-lookback:]

    # Current RSI
    current_rsi = float(rsi[-1])

    # RSI slopes
    rsi_slope_5 = float(rsi[-1] - rsi[-6])
    rsi_slope_10 = float(rsi[-1] - rsi[-11])

    # Acceleration
    recent_slope = rsi[-1] - rsi[-3]
    old_slope = rsi[-4] - rsi[-6]
    rsi_acceleration = float(recent_slope - old_slope)

    # Volatility
    rsi_std_14 = float(np.std(recent))

    # Range
    rsi_range_14 = float(np.max(recent) - np.min(recent))

    # Above-50 ratio
    above_50_ratio = float(np.mean(recent > 50))

    # Direction consistency
    changes = np.diff(recent)

    if len(changes) == 0:
        direction_consistency = 0.0
    else:
        up_count = np.sum(changes > 0)
        down_count = np.sum(changes < 0)

        direction_consistency = float(
            max(up_count, down_count) / len(changes)
        )

    # State classification
    if current_rsi >= 70:
        state = "overbought"
    elif current_rsi <= 30:
        state = "oversold"
    elif current_rsi > 55:
        state = "bull_zone"
    elif current_rsi < 45:
        state = "bear_zone"
    else:
        state = "neutral"

    return {
        "current_rsi": round(current_rsi, 2),
        "rsi_slope_5": round(rsi_slope_5, 2),
        "rsi_slope_10": round(rsi_slope_10, 2),
        "rsi_acceleration": round(rsi_acceleration, 2),
        "rsi_std_14": round(rsi_std_14, 2),
        "rsi_range_14": round(rsi_range_14, 2),
        "above_50_ratio": round(above_50_ratio, 2),
        "direction_consistency": round(direction_consistency, 2),
        "state": state,
    }
