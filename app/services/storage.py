import pandas as pd
import os

FILE_PATH = "data/analyses.csv"

def save_analysis(email, result):
    os.makedirs("data", exist_ok=True)

    new_row = pd.DataFrame([{
        "email": email,
        "analysis": result
    }])

    if os.path.exists(FILE_PATH):
        df = pd.read_csv(FILE_PATH)
        df = pd.concat([df, new_row], ignore_index=True)
    else:
        df = new_row

    df.to_csv(FILE_PATH, index=False)