"""
Hotspot Predictor - ML model for predicting next-24h waste accumulation per ward.
Member 5 (Research & Analytics Lead) owns this file.

Model: GradientBoostingRegressor
Features: temporal, spatial, historical scan patterns
Target: predicted scan count in next 24 hours per ward
"""

import os
import pickle
import numpy as np
import pandas as pd
from typing import List, Optional


FEATURE_COLUMNS = [
    "day_of_week",       # 0=Mon, 6=Sun
    "hour_of_day",       # 0-23
    "week_of_year",      # 1-52
    "is_weekend",        # 0/1
    "scan_count_24h",    # scans in last 24h in ward
    "scan_count_7d",     # scans in last 7 days in ward
    "avg_urgency_7d",    # average urgency score last 7 days
    "pct_hazardous_7d",  # % hazardous waste scans last 7d
    "festival_proximity",# days to next major Indian festival (0-30)
]

MODEL_PATH = "ml-models/analytics/hotspot_model.pkl"
SCALER_PATH = "ml-models/analytics/hotspot_scaler.pkl"


class HotspotPredictor:
    def __init__(self):
        self.model = None
        self.scaler = None
        self._load_or_init()

    def _load_or_init(self):
        try:
            from sklearn.ensemble import GradientBoostingRegressor
            from sklearn.preprocessing import StandardScaler

            if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
                with open(MODEL_PATH, "rb") as f:
                    self.model = pickle.load(f)
                with open(SCALER_PATH, "rb") as f:
                    self.scaler = pickle.load(f)
            else:
                self.model = GradientBoostingRegressor(
                    n_estimators=200,
                    max_depth=4,
                    learning_rate=0.05,
                    subsample=0.8,
                    random_state=42,
                )
                self.scaler = StandardScaler()
        except ImportError:
            pass

    def fit(self, X: pd.DataFrame, y: pd.Series):
        X_scaled = self.scaler.fit_transform(X[FEATURE_COLUMNS])
        self.model.fit(X_scaled, y)
        self._save()

    def predict(self, X: pd.DataFrame) -> List[float]:
        if self.model is None:
            return [float(X.get("scan_count_24h", 5).iloc[0])] * len(X)
        try:
            X_scaled = self.scaler.transform(X[FEATURE_COLUMNS])
            preds = self.model.predict(X_scaled)
            return [max(0.0, float(p)) for p in preds]
        except Exception:
            return [5.0] * len(X)

    def _save(self):
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(self.model, f)
        with open(SCALER_PATH, "wb") as f:
            pickle.dump(self.scaler, f)


_predictor: Optional[HotspotPredictor] = None


def get_predictor() -> HotspotPredictor:
    global _predictor
    if _predictor is None:
        _predictor = HotspotPredictor()
    return _predictor


def predict_hotspots(ward_features: List[dict]) -> List[dict]:
    """
    ward_features: list of {ward_number, city, lat, lon, + feature columns}
    Returns list of {ward_number, city, lat, lon, predicted_count, urgency_level}
    """
    if not ward_features:
        return []

    predictor = get_predictor()
    df = pd.DataFrame(ward_features)

    # Fill missing feature columns with defaults
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0

    predictions = predictor.predict(df)

    results = []
    for i, row in df.iterrows():
        pred = predictions[i]
        if pred < 5:
            level = "low"
        elif pred < 15:
            level = "medium"
        elif pred < 30:
            level = "high"
        else:
            level = "critical"
        results.append({
            "ward_number": row.get("ward_number", "unknown"),
            "city": row.get("city", "unknown"),
            "predicted_count": round(pred, 1),
            "urgency_level": level,
            "latitude": row.get("lat"),
            "longitude": row.get("lon"),
        })

    return sorted(results, key=lambda x: x["predicted_count"], reverse=True)
