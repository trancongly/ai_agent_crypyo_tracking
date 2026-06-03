import numpy as np
import joblib

from config import *

# ==========================================
# FAST PIVOT
# ==========================================
def fast_pivot_low(series):
    i = len(series) - 3
    if i < 2:
        return None
    v = series[i]
    if (v < series[i-1] and v < series[i-2] and 
        v < series[i+1] and v < series[i+2]):
        return (i, v)
    return None

def fast_pivot_high(series):
    i = len(series) - 3
    if i < 2:
        return None
    v = series[i]
    if (v > series[i-1] and v > series[i-2] and 
        v > series[i+1] and v > series[i+2]):
        return (i, v)
    return None

class PivotState:
    def __init__(self):
        self.lows = []
        self.highs = []

    def update(self, series):
        pl = fast_pivot_low(series)
        ph = fast_pivot_high(series)

        if pl:
            self.lows.append(pl)
            self.lows = self.lows[-3:]

        if ph:
            self.highs.append(ph)
            self.highs = self.highs[-3:]

# ==========================================
# DIVERGENCE
# ==========================================
def detect_divergence(price_state, rsi_state):
    if len(price_state.lows) >= 2 and len(rsi_state.lows) >= 2:
        p1, p2 = price_state.lows[-2:]
        r1, r2 = rsi_state.lows[-2:]

        if p2[1] < p1[1] and r2[1] > r1[1]:
            return "bullish_divergence"
        if p2[1] > p1[1] and r2[1] < r1[1]:
            return "hidden_bullish"

    if len(price_state.highs) >= 2 and len(rsi_state.highs) >= 2:
        p1, p2 = price_state.highs[-2:]
        r1, r2 = rsi_state.highs[-2:]

        if p2[1] > p1[1] and r2[1] < r1[1]:
            return "bearish_divergence"
        if p2[1] < p1[1] and r2[1] > r1[1]:
            return "hidden_bearish"

    return "none"

# ==========================================
# ML MODEL
# ==========================================
model = None

try:
    model = joblib.load("divergence_model.pkl")
except Exception:
    model = None

def extract_features(close, rsi):
    return [
        close[-1] - close[-3],
        rsi[-1] - rsi[-3],
        min(rsi[-5:]),
        max(rsi[-5:])
    ]

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

# ======
def determine_status(rsi_current, base_trend):
    """
    Helper function to determine the final market status 
    based on the current RSI value and the underlying base trend.
    """
    # Case 1: RSI is within the neutral zone (30-70) and base trend is sideway
    if 30 <= rsi_current <= 70:
        if base_trend == "sideway":
            return "sideway"
    
    # Case 2: RSI is overbought (> 80)
    elif rsi_current > 80:
        if base_trend == "up":
            return "wait top"
        elif base_trend in ["sideway", "down"]:
            return "test top"
            
    # Case 3: RSI is oversold (< 20)
    elif rsi_current < 20:
        if base_trend == "down":
            return "wait bottom"
        elif base_trend in ["sideway", "up"]:
            return "test bottom"
            
    # Default case for any other conditions
    return "wait trend"


def check_rsi_trend(rsis):
    """
    Main function to analyze RSI volatility and trends.
    Assumes rsis[0] is the CURRENT (latest) value, rsis[1] is 1 period ago, etc.
    """
    if len(rsis) < 10:
        return "Error: RSI array must contain at least 10 elements."
    
    # Extract the latest 5 and 10 periods from the beginning of the list
    rsi_5 = rsis[:5]    # Contains rsis[0] to rsis[4]
    rsi_10 = rsis[:10]  # Contains rsis[0] to rsis[9]
    rsi_current = rsis[0]
    
    results = {}
    
    for period_name, rsi_sub in [("last_5", rsi_5), ("last_10", rsi_10)]:
        max_rsi = max(rsi_sub)
        min_rsi = min(rsi_sub)
        
        # Prevent DivisionByZero error if min_rsi is 0
        if min_rsi == 0:
            volatility = 0.0
        else:
            volatility = ((max_rsi - min_rsi) / min_rsi) * 100
        
        # 1. Determine the base trend based on 10% volatility threshold
        if volatility < 20.0:
            base_trend = "sideway"
        else:
            # Since rsi_sub[0] is current and rsi_sub[-1] is the oldest value in the window:
            # It's an uptrend if current value is higher than or equal to the oldest value
            if rsi_sub[0] >= rsi_sub[-1]:
                base_trend = "up"
            else:
                base_trend = "down"
        
        # 2. Apply advanced logic to get the final status
        final_status = determine_status(rsi_current, base_trend)
                
        # Store metrics into the results dictionary
        results[period_name] = {
            "rsi_slope": base_trend,
            "status": final_status,
            "volatility": round(volatility, 2),
            "current_rsi": rsi_current,
            "max_rsi": max_rsi,
            "min_rsi": min_rsi
        }
        
    return results

