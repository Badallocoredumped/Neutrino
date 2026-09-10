from .mongodb_client import MongoDBClient
from datetime import datetime, timedelta
import pandas as pd

class EnergyDataRepository:
    def __init__(self):
        self.mongo_client = MongoDBClient()
        self.mongo_client.connect()
        self.mongo_client.create_indexes()
    
    def save_power_data(self, power_df):
        """Smart upsert power data - skip identical, update changed, insert new"""
        power_collection = self.mongo_client.get_collection("power_data")
        
        print(f"🔄 Processing {len(power_df)} power records for smart upsert...")
        inserted_count = 0
        updated_count = 0
        skipped_count = 0
        
        for idx, row in power_df.iterrows():
            # Standardize datetime format
            if hasattr(row["datetime"], 'isoformat'):
                datetime_str = row["datetime"].strftime("%Y-%m-%dT%H:%M:%S.000Z")
            else:
                dt = pd.to_datetime(row["datetime"])
                datetime_str = dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            
            # Create filter for datetime + zone (unique identifier)
            filter_query = {
                "datetime": datetime_str,
                "zone": row["zone"]
            }
            
            # Convert row to dict and ensure datetime is standardized
            row_dict = row.to_dict()
            row_dict["datetime"] = datetime_str
            
            # Clean up any NaN values
            for key, value in row_dict.items():
                if pd.isna(value):
                    row_dict[key] = None
            
            # Check if record already exists
            existing_record = power_collection.find_one(filter_query)
            
            if existing_record:
                # Remove MongoDB's _id for comparison
                existing_data = {k: v for k, v in existing_record.items() if k != '_id'}
                
                # Compare the data (excluding _id)
                if existing_data == row_dict:
                    # Exact same data - skip
                    skipped_count += 1
                    print(f"  ⚪ SKIPPED (identical): {datetime_str}")
                else:
                    # Different data - update
                    result = power_collection.replace_one(filter_query, row_dict)
                    if result.modified_count > 0:
                        updated_count += 1
                        print(f"  🔄 UPDATED: {datetime_str}")
            else:
                # New record - insert
                power_collection.insert_one(row_dict)
                inserted_count += 1
                print(f"  ✅ INSERTED: {datetime_str}")
                
        print(f"✅ Power data complete - Inserted: {inserted_count}, Updated: {updated_count}, Skipped: {skipped_count}")
        
        # Get total count in database
        total_count = power_collection.count_documents({})
        print(f"📊 Total power records in database: {total_count}")

    def save_carbon_data(self, carbon_df):
        """Smart upsert carbon data - skip identical, update changed, insert new"""
        carbon_collection = self.mongo_client.get_collection("carbon_intensity")
        
        print(f"🔄 Processing {len(carbon_df)} carbon records for smart upsert...")
        inserted_count = 0
        updated_count = 0
        skipped_count = 0
        
        for idx, row in carbon_df.iterrows():
            # Standardize datetime format
            if hasattr(row["datetime"], 'isoformat'):
                datetime_str = row["datetime"].strftime("%Y-%m-%dT%H:%M:%S.000Z")
            else:
                dt = pd.to_datetime(row["datetime"])
                datetime_str = dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            
            # Create filter for datetime + zone (unique identifier)
            filter_query = {
                "datetime": datetime_str,
                "zone": row["zone"]
            }
            
            # Convert row to dict and ensure datetime is standardized
            row_dict = row.to_dict()
            row_dict["datetime"] = datetime_str
            
            # Handle other datetime fields with standardization
            if "updatedAt" in row_dict and pd.notna(row_dict["updatedAt"]):
                if hasattr(row_dict["updatedAt"], 'isoformat'):
                    row_dict["updatedAt"] = row_dict["updatedAt"].strftime("%Y-%m-%dT%H:%M:%S.000Z")
                else:
                    dt = pd.to_datetime(row_dict["updatedAt"])
                    row_dict["updatedAt"] = dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                    
            if "createdAt" in row_dict and pd.notna(row_dict["createdAt"]):
                if hasattr(row_dict["createdAt"], 'isoformat'):
                    row_dict["createdAt"] = row_dict["createdAt"].strftime("%Y-%m-%dT%H:%M:%S.000Z")
                else:
                    dt = pd.to_datetime(row_dict["createdAt"])
                    row_dict["createdAt"] = dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            
            # Clean up any NaN values
            for key, value in row_dict.items():
                if pd.isna(value):
                    row_dict[key] = None
            
            # Check if record already exists
            existing_record = carbon_collection.find_one(filter_query)
            
            if existing_record:
                # Remove MongoDB's _id for comparison
                existing_data = {k: v for k, v in existing_record.items() if k != '_id'}
                
                # Compare the data (excluding _id)
                if existing_data == row_dict:
                    # Exact same data - skip
                    skipped_count += 1
                    print(f"  ⚪ SKIPPED (identical): {datetime_str}")
                else:
                    # Different data - update
                    result = carbon_collection.replace_one(filter_query, row_dict)
                    if result.modified_count > 0:
                        updated_count += 1
                        print(f"  🔄 UPDATED: {datetime_str}")
            else:
                # New record - insert
                carbon_collection.insert_one(row_dict)
                inserted_count += 1
                print(f"  ✅ INSERTED: {datetime_str}")
                
        print(f"✅ Carbon data complete - Inserted: {inserted_count}, Updated: {updated_count}, Skipped: {skipped_count}")
        
        # Get total count in database
        total_count = carbon_collection.count_documents({})
        print(f"📊 Total carbon records in database: {total_count}")
    
    def get_latest_power_data(self, hours=24):
        """Get power data from last N hours"""
        return self.mongo_client.find_latest_records("power_data", limit=hours)
    
    def get_latest_carbon_data(self, hours=24):
        """Get carbon data from last N hours"""
        return self.mongo_client.find_latest_records("carbon_intensity", limit=hours)
    
    def get_power_data_by_zone(self, zone, start_date, end_date):
        """Get power data for specific zone and date range"""
        collection = self.mongo_client.get_collection("power_data")
        query = {
            "zone": zone,
            "datetime": {"$gte": start_date, "$lte": end_date}
        }
        return list(collection.find(query).sort("datetime", 1))

    def get_daily_consumption_summary(self, start_date, end_date):
        """Return total and average EPİAŞ consumption for each calendar day."""
        start = datetime.fromisoformat(str(start_date).replace("Z", "+00:00")).date()
        end = datetime.fromisoformat(str(end_date).replace("Z", "+00:00")).date()
        if start > end:
            raise ValueError("start_date must be before or equal to end_date")

        collection = self.mongo_client.get_collection("epias_consumption")
        records = collection.find({
            "datetime": {
                "$gte": start.isoformat(),
                "$lt": (end + timedelta(days=1)).isoformat()
            }
        }).sort("datetime", 1)

        df = pd.DataFrame(list(records))
        if df.empty:
            return pd.DataFrame(columns=["date", "total_consumption", "average_consumption"])

        df["date"] = df["datetime"].map(
            lambda value: datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
        )
        df["consumption_mwh"] = pd.to_numeric(df["consumption_mwh"])
        summary = (
            df.groupby("date", as_index=False)["consumption_mwh"]
            .agg(total_consumption="sum", average_consumption="mean")
        )
        return summary
    
    def get_carbon_summary_stats(self, zone=None):
        """Get carbon intensity summary statistics"""
        collection = self.mongo_client.get_collection("carbon_intensity")
        
        pipeline = []
        if zone:
            pipeline.append({"$match": {"zone": zone}})
        
        pipeline.extend([
            {
                "$group": {
                    "_id": "$zone",
                    "avg_carbon_intensity": {"$avg": "$carbonIntensity"},
                    "min_carbon_intensity": {"$min": "$carbonIntensity"},
                    "max_carbon_intensity": {"$max": "$carbonIntensity"},
                    "count": {"$sum": 1}
                }
            }
        ])
        
        return list(collection.aggregate(pipeline))
    
    def close(self):
        """Close database connections"""
        self.mongo_client.disconnect()