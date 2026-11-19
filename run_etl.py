import os
import shutil
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault(
    "url",
    os.getenv("CHICAGO_CRIMES_URL", "https://data.cityofchicago.org/resource/ijzp-q8t2.json"),
)
if os.getenv("SOCRATA_APP_TOKEN"):
    os.environ.setdefault("app_token", os.environ["SOCRATA_APP_TOKEN"])

os.environ.setdefault("DB_HOST", os.getenv("POSTGRES_HOST", "db"))
os.environ.setdefault("DB_PORT", os.getenv("POSTGRES_PORT", "5432"))
os.environ.setdefault("DB_NAME", os.getenv("POSTGRES_DB", "chicago_crimes"))
os.environ.setdefault("DB_USER", os.getenv("POSTGRES_USER", "postgres"))
if os.getenv("POSTGRES_PASSWORD"):
    os.environ.setdefault("DB_PASSWORD", os.environ["POSTGRES_PASSWORD"])

from extract.extract import extract, get_last_extracted_date, default_cutoff
from loader.transform import clean
from loader.load import load_data


def ensure_schema_file() -> None:
    """Ensure schema.sql is available in the working directory for loader/load.py."""
    root_schema = Path("schema.sql")
    db_schema = Path("db/schema.sql")
    if not root_schema.exists() and db_schema.exists():
        shutil.copyfile(db_schema, root_schema)


def main() -> None:
    api_url = os.environ["url"]
    app_token = os.getenv("app_token") or None
    cutoff_date = os.getenv("INITIAL_MIN_DATE") or get_last_extracted_date(default=default_cutoff)

    print(f"Extracting Chicago crime records since {cutoff_date}...")
    raw_df = extract(api_url, app_token, cutoff_date)
    if raw_df.empty:
        print("No new crime records fetched.")
        return

    for col in ["district", "ward", "beat", "community_area"]:
        if col in raw_df.columns:
            raw_df[col] = pd.to_numeric(raw_df[col], errors="coerce")
    raw_df = raw_df.dropna(subset=["district", "ward", "beat", "community_area"])

    cleaned_df = clean(raw_df)
    if cleaned_df.empty:
        print("No valid crime records remaining after cleaning.")
        return

    ensure_schema_file()
    load_data(cleaned_df)


if __name__ == "__main__":
    main()