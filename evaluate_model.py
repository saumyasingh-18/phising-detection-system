from urllib.parse import urlsplit

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import GroupShuffleSplit, train_test_split

from backend.feature_extractor import FEATURE_NAMES, extract_features
from ml.utils import MODEL_PATH, load_training_data_from_raw


def _build_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    rows = df["url"].apply(extract_features).tolist()
    return pd.DataFrame(rows, columns=FEATURE_NAMES)


def _hostname(url: str) -> str:
    try:
        return (urlsplit(str(url)).hostname or "").lower().strip()
    except Exception:
        return ""


def _print_metrics(name: str, y_true, y_pred) -> None:
    print(f"{name}")
    print(f"Accuracy: {accuracy_score(y_true, y_pred):.4f}")
    print(classification_report(y_true, y_pred))


def evaluate_random_split(model, X, y) -> None:
    _, X_test, _, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    y_pred = model.predict(X_test)
    _print_metrics("Random Split Evaluation", y_test, y_pred)


def evaluate_unseen_domain_split(model, X, y, urls) -> None:
    groups = pd.Series(urls).map(_hostname)

    # If we cannot form meaningful groups, skip gracefully.
    if groups.nunique() < 2:
        print("Unseen Domain Evaluation")
        print("Skipped: not enough distinct hostnames for grouped split.")
        return

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y, groups))

    X_test = X.iloc[test_idx]
    y_test = y.iloc[test_idx]

    y_pred = model.predict(X_test)
    _print_metrics("Unseen Domain Evaluation", y_test, y_pred)


def main() -> None:
    # Use cleaned raw dataset (before balancing) for realistic evaluation.
    df = load_training_data_from_raw()

    X = _build_feature_frame(df)
    y = df["label"]

    model = joblib.load(MODEL_PATH)

    evaluate_random_split(model, X, y)
    evaluate_unseen_domain_split(model, X, y, df["url"])


if __name__ == "__main__":
    main()
