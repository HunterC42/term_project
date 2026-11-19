import pandas as pd
import requests
import os
import time

url = os.getenv("url")
app_token = os.getenv("app_token")
default_cutoff = "2026-01-01T00:00:00.000"
output_csv = "Chicago-crimes.csv"

def get_last_extracted_date(path=output_csv, default=default_cutoff):
    if not os.path.exists(path):
        return default
    existing = pd.read_csv(path, usecols=["date"])
    if existing.empty:
        return default
    return existing["date"].max()

def get_with_retry(params, max_retries=5):
    for attempt in range(max_retries):
        resp = requests.get(url, params=params)
        if resp.status_code not in (429, 503):
            return resp
        time.sleep(2 ** attempt)
    resp.raise_for_status()
    return resp
def extract(url, app_token, cutoff_date):
    frames = []
    last_date, last_id = None, None

    while True:
        where = f"date >= '{cutoff_date}'"
        if last_date is not None:
            where += f" AND (date < '{last_date}' OR (date = '{last_date}' AND id < '{last_id}'))"

        params = {
            "$where": where,
            "$order": "date DESC, id DESC",
            "$limit": 1000,
            "$$app_token": app_token,
        }

        resp = get_with_retry(params)
        resp.raise_for_status()
        page = resp.json()
        if not page:
            break

        frames.append(pd.DataFrame(page))
        last_date = page[-1]["date"]
        last_id = page[-1]["id"]
        print(last_date, len(frames) * 1000)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)

if __name__ == "__main__":
    cutoff_date = get_last_extracted_date()
    new_df = extract(url, app_token, cutoff_date)

    if os.path.exists(output_csv):
        existing_df = pd.read_csv(output_csv)
        new_df = pd.concat([existing_df, new_df], ignore_index=True).drop_duplicates(subset="id")

    new_df.to_csv(output_csv, index=False)
    new_df.to_json("chiraq-crimes.json", orient="records")
