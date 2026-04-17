import joblib
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from backend.feature_extractor import FEATURE_NAMES, extract_features
from ml.utils import MODEL_PATH, prepare_training_dataset, load_prepared_training_dataset


def load_hybrid_training_data() -> pd.DataFrame:
    """Load cleaned and balanced training data prepared from raw files."""
    return load_prepared_training_dataset()


def build_hybrid_model() -> StackingClassifier:
    rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=24,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )

    xgb = XGBClassifier(
        n_estimators=350,
        max_depth=8,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )

    lgbm = LGBMClassifier(
        n_estimators=400,
        learning_rate=0.05,
        num_leaves=63,
        subsample=0.9,
        colsample_bytree=0.9,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    meta = LogisticRegression(max_iter=2000, class_weight="balanced")

    return StackingClassifier(
        estimators=[("rf", rf), ("xgb", xgb), ("lgbm", lgbm)],
        final_estimator=meta,
        stack_method="predict_proba",
        passthrough=False,
        cv=5,
        n_jobs=-1,
    )


def main() -> None:
    prepared_path = prepare_training_dataset(balance=True, target_ratio=1.2)
    df = load_hybrid_training_data()

    rows = df["url"].apply(extract_features).tolist()
    X = pd.DataFrame(rows, columns=FEATURE_NAMES)
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = build_hybrid_model()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    print(f"Loaded {len(df)} samples")
    print("Label distribution:")
    print(df["label"].value_counts().sort_index())
    print(f"Prepared training data saved to: {prepared_path}")
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    print(classification_report(y_test, y_pred))

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"Model trained and saved successfully: {MODEL_PATH}")


if __name__ == "__main__":
    main()
