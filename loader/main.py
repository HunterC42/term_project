import os
import pandas as pd
from transform import clean
from load import load_data

DATA_DIR = os.getenv("DATA_DIR", ".")
CSV_PATH = os.path.join(DATA_DIR, "Chicago-crimes.csv")

# Read code-like columns as text so values like IUCR "0560" keep their leading zero
TEXT_COLUMNS = {
    "case_number": str,
    "block": str,
    "iucr": str,
    "fbi_code": str,
    "primary_type": str,
    "description": str,
    "location_description": str,
}


def main():
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"{CSV_PATH} not found - the extract step must run first")

    df = pd.read_csv(CSV_PATH, dtype=TEXT_COLUMNS)
    print(f"Read {len(df)} rows from {CSV_PATH}")

    df = clean(df)
    print(f"{len(df)} rows after transform")

    load_data(df)
    print("Transform + load completed successfully!")


if __name__ == "__main__":
    main()