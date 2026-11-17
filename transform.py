import ast

def remove_na(raw_df):
    ## NA Removal
    print("NA: ", raw_df.isna().sum())
    processed_df = raw_df.dropna()
    print("Raw: ",len(raw_df), "Processed: ", len(processed_df))
    print("Rows Removed: ", len(raw_df) - len(processed_df))
    return processed_df

def dtype_conv(processed_df):
    processed_df["location"] = processed_df["location"].apply(ast.literal_eval)
    processed_df["updated_on"] = pd.to_datetime(processed_df["updated_on"])
    processed_df["date"] = pd.to_datetime(processed_df["date"])



