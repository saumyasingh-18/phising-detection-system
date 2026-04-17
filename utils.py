from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = PROJECT_ROOT / "data" / "raw" / "data_bal - 20000.xlsx"
MODEL_PATH = PROJECT_ROOT / "ml" / "hybrid_model.pkl"
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
CLEAN_TRAINING_PATH = PROCESSED_DATA_DIR / "training_data_clean.csv"
PREPARED_TRAINING_PATH = PROCESSED_DATA_DIR / "training_data.csv"


LABEL_COLUMN_CANDIDATES = [
    "label",
    "labels",
    "type",
    "result",
    "class",
    "target",
]
URL_COLUMN_CANDIDATES = ["url", "urls"]


def _read_dataset(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"Unsupported dataset format: {path}")


def _normalize_label(value) -> int | None:
    if pd.isna(value):
        return None

    text = str(value).strip().lower()
    if text == "":
        return None

    try:
        numeric = float(text)
        if numeric in {1.0, 0.0}:
            return int(numeric)
        if numeric == -1.0:
            return 0
    except ValueError:
        pass

    phishing_tokens = {
        "1",
        "phishing",
        "phish",
        "malicious",
        "bad",
        "fraud",
        "fraudulent",
        "unsafe",
        "harmful",
    }
    legitimate_tokens = {
        "0",
        "legitimate",
        "benign",
        "safe",
        "good",
        "normal",
        "valid",
    }

    if text in phishing_tokens:
        return 1
    if text in legitimate_tokens:
        return 0

    return None


def _canonicalize_url(value: str) -> str:
    url = str(value).strip()
    if not url:
        return ""

    if "://" not in url:
        url = f"http://{url}"

    try:
        parsed = urlsplit(url)
    except ValueError:
        return ""

    scheme = parsed.scheme.lower() or "http"
    netloc = parsed.netloc.lower().strip()
    path = (parsed.path or "/").strip()
    if path != "/":
        path = path.rstrip("/")

    # Remove tracking fragments; keep query because it can be predictive.
    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def _normalize_dataset_columns(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    column_map = {str(column).strip().lower(): column for column in df.columns}

    url_column = next((column_map[c] for c in URL_COLUMN_CANDIDATES if c in column_map), None)
    label_column = next(
        (column_map[c] for c in LABEL_COLUMN_CANDIDATES if c in column_map),
        None,
    )

    if not url_column or not label_column:
        raise ValueError(
            f"{source_name}: dataset must contain URL and label columns. "
            f"Found columns: {list(df.columns)}"
        )

    normalized = df[[url_column, label_column]].rename(
        columns={url_column: "url", label_column: "label"}
    )

    normalized["label"] = normalized["label"].apply(_normalize_label)
    normalized["url"] = normalized["url"].astype(str).map(_canonicalize_url)

    normalized = normalized.dropna(subset=["url", "label"])
    normalized = normalized[normalized["url"] != ""]
    normalized["label"] = normalized["label"].astype(int)

    return normalized


def _drop_label_conflicts(df: pd.DataFrame) -> pd.DataFrame:
    # If the same URL appears with conflicting labels across datasets, keep the mode label.
    grouped = df.groupby("url")["label"].agg(lambda s: s.mode().iloc[0])
    return grouped.reset_index()


def _balance_dataset(df: pd.DataFrame, target_ratio: float = 1.2, random_state: int = 42) -> pd.DataFrame:
    """
    Balance classes by downsampling the majority class to target_ratio * minority_class.
    target_ratio=1.0 gives a fully balanced dataset.
    """
    counts = df["label"].value_counts()
    if len(counts) != 2:
        return df

    minority_label = counts.idxmin()
    majority_label = counts.idxmax()

    minority = df[df["label"] == minority_label]
    majority = df[df["label"] == majority_label]

    desired_majority = int(len(minority) * target_ratio)
    if len(majority) <= desired_majority:
        return df.sample(frac=1, random_state=random_state).reset_index(drop=True)

    majority_sampled = majority.sample(n=desired_majority, random_state=random_state)
    balanced = pd.concat([minority, majority_sampled], ignore_index=True)
    return balanced.sample(frac=1, random_state=random_state).reset_index(drop=True)


def load_training_dataset(path: Path | None = None) -> pd.DataFrame:
    dataset_path = Path(path) if path else DATASET_PATH
    df = _read_dataset(dataset_path)
    normalized = _normalize_dataset_columns(df, dataset_path.name)
    normalized = _drop_label_conflicts(normalized)
    return normalized.reset_index(drop=True)


def load_training_data_from_raw(raw_dir: Path | None = None) -> pd.DataFrame:
    """Merge all supported files from data/raw into one cleaned dataframe."""
    data_dir = Path(raw_dir) if raw_dir else RAW_DATA_DIR
    if not data_dir.exists():
        raise FileNotFoundError(f"Raw data directory does not exist: {data_dir}")

    files = sorted(
        [
            path
            for path in data_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {".csv", ".xlsx", ".xls"}
        ]
    )

    if not files:
        raise FileNotFoundError(f"No supported dataset files found in: {data_dir}")

    frames = []
    for path in files:
        df = _read_dataset(path)
        normalized = _normalize_dataset_columns(df, path.name)
        frames.append(normalized)

    merged = pd.concat(frames, ignore_index=True)
    merged = merged.dropna(subset=["url", "label"])
    merged = merged[merged["url"].astype(str).str.strip() != ""]
    merged["url"] = merged["url"].astype(str).str.strip()
    merged["label"] = merged["label"].astype(int)
    merged = _drop_label_conflicts(merged)
    return merged.reset_index(drop=True)


def prepare_training_dataset(
    output_path: Path | None = None,
    *,
    balance: bool = True,
    target_ratio: float = 1.2,
) -> Path:
    """Build, clean, optionally balance, and persist training data from all raw files."""
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    clean_data = load_training_data_from_raw()
    clean_data.to_csv(CLEAN_TRAINING_PATH, index=False)

    prepared = _balance_dataset(clean_data, target_ratio=target_ratio) if balance else clean_data

    target = Path(output_path) if output_path else PREPARED_TRAINING_PATH
    prepared.to_csv(target, index=False)
    return target


def load_prepared_training_dataset(path: Path | None = None) -> pd.DataFrame:
    dataset_path = Path(path) if path else PREPARED_TRAINING_PATH
    if not dataset_path.exists():
        prepare_training_dataset(dataset_path)
    return pd.read_csv(dataset_path)
