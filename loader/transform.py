import pandas as pd


def drop_duplicate_ids(df):
    """Defensive guard: extractor pagination overlap (date tie at page boundary) can
    occasionally repeat a row across runs."""
    before = len(df)
    df = df.drop_duplicates(subset="id")
    print(f"Duplicate ids removed: {before - len(df)}")
    return df


def drop_unknown_locations(df):
    """Source marks unresolved locations with block='...UNKNOWN AVE', ward=0,
    district=61, beat=6100, community_area=0 — sentinel placeholders, not real
    wards/districts/areas. District 31 (airport unit) is legitimate and untouched."""
    before = len(df)
    df = df[df["district"] != 61]
    print(f"Unknown-location rows removed: {before - len(df)}")
    return df


def remove_na(df, subset=None):
    before = len(df)
    df = df.dropna(subset=subset)
    print(f"Rows with missing values removed: {before - len(df)}")
    return df


def drop_redundant_columns(df):
    """`location` duplicates latitude/longitude as a dict; `Unnamed: 0` is a stray
    CSV row-index column."""
    return df.drop(columns=["location", "Unnamed: 0"], errors="ignore")


def convert_dtypes(df):
    df["date"] = pd.to_datetime(df["date"])
    df["updated_on"] = pd.to_datetime(df["updated_on"])
    df["community_area"] = df["community_area"].astype(int)
    df["ward"] = df["ward"].astype(int)
    df["district"] = df["district"].astype(int)
    df["beat"] = df["beat"].astype(int)
    return df


def add_date_parts(df):
    """Derived columns needed for Q4 (crime patterns over time by region)."""
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    df["day"] = df["date"].dt.day
    df["day_of_week"] = df["date"].dt.dayofweek  # Monday = 0
    df["hour"] = df["date"].dt.hour
    return df


def clean(df):
    """Full transform pipeline, in order: dedupe -> drop sentinel/unusable rows ->
    drop redundant columns -> fix dtypes -> derive date parts."""
    df = drop_duplicate_ids(df)
    df = drop_unknown_locations(df)
    df = remove_na(df, subset=["latitude", "longitude", "community_area"])
    df = drop_redundant_columns(df)
    df = convert_dtypes(df)
    df = add_date_parts(df)
    return df
