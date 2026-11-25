import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")

def connect_db():
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )
    return conn


def get_loaded_updates(conn):
    with conn.cursor() as cursor:
        cursor.execute("SELECT crime_id, updated_on FROM fact_crime")
        return dict(cursor.fetchall())


def create_tables(conn):
    with open(SCHEMA_PATH, "r") as file:
        schema = file.read()

    with conn.cursor() as cursor:
        cursor.execute(schema)

    conn.commit()
    print("PostgreSQL tables created successfully!")
    
    
def validate_data(df):
    df = df.copy()

    df = df.drop(columns=["Unnamed: 0", "location"], errors="ignore")

    integer_columns = [
        "id", "beat", "district", "ward",
        "community_area", "year"
    ]

    for col in integer_columns:
        df[col] = pd.to_numeric(df[col], errors="raise").astype("Int64")


    df["date"] = pd.to_datetime(df["date"], errors="raise")
    df["updated_on"] = pd.to_datetime(df["updated_on"], errors="raise")

    coordinate_columns = [
        "latitude", "longitude"
    ]

    for col in coordinate_columns:
        df[col] = pd.to_numeric(df[col], errors="raise")

    for col in ["arrest", "domestic"]:
        if not df[col].dropna().isin([True, False]).all():
            raise ValueError(f"Invalid boolean values in {col}")
        df[col] = df[col].astype("boolean")

    if df["id"].isna().any():
        raise ValueError("Crime ID cannot be missing")

    print("Data types validated successfully!")
    return df


def load_crime_types(conn, df):
    crime_types = df[
        ["iucr", "primary_type", "description", "fbi_code"]
    ].drop_duplicates(subset=["iucr"])

    with conn.cursor() as cursor:
        for _, row in crime_types.iterrows():
            cursor.execute("""
                INSERT INTO dim_crime_type
                    (iucr, primary_type, description, fbi_code)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (iucr)
                DO UPDATE SET
                    primary_type = EXCLUDED.primary_type,
                    description = EXCLUDED.description,
                    fbi_code = EXCLUDED.fbi_code
            """, (
                row["iucr"],
                row["primary_type"],
                row["description"],
                row["fbi_code"]
            ))

    conn.commit()
    print("Crime types loaded successfully!")
    
    
def load_dates(conn, df):

    dates = pd.to_datetime(df["date"]).dt.normalize().drop_duplicates()

    with conn.cursor() as cursor:
        for date in dates:
            cursor.execute("""
                INSERT INTO dim_date
                    (date_key, year, quarter, month, day, day_of_week)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (date_key)
                DO UPDATE SET
                    year = EXCLUDED.year,
                    quarter = EXCLUDED.quarter,
                    month = EXCLUDED.month,
                    day = EXCLUDED.day,
                    day_of_week = EXCLUDED.day_of_week
            """, (
                date.date(),
                int(date.year),
                int(date.quarter),
                int(date.month),
                int(date.day),
                int(date.dayofweek) + 1
            ))

    conn.commit()
    print("Dates loaded successfully!")


def get_location_key(row):
    columns = [
        "block", "location_description", "beat",
        "district", "ward", "community_area",
        "latitude", "longitude"
    ]

    return tuple(
        None if pd.isna(row[col]) else
        row[col].item() if hasattr(row[col], "item") else row[col]
        for col in columns
    )

def load_locations(conn, df):
    location_columns = [
        "block", "location_description", "beat",
        "district", "ward", "community_area",
        "latitude", "longitude"
    ]

    locations = df[location_columns].drop_duplicates().copy()
    location_keys = {}

    with conn.cursor() as cursor:
        for row in locations.itertuples(index=False, name=None):
            values = tuple(
                None if pd.isna(value) else
                value.item() if hasattr(value, "item") else value
                for value in row
            )

            cursor.execute("""
                INSERT INTO dim_location (
                    block, location_description, beat,
                    district, ward, community_area,
                    latitude, longitude
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (
                    block, location_description, beat,
                    district, ward, community_area,
                    latitude, longitude
                )
                DO UPDATE SET
                    block = EXCLUDED.block
                RETURNING location_key
            """, values)

            location_keys[get_location_key(dict(zip(location_columns, row)))] = cursor.fetchone()[0]


    conn.commit()
    print("Locations loaded successfully!")
    return location_keys



def load_crimes(conn, df, location_keys):
    with conn.cursor() as cursor:
        for row in df.to_dict("records"):
            location = get_location_key(row)


            cursor.execute("""
                SELECT crime_type_key
                FROM dim_crime_type
                WHERE iucr = %s
            """, (row["iucr"],))
            result = cursor.fetchone()

            if result is None:
                raise ValueError(f"Missing crime type: {row['iucr']}")

            crime_type_key = result[0]

            cursor.execute("""
                INSERT INTO fact_crime (
                    crime_id, case_number, occurred_at,
                    updated_on, date_key, location_key,
                    crime_type_key, arrest, domestic
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (crime_id) DO UPDATE SET
                    case_number = EXCLUDED.case_number,
                    occurred_at = EXCLUDED.occurred_at,
                    updated_on = EXCLUDED.updated_on,
                    date_key = EXCLUDED.date_key,
                    location_key = EXCLUDED.location_key,
                    crime_type_key = EXCLUDED.crime_type_key,
                    arrest = EXCLUDED.arrest,
                    domestic = EXCLUDED.domestic
            """, (
                int(row["id"]),
                row["case_number"],
                row["date"],
                row["updated_on"],
                pd.Timestamp(row["date"]).date(),

                location_keys[location],
                crime_type_key,
                bool(row["arrest"]),
                bool(row["domestic"])
            ))

    conn.commit()
    print("Crime records loaded successfully!")


def load_data(df):
    conn = connect_db()

    try:
        create_tables(conn)

        loaded_updates = get_loaded_updates(conn)
        df = df.copy()
        df["updated_on_dt"] = pd.to_datetime(df["updated_on"])
        df["stored_updated_on"] = pd.to_datetime(df["id"].map(loaded_updates))

        is_new = df["stored_updated_on"].isna()
        is_changed = df["updated_on_dt"] > df["stored_updated_on"]
        df = df[is_new | is_changed].drop(columns=["updated_on_dt", "stored_updated_on"])

        print(f"Already loaded: {len(loaded_updates)} | New/updated rows to load: {len(df)}")

        if df.empty:
            print("No new or updated rows to load.")
            return

        df = validate_data(df)
        df = df.astype(object).where(pd.notna(df), None)

        load_crime_types(conn, df)
        load_dates(conn, df)
        location_keys = load_locations(conn, df)
        load_crimes(conn, df, location_keys)

        print("All crime data loaded successfully!")

    finally:
        conn.close()



if __name__ == "__main__":
    print("Load functions are ready for testing.")


