import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

from epias_data_repository import EPIASDataRepository

load_dotenv()

CSV_PATH = "Gercek_Zamanli_Tuketim-18082025-25082025.csv"  # Update path if needed

def parse_csv(csv_path):
    # Read CSV with semicolon separator and Turkish decimal comma
    df = pd.read_csv(csv_path, sep=";")
    # Rename columns to match DB
    df = df.rename(columns={
        "Tarih": "date",
        "Saat": "hour",
        "Tüketim Miktarı(MWh)": "energy_mwh"
    })
    # Convert consumption to float (replace comma with dot)
    df["energy_mwh"] = (
        df["energy_mwh"]
        .str.replace(".", "", regex=False)   # Remove thousands separator
        .str.replace(",", ".", regex=False)  # Replace decimal comma with dot
        .astype(float)
    )
    # Combine date and hour into a single datetime column
    df["datetime"] = pd.to_datetime(df["date"] + " " + df["hour"], format="%d.%m.%Y %H:%M")
    # Select only needed columns
    df = df[["datetime", "energy_mwh"]]
    return df

def main():
    df = parse_csv(CSV_PATH)
    print(f"Loaded {len(df)} records from {CSV_PATH}")
    repo = EPIASDataRepository()
    repo.save_consumption_data(df)
    repo.close()

if __name__ == "__main__":
    main()