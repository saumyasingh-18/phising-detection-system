from pathlib import Path
from functools import lru_cache

import joblib
import pandas as pd

try:
    from backend.feature_extractor import FEATURE_NAMES, extract_features
except ModuleNotFoundError:
    from feature_extractor import FEATURE_NAMES, extract_features


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "ml" / "hybrid_model.pkl"


@lru_cache(maxsize=1)
def get_model():
    if not MODEL_PATH.exists():
        raise RuntimeError(
            f"Model file not found at {MODEL_PATH}. Train the model before starting the API."
        )

    if MODEL_PATH.stat().st_size == 0:
        raise RuntimeError(
            f"Model file at {MODEL_PATH} is empty. Retrain the model to regenerate it."
        )

    try:
        return joblib.load(MODEL_PATH)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load model from {MODEL_PATH}. Retrain the model to repair it."
        ) from exc


def predict_url_probability(model, url: str) -> float:
    feature_row = extract_features(url)
    feature_frame = pd.DataFrame([feature_row], columns=FEATURE_NAMES)
    try:
        return float(model.predict_proba(feature_frame)[0][1])
    except Exception as exc:
        raise RuntimeError(
            "Loaded model could not score the supplied URL with feature dataframe input. "
            "Retrain the model with a compatible prediction pipeline."
        ) from exc

    raise RuntimeError("Unexpected scoring failure")
