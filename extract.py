import pandas as pd
import requests
import os
import time

url = os.getenv("url")
app_token = os.getenv("app_token")
cutoff_date = "2026-01-01T00:00:00.000"

def get_with_retry(params, max_retries=5):
    for attempt in range(max_retries):
        resp = requests.get(url, params=params)
        if resp.status_code not in (429, 503):
            return resp
        time.sleep(2 ** attempt)
    resp.raise_for_status()
    return resp

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

df = pd.concat(frames, ignore_index=True)
df.count()
df.to_csv()

df.head()
df.to_csv("Chicago-crimes.csv")
df.to_json("chiraq-crimes.json")