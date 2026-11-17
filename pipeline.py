import pandas as pd
from transform import remove_na, dtype_conv
from load import load_data

df = pd.read_csv("Chicago-crimes.csv")
df = remove_na(df)
df = dtype_conv(df)

load_data(df)

print("Pipeline completed successfully!")