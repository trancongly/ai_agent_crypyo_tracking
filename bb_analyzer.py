import numpy as np
import pandas as pd
from scipy.signal import find_peaks


class BollingerStructureAnalyzer:
    """
    Input DataFrame columns:
    time, open, high, low, close, volume
    """

    def __init__(
        self,
        bb_period=20,
        bb_std=2.0,
        peak_distance=5,
        cluster_pct=0.01,
        band_tolerance=0.01,
        touch_gap=3
    ):
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.peak_distance = peak_distance
        self.cluster_pct = cluster_pct
        self.band_tolerance = band_tolerance
        self.touch_gap = touch_gap

    def _calculate_bollinger(self, df):
        bb_mid = df["close"].rolling(self.bb_period).mean()
        rolling_std = df["close"].rolling(self.bb_period).std()

        bb_upper = bb_mid + self.bb_std * rolling_std
        bb_lower = bb_mid - self.bb_std * rolling_std

        return bb_upper, bb_mid, bb_lower

    @staticmethod
    def _calculate_bbw(df):
        return ((df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]) * 100

    @staticmethod
    def _calculate_bb_position(df):
        band_range = df["bb_upper"] - df["bb_lower"]
        return (df["close"] - df["bb_lower"]) / band_range

    @staticmethod
    def _bars_ago(df, idx):
        return len(df) - idx - 1

    def _count_touch_events(self, indices):
        if len(indices) == 0:
            return 0

        indices = sorted(indices)
        events = 1

        for i in range(1, len(indices)):
            if indices[i] - indices[i - 1] > self.touch_gap:
                events += 1

        return events

    @staticmethod
    def _recency_score(last_touch_idx, total_bars):
        bars_ago = total_bars - last_touch_idx - 1
        return max(0.0, 1 - bars_ago / total_bars)

    def _cluster_price_levels(self, prices, volumes, indices):
        if len(prices) == 0:
            return []

        cluster_size = np.mean(prices) * self.cluster_pct
        clusters = []

        for price, volume, idx in zip(prices, volumes, indices):
            assigned = False

            for cluster in clusters:
                if abs(cluster["center"] - price) <= cluster_size:
                    cluster["prices"].append(price)
                    cluster["volumes"].append(volume)
                    cluster["indices"].append(idx)
                    cluster["center"] = np.mean(cluster["prices"])
                    assigned = True
                    break

            if not assigned:
                clusters.append({
                    "center": price,
                    "prices": [price],
                    "volumes": [volume],
                    "indices": [idx]
                })

        return clusters

    def _build_levels(
        self,
        clusters,
        current_price,
        avg_volume,
        total_bars,
        limit=3
    ):
        levels = []

        for cluster in clusters:
            level_price = np.mean(cluster["prices"])
            level_volume = np.mean(cluster["volumes"])

            touch_events = self._count_touch_events(cluster["indices"])

            touch_score = min(1.0, touch_events / 5.0)
            volume_score = min(1.0, level_volume / avg_volume)

            recency_score = self._recency_score(
                max(cluster["indices"]),
                total_bars
            )

            strength = (
                0.5 * touch_score +
                0.3 * volume_score +
                0.2 * recency_score
            )

            distance_pct = (
                (level_price - current_price)
                / current_price
                * 100
            )

            levels.append({
                "price": round(float(level_price), 8),
                "touch_events": int(touch_events),
                "avg_volume": round(float(level_volume), 2),
                "volume_score": round(float(volume_score), 3),
                "recency_score": round(float(recency_score), 3),
                "strength": round(float(strength), 3),
                "distance_pct": round(float(distance_pct), 2)
            })

        levels.sort(
            key=lambda x: x["strength"],
            reverse=True
        )

        return levels[:limit]

    def get_resistance_levels(self, df, limit=3):
        hits = df[
            df["high"] >=
            df["bb_upper"] * (1 - self.band_tolerance)
        ]

        if len(hits) == 0:
            return []

        clusters = self._cluster_price_levels(
            hits["high"].values,
            hits["volume"].values,
            hits.index.to_numpy()
        )

        return self._build_levels(
            clusters,
            current_price=df["close"].iloc[-1],
            avg_volume=df["volume"].mean(),
            total_bars=len(df),
            limit=limit
        )

    def get_support_levels(self, df, limit=3):
        hits = df[
            df["low"] <=
            df["bb_lower"] * (1 + self.band_tolerance)
        ]

        if len(hits) == 0:
            return []

        clusters = self._cluster_price_levels(
            hits["low"].values,
            hits["volume"].values,
            hits.index.to_numpy()
        )

        return self._build_levels(
            clusters,
            current_price=df["close"].iloc[-1],
            avg_volume=df["volume"].mean(),
            total_bars=len(df),
            limit=limit
        )

    def get_bbw_peaks(self, df, bbw, limit=5):
        peaks, _ = find_peaks(
            bbw,
            distance=self.peak_distance,
            prominence=np.std(bbw) * 0.5
        )

        result = []

        for idx in peaks[-limit:]:
            result.append({
                "price": round(float(df["close"].iloc[idx]), 8),
                "bbw": round(float(bbw.iloc[idx]), 2),
                "bars_ago": self._bars_ago(df, idx)
            })

        return result

    def get_bbw_bottoms(self, df, bbw, limit=5):
        bottoms, _ = find_peaks(
            -bbw,
            distance=self.peak_distance,
            prominence=np.std(bbw) * 0.5
        )

        result = []

        for idx in bottoms[-limit:]:
            result.append({
                "price": round(float(df["close"].iloc[idx]), 8),
                "bbw": round(float(bbw.iloc[idx]), 2),
                "bars_ago": self._bars_ago(df, idx)
            })

        return result

    @staticmethod
    def _detect_structure(values):
        if len(values) < 2:
            return "unknown"

        if values[-1] > values[-2]:
            return "higher_high"

        if values[-1] < values[-2]:
            return "lower_high"

        return "equal"

    @staticmethod
    def _volatility_state(current_bbw, percentile):
        if percentile >= 80:
            return "high_volatility"

        if percentile <= 20:
            return "squeeze"

        if current_bbw > 10:
            return "expanding"

        return "normal"

    def analyze(self, df, top_levels=3):
        df = df.copy()

        bb_upper, bb_mid, bb_lower = self._calculate_bollinger(df)

        df["bb_upper"] = bb_upper
        df["bb_mid"] = bb_mid
        df["bb_lower"] = bb_lower

        df = df.dropna().reset_index(drop=True)

        if len(df) < 30:
            raise ValueError("Not enough candles.")

        bbw = self._calculate_bbw(df)
        bb_position = self._calculate_bb_position(df)

        bbw_percentile = round(
            float(bbw.rank(pct=True).iloc[-1] * 100),
            2
        )

        supports = self.get_support_levels(df, top_levels)
        resistances = self.get_resistance_levels(df, top_levels)

        bbw_peaks = self.get_bbw_peaks(df, bbw)
        bbw_bottoms = self.get_bbw_bottoms(df, bbw)

        result = {
            "current": {
                "close": round(float(df["close"].iloc[-1]), 8),
                "bb_position": round(float(bb_position.iloc[-1]), 3),
                "bbw": round(float(bbw.iloc[-1]), 2),
                "bbw_percentile": bbw_percentile
            },
            "supports": supports,
            "resistances": resistances,
            "bbw_peaks": bbw_peaks,
            "bbw_bottoms": bbw_bottoms,
            "volatility_state": self._volatility_state(
                bbw.iloc[-1],
                bbw_percentile
            )
        }

        if len(bbw_peaks) >= 2:
            result["bbw_peak_structure"] = self._detect_structure(
                [x["bbw"] for x in bbw_peaks[-2:]]
            )

        if len(bbw_bottoms) >= 2:
            result["bbw_bottom_structure"] = self._detect_structure(
                [x["bbw"] for x in bbw_bottoms[-2:]]
            )

        return result
