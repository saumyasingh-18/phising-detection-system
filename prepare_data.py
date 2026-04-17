import pandas as pd

from ml.utils import CLEAN_TRAINING_PATH, PREPARED_TRAINING_PATH, prepare_training_dataset


def main() -> None:
    output_path = prepare_training_dataset(PREPARED_TRAINING_PATH, balance=True, target_ratio=1.2)
    clean_df = pd.read_csv(CLEAN_TRAINING_PATH)
    prepared_df = pd.read_csv(output_path)

    print(f"Clean dataset path: {CLEAN_TRAINING_PATH}")
    print(f"Clean rows: {len(clean_df)}")
    print("Clean label distribution:")
    print(clean_df["label"].value_counts().sort_index())

    print(f"Prepared dataset path: {output_path}")
    print(f"Prepared rows: {len(prepared_df)}")
    print("Prepared label distribution:")
    print(prepared_df["label"].value_counts().sort_index())


if __name__ == "__main__":
    main()
