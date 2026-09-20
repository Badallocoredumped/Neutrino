"""
EPİAŞ Data Repository
Handles PostgreSQL operations for EPİAŞ consumption data
"""

import os
import psycopg2
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import logging

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EPIASDataRepository:
    """Repository for EPİAŞ consumption data operations with PostgreSQL"""
    
    def __init__(self):
        """Initialize PostgreSQL connection"""
        self.pg_conn = None
        self.connect()
    
    def connect(self):
        """Establish connection to PostgreSQL database"""
        try:
            self.pg_conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST") or os.getenv("POSTGRES_HOST_DEV", "localhost"),
                database=os.getenv("POSTGRES_DB") or os.getenv("POSTGRES_DB_DEV"),
                user=os.getenv("POSTGRES_USER") or os.getenv("POSTGRES_USER_DEV"),
                password=os.getenv("POSTGRES_PASSWORD") or os.getenv("POSTGRES_PASSWORD_DEV"),
                port=os.getenv("POSTGRES_PORT", 5432)
            )
            self.pg_conn.autocommit = True
            print(f"✅ Connected to PostgreSQL: {os.getenv('POSTGRES_DB_DEV') or os.getenv('POSTGRES_DB')}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
            raise e
    
    @staticmethod
    def _deduplicate_records(df):
        """Drop duplicate records from an incoming consumption DataFrame."""
        deduped = df.copy()
        deduped["_date"] = deduped["datetime"].dt.date
        deduped = deduped.drop_duplicates(subset=["_date"]).drop(columns=["_date"])
        return deduped.reset_index(drop=True)

    def save_consumption_data(self, consumption_df):
        """Save consumption data to epias_power_consumption table with smart upsert"""
        if consumption_df.empty:
            print("⚠️ No EPİAŞ consumption data to save")
            return False

        consumption_df = self._deduplicate_records(consumption_df)

        try:
            cursor = self.pg_conn.cursor()

            # Calculate time range for summary
            min_datetime = consumption_df["datetime"].min()
            max_datetime = consumption_df["datetime"].max()
            
            print("")
            print(f"🔄 Processing {len(consumption_df)} total EPİAŞ consumption records...")
            print(f"   📊 Total EPİAŞ records to process: {len(consumption_df)}")
            print(f"   📅 Time range: {min_datetime} → {max_datetime}")
            print(f"🔄 Processing {len(consumption_df)} EPİAŞ records for smart upsert...")
            
            inserted_count = 0
            updated_count = 0
            skipped_count = 0
            
            for idx, row in consumption_df.iterrows():
                # Handle timezone-aware datetime properly
                datetime_obj = row["datetime"]
                
                # Convert to string for PostgreSQL - let psycopg2 handle the timezone
                if hasattr(datetime_obj, 'isoformat'):
                    datetime_str = datetime_obj.isoformat()
                else:
                    dt = pd.to_datetime(datetime_obj)
                    datetime_str = dt.isoformat()
                
                # Format datetime for display (consistent with MongoDB style)
                if hasattr(datetime_obj, 'strftime'):
                    display_datetime = datetime_obj.strftime('%Y-%m-%dT%H:%M:%S.000Z')
                else:
                    dt = pd.to_datetime(datetime_obj)
                    display_datetime = dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
                
                consumption_mwh = float(row["consumption_mwh"])
                
                # Use PostgreSQL UPSERT (INSERT ... ON CONFLICT)
                upsert_sql = """
                    INSERT INTO epias_power_consumption (datetime, consumption_mwh, created_at, updated_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (datetime) 
                    DO UPDATE SET 
                        consumption_mwh = EXCLUDED.consumption_mwh,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE epias_power_consumption.consumption_mwh != EXCLUDED.consumption_mwh
                    RETURNING (xmax = 0) AS inserted
                """
                
                cursor.execute(upsert_sql, (datetime_str, consumption_mwh))
                result = cursor.fetchone()
                
                if result and result[0]:  # INSERT
                    inserted_count += 1
                    print(f"  ✅ INSERTED: {display_datetime}")
                elif result:  # UPDATE
                    updated_count += 1
                    print(f"  🔄 UPDATED: {display_datetime}")
                else:  # SKIP (identical data)
                    skipped_count += 1
                    print(f"  ⚪ SKIPPED (identical): {display_datetime}")
            
            # Show final summary
            print(f"✅ EPİAŞ consumption data complete - Inserted: {inserted_count}, Updated: {updated_count}, Skipped: {skipped_count}")
            
            # Get total count in database
            cursor.execute("SELECT COUNT(*) FROM epias_power_consumption")
            total_count = cursor.fetchone()[0]
            print(f"📊 Total EPİAŞ consumption records in database: {total_count}")
            
            cursor.close()
            logger.info(f"✅ Successfully processed {len(consumption_df)} EPİAŞ consumption records")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving EPİAŞ consumption data: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_consumption_data_by_date_range(self, start_date, end_date):
        """
        Retrieve consumption data for a date range
        
        Args:
            start_date (datetime): Start date
            end_date (datetime): End date
            
        Returns:
            pd.DataFrame: Consumption data
        """
        try:
            query = """
                SELECT datetime, consumption_mwh, created_at, updated_at
                FROM epias_power_consumption
                WHERE datetime >= %s AND datetime <= %s
                ORDER BY datetime
            """
            
            df = pd.read_sql_query(
                query, 
                self.pg_conn, 
                params=[start_date, end_date]
            )
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Error retrieving consumption data: {e}")
            return pd.DataFrame()
    
    def get_latest_consumption_data(self, limit=24):
        """
        Get the latest consumption records
        
        Args:
            limit (int): Number of records to retrieve
            
        Returns:
            pd.DataFrame: Latest consumption data
        """
        try:
            query = """
                SELECT datetime, consumption_mwh, created_at, updated_at
                FROM epias_power_consumption
                ORDER BY datetime DESC
                LIMIT %s
            """
            
            df = pd.read_sql_query(query, self.pg_conn, params=[limit])
            return df
            
        except Exception as e:
            logger.error(f"❌ Error retrieving latest consumption data: {e}")
            return pd.DataFrame()
    
    def close(self):
        """Close database connection"""
        if self.pg_conn:
            self.pg_conn.close()
            print("🔌 Disconnected from PostgreSQL")


# Test function
def test_repository():
    """Test the EPİAŞ data repository"""
    try:
        repo = EPIASDataRepository()
        
        # Test getting latest data
        latest = repo.get_latest_consumption_data(limit=5)
        print(f"📊 Latest 5 EPİAŞ records:")
        print(latest)
        
        repo.close()
        return True
        
    except Exception as e:
        print(f"❌ Repository test failed: {e}")
        return False


if __name__ == "__main__":
    test_repository()