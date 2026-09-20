"""
EPİAŞ Consumption Data Collector
Handles fetching, processing, and saving real-time consumption data from EPİAŞ API
"""

import json
import os
from datetime import datetime, timedelta
from pprint import pprint
from dotenv import load_dotenv
import requests
import pandas as pd

# Import required modules
from database.tgt_manager import TGTManager

load_dotenv(dotenv_path=".env", override=True)

class EPIASConsumptionCollector:
    """Collects real-time consumption data from EPİAŞ"""
    
    def __init__(self):
        """Initialize with TGT manager and configuration"""
        self.tgt_manager = TGTManager()
        self.consumption_url = os.getenv("REALTIME_CONSUMPTION_URL")
        
        # Headers for data requests - defined here instead of importing
        self.headers_getdata = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
    
    def get_realtime_consumption_data(self, start_date, end_date):
        """
        Get real-time consumption data with automatic TGT management and retry.

        Args:
            start_date (str): Start date in format "2024-09-10T00:00:00+03:00"
            end_date (str): End date in format "2024-09-10T23:00:00+03:00"

        Returns:
            dict: API response data or None if failed
        """
        params = {
            "startDate": start_date,
            "endDate": end_date,
            "regionCode": "TR"
        }

        while True:
            try:
                tgt = self.tgt_manager.get_valid_tgt()
                if not tgt:
                    print("❌ Failed to get valid TGT")
                    return None

                headers = self.headers_getdata.copy()
                headers["TGT"] = tgt

                print(f"📡 Requesting data from {start_date} to {end_date}")
                response = requests.post(self.consumption_url, headers=headers, json=params)
                print(f"Data request status: {response.status_code}")

                if response.status_code == 200:
                    print("✅ Successfully fetched consumption data")
                    return response.json()
                elif response.status_code == 401:
                    print("🔄 TGT expired (401), clearing cache and retrying...")
                    self.tgt_manager.clear_cache()
                else:
                    print(f"❌ Request failed: {response.status_code}")
                    return None
            except:
                pass
    
    def process_consumption_data(self, data):
        """Process EPİAŞ API response into a clean DataFrame with proper timezone"""
        if not data:
            return pd.DataFrame()
        
        try:
            

            if 'items' in data:
                consumption_list = data['items']
                df = pd.DataFrame(consumption_list)
                
                # 🔧 FIX: Handle timezone properly - don't double convert
                if 'date' in df.columns:
                    # The API already gives us dates with timezone: "2025-08-28T00:00:00+03:00"
                    # Just parse them as-is, don't convert timezone
                    df['datetime'] = pd.to_datetime(df['date'])
                    
                    # DEBUG: Show what we got
                    print(f"🔍 First datetime after parsing: {df['datetime'].iloc[0]}")
                    print(f"🔍 Timezone info: {df['datetime'].iloc[0].tzinfo}")
                
                # Rename consumption column
                if 'consumption' in df.columns:
                    df = df.rename(columns={'consumption': 'consumption_mwh'})
                
                # Keep only required columns
                columns_to_keep = [col for col in ['datetime', 'consumption_mwh'] if col in df.columns]
                if columns_to_keep:
                    df = df[columns_to_keep]
                else:
                    print(f"⚠️ DataFrame columns: {df.columns.tolist()}")
                    print("❌ Required columns missing after processing!")
                    return pd.DataFrame()
                
                # Sort by datetime
                df = df.sort_values('datetime').reset_index(drop=True)
                
                print(f"📊 Processed {len(df)} consumption records")
                print(f"📅 Date range: {df['datetime'].min()} to {df['datetime'].max()}")
                
                return df
            else:
                print("⚠️ Unexpected data structure")
                return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ Error processing consumption data: {e}")
            return pd.DataFrame()
    
    def save_consumption_to_csv(self, data, filename="consumption_data.csv"):
        """
        Save consumption data to CSV file
        
        Args:
            data (dict): Raw API response
            filename (str): Output CSV filename
        """
        if not data:
            print("No data to save")
            return
        
        try:
            # Process the data
            df = self.process_consumption_data(data)
            
            if not df.empty:
                # Save to CSV
                df.to_csv(filename, index=False, encoding='utf-8')
                print(f"✅ Data saved to {filename}")
                print(f"📊 Saved {len(df)} records")
                
                # Display first few rows
                print("\nFirst 5 rows:")
                print(df.head())
                
                return df
            else:
                print("⚠️ No data to save after processing")
                
        except Exception as e:
            print(f"❌ Error saving to CSV: {e}")
            # Fallback: save as JSON
            json_filename = filename.replace('.csv', '.json')
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"📄 Data saved as JSON instead: {json_filename}")
    
    def get_tgt_status(self):
        """Get current TGT status"""
        return self.tgt_manager.get_tgt_status()
    
    def save_consumption_to_database(self, data):
        """
        Save consumption data to PostgreSQL database
        
        Args:
            data (dict): Raw API response
            
        Returns:
            bool: Success status
        """
        try:
            # Process the data first
            df = self.process_consumption_data(data)
            
            if df.empty:
                print("⚠️ No data to save to database")
                return False
            
            # Import and initialize repository
            from .epias_data_repository import EPIASDataRepository  # Local import to avoid circular dependency
            
            repo = EPIASDataRepository()
            success = repo.save_consumption_data(df)
            repo.close()
            
            if success:
                print(f"✅ Successfully saved {len(df)} records to database")
                return True
            else:
                print("❌ Failed to save data to database")
                return False
                
        except Exception as e:
            print(f"❌ Error saving to database: {e}")
            import traceback
            traceback.print_exc()
            return False

    def collect_and_save_consumption_data(self, start_date, end_date, save_to_csv=True, save_to_db=True, csv_directory=None):
        """
        Complete workflow: fetch, transform, and save consumption data
        
        Args:
            start_date (str): Start date in ISO format
            end_date (str): End date in ISO format  
            save_to_csv (bool): Whether to save CSV file
            save_to_db (bool): Whether to save to database
            csv_directory (str): Directory to save CSV files (optional)
        
        Returns:
            pd.DataFrame: Processed consumption data
        """
        print(f"🚀 Starting EPİAŞ data collection for {start_date} to {end_date}")
        
        # Fetch data from API
        raw_data = self.get_realtime_consumption_data(start_date, end_date)
        
        if not raw_data:
            print("❌ Failed to fetch data from API")
            return pd.DataFrame()
        
        # Process data
        df = self.process_consumption_data(raw_data)
        
        if df.empty:
            print("❌ No data after processing")
            return df
        
        # Show statistics from API response
        if 'statistics' in raw_data:
            stats = raw_data['statistics']
            print(f"\n📊 API Statistics:")
            print(f"  Total Consumption: {stats.get('consumptionTotal', 0):,.2f} MWh")
            print(f"  Average: {stats.get('consumptionAvg', 0):,.2f} MWh")
            print(f"  Min: {stats.get('consumptionMin', 0):,.2f} MWh")
            print(f"  Max: {stats.get('consumptionMax', 0):,.2f} MWh")
        
        # Save to CSV if requested
        if save_to_csv and not df.empty:
            # Use custom directory if provided
            if csv_directory:
                csv_filename = os.path.join(csv_directory, f"epias_consumption_{start_date[:10].replace('-', '')}.csv")
            else:
                csv_filename = f"epias_consumption_{start_date[:10].replace('-', '')}.csv"
            
            df.to_csv(csv_filename, index=False)
            print(f"💾 CSV saved: {csv_filename}")
        
        # Save to database if requested
        if save_to_db:
            self.save_consumption_to_database(raw_data)
        
        return df


# Test function for the collector
def test_collector():
    """Test function for the EPİAŞ consumption collector"""
    collector = EPIASConsumptionCollector()
    
    # Test dates - get yesterday's data
    yesterday = datetime.now() - timedelta(days=1)
    start_date = yesterday.strftime("%Y-%m-%dT00:00:00+03:00")
    end_date = yesterday.strftime("%Y-%m-%dT23:00:00+03:00")
    
    print(f"🧪 Testing EPİAŞ collector for: {start_date} to {end_date}")
    
    # Test the collector
    df = collector.collect_and_save_consumption_data(
        start_date=start_date,
        end_date=end_date,
        save_to_csv=True,
        save_to_db=True
    )
    
    if not df.empty:
        print(f"✅ Test successful: {len(df)} records collected")
    else:
        print("❌ Test failed: No data collected")
    
    return df


if __name__ == "__main__":
    test_collector()