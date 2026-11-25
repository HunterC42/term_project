import pandas as pd
import requests
import os
import time

url = os.getenv("url")
app_token = os.getenv("app_token")
default_cutoff = "2026-01-01T00:00:00.000"
output_csv = os.path.join(os.path.dirname(__file__), "..", "data", "Chicago-crimes.csv")
output_json = os.path.join(os.path.dirname(__file__), "..", "data", "chiraq-crimes.json")

def get_last_extracted_date(path=output_csv, default=default_cutoff):
    if not os.path.exists(path):
        return default
    existing = pd.read_csv(path, usecols=["updated_on"])
    if existing.empty:
        return default
    return existing["updated_on"].max()

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
    last_updated, last_id = None, None

    while True:
        where = f"updated_on >= '{cutoff_date}'"
        if last_updated is not None:
            where += f" AND (updated_on < '{last_updated}' OR (updated_on = '{last_updated}' AND id < '{last_id}'))"

        params = {
            "$where": where,
            "$order": "updated_on DESC, id DESC",
            "$limit": 1000,
            "$$app_token": app_token,
        }

        resp = get_with_retry(params)
        resp.raise_for_status()
        page = resp.json()
        if not page:
            break

        frames.append(pd.DataFrame(page))
        last_updated = page[-1]["updated_on"]
        last_id = page[-1]["id"]
        print(last_updated, len(frames) * 1000)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)

if __name__ == "__main__":
    cutoff_date = get_last_extracted_date()
    new_df = extract(url, app_token, cutoff_date)

    if os.path.exists(output_csv):
        existing_df = pd.read_csv(output_csv)
        new_df = pd.concat([existing_df, new_df], ignore_index=True).drop_duplicates(subset="id", keep="last")

    new_df = new_df.drop(columns=["x_coordinate", "y_coordinate"], errors="ignore")

    new_df.to_csv(output_csv, index=False)
    new_df.to_json(output_json, orient="records")
