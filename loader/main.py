import os
import pandas as pd

import transform
import load

DATA_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "Chicago-crimes.csv")


def main():
    df = pd.read_csv(DATA_CSV)
    df = transform.clean(df)
    load.load_data(df)


if __name__ == "__main__":
    main()
