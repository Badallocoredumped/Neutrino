"""
EPİAŞ Energy Consumption Data - Main Execution Script
Imports and uses the EPİAŞ consumption collector class
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

# Import the collector class
from database.epias_consumption_manager import EPIASConsumptionCollector
from database.energy_data_repository import EnergyDataRepository

load_dotenv(dotenv_path=".env", override=True)

def ensure_epias_directory():
    """Ensure the epias directory exists"""
    epias_dir = "./data/epias"
    if not os.path.exists(epias_dir):
        os.makedirs(epias_dir)
        print(f"📁 Created directory: {epias_dir}")
    return epias_dir

def main():
    """Main function for testing consumption data collection"""
    print("🚀 Starting EPİAŞ consumption data collection...")
    
    # Ensure epias directory exists
    epias_dir = ensure_epias_directory()
    
    # Initialize collector
    collector = EPIASConsumptionCollector()
    
    # Show TGT status
    status = collector.get_tgt_status()
    print(f"📊 TGT Status: {status}")
    
    # Test dates - get yesterday's data
    yesterday = datetime.now() - timedelta(days=1)
    start_date = yesterday.strftime("%Y-%m-%dT00:00:00+03:00")
    end_date = yesterday.strftime("%Y-%m-%dT23:00:00+03:00")
    
    print(f"🗓️ Fetching data for: {yesterday.strftime('%Y-%m-%d')}")
    print(f"   From: {start_date}")
    print(f"   To:   {end_date}")
    
    # Use the complete workflow with custom CSV path
    df = collector.collect_and_save_consumption_data(
        start_date=start_date,
        end_date=end_date,
        save_to_csv=True,
        save_to_db=True,
        csv_directory=epias_dir  # Save to epias folder
    )
    
    if not df.empty:
        print(f"\n📈 Final Data Summary:")
        print(f"Records: {len(df)}")
        print(f"Date range: {df['datetime'].min()} to {df['datetime'].max()}")
        print(f"Avg consumption: {df['consumption_mwh'].mean():.2f} MWh")
        print(f"Min consumption: {df['consumption_mwh'].min():.2f} MWh")
        print(f"Max consumption: {df['consumption_mwh'].max():.2f} MWh")
        
        # Show hourly pattern
        print(f"\n🕐 Hourly Pattern (sample):")
        df['hour'] = df['datetime'].dt.hour
        hourly_avg = df.groupby('hour')['consumption_mwh'].mean()
        for hour in [0, 6, 12, 18, 23]:
            if hour in hourly_avg.index:
                print(f"  {hour:02d}:00 - {hourly_avg[hour]:.2f} MWh")
                
        print(f"\n✅ EPİAŞ data collection completed successfully!")
        print(f"📂 CSV files saved to: {os.path.abspath(epias_dir)}")
    else:
        print("❌ No data collected")
    
    # Show final TGT status
    final_status = collector.get_tgt_status()
    print(f"\n📊 Final TGT Status: {final_status}")

def collect_custom_date_range(start_date_str, end_date_str):
    """
    Collect data for a custom date range
    
    Args:
        start_date_str (str): Start date in YYYY-MM-DD format
        end_date_str (str): End date in YYYY-MM-DD format
    """
    # Ensure epias directory exists
    epias_dir = ensure_epias_directory()
    
    collector = EPIASConsumptionCollector()
    
    # Convert to proper datetime format
    start_date = f"{start_date_str}T00:00:00+03:00"
    end_date = f"{end_date_str}T23:00:00+03:00"
    
    print(f"🗓️ Collecting custom date range: {start_date_str} to {end_date_str}")
    
    df = collector.collect_and_save_consumption_data(
        start_date=start_date,
        end_date=end_date,
        save_to_csv=True,
        save_to_db=True,
        csv_directory=epias_dir  # Save to epias folder
    )
    
    return df

def collect_last_n_days(days=7):
    """
    Collect data for the last N days
    
    Args:
        days (int): Number of days to collect (default: 7)
    """
    # Ensure epias directory exists
    epias_dir = ensure_epias_directory()
    
    collector = EPIASConsumptionCollector()
    
    print(f"🗓️ Collecting data for last {days} days...")
    print(f"📂 CSV files will be saved to: {os.path.abspath(epias_dir)}")
    
    for i in range(days):
        target_date = datetime.now() - timedelta(days=i+1)
        start_date = target_date.strftime("%Y-%m-%dT00:00:00+03:00")
        end_date = target_date.strftime("%Y-%m-%dT23:00:00+03:00")
        
        print(f"\n📅 Day {i+1}/{days}: {target_date.strftime('%Y-%m-%d')}")
        
        df = collector.collect_and_save_consumption_data(
            start_date=start_date,
            end_date=end_date,
            save_to_csv=True,  # Save individual CSVs for multi-day collection
            save_to_db=True,
            csv_directory=epias_dir  # Save to epias folder
        )
        
        if not df.empty:
            print(f"  ✅ Collected {len(df)} records")
            csv_filename = f"epias_consumption_{target_date.strftime('%Y%m%d')}.csv"
            print(f"  📄 Saved to: {epias_dir}/{csv_filename}")
        else:
            print(f"  ❌ Failed to collect data")
    
    print(f"\n🎉 Completed collecting {days} days of data!")
    print(f"📂 All CSV files saved to: {os.path.abspath(epias_dir)}")

def print_daily_summary(start_date, end_date):
    """Print the MongoDB EPİAŞ consumption summary for a date range."""
    repository = EnergyDataRepository()
    try:
        summary = repository.get_daily_consumption_summary(start_date, end_date)
        if summary.empty:
            print("No consumption records found.")
        else:
            print(summary.to_string(index=False))
    finally:
        repository.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--daily-summary",
        nargs=2,
        metavar=("START_DATE", "END_DATE"),
        help="Print daily EPİAŞ consumption totals and averages from MongoDB"
    )
    args = parser.parse_args()

    if args.daily_summary:
        print_daily_summary(*args.daily_summary)
    else:
        main()