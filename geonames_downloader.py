"""
GeoNames Data Downloader and Database Builder
Downloads geographic names from GeoNames.org and builds a SQLite database
"""

import urllib.request
import zipfile
import os
import sqlite3
from typing import List, Tuple

# GeoNames file format (tab-separated):
# 0: geonameid
# 1: name
# 2: asciiname
# 3: alternatenames (comma separated)
# 4: latitude
# 5: longitude
# 6: feature class
# 7: feature code
# 8: country code
# 9: cc2
# 10: admin1 code
# 11: admin2 code
# 12: admin3 code
# 13: admin4 code
# 14: population
# 15: elevation
# 16: dem
# 17: timezone
# 18: modification date

class GeoNamesDownloader:
    def __init__(self, db_path: str = "geonames.db"):
        self.db_path = db_path
        self.base_url = "https://download.geonames.org/export/dump/"
        
    def download_file(self, filename: str, output_dir: str = "data") -> str:
        """Download a file from GeoNames"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        url = self.base_url + filename
        output_path = os.path.join(output_dir, filename)
        
        if os.path.exists(output_path.replace('.zip', '.txt')):
            print(f"{filename} already downloaded and extracted")
            return output_path.replace('.zip', '.txt')
        
        print(f"Downloading {filename}...")
        urllib.request.urlretrieve(url, output_path)
        print(f"Downloaded to {output_path}")
        
        if filename.endswith('.zip'):
            print(f"Extracting {filename}...")
            with zipfile.ZipFile(output_path, 'r') as zip_ref:
                zip_ref.extractall(output_dir)
            extracted_file = output_path.replace('.zip', '.txt')
            print(f"Extracted to {extracted_file}")
            return extracted_file
        
        return output_path
    
    def download_feature_codes(self) -> str:
        """Download feature codes reference"""
        return self.download_file("featureCodes_en.txt")
    
    def download_countries_data(self, countries: List[str] = None) -> List[str]:
        """
        Download data for specific countries
        countries: List of 2-letter country codes (e.g., ['US', 'GB', 'FR'])
        If None, downloads allCountries.zip (large file, 1.4GB uncompressed)
        """
        if countries is None:
            print("Downloading all countries (this may take a while)...")
            return [self.download_file("allCountries.zip")]
        
        files = []
        for country in countries:
            filename = f"{country}.zip"
            files.append(self.download_file(filename))
        return files
    
    def create_database(self):
        """Create SQLite database with proper schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main geographic names table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS geonames (
                geonameid INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                asciiname TEXT,
                alternatenames TEXT,
                latitude REAL,
                longitude REAL,
                feature_class TEXT,
                feature_code TEXT,
                country_code TEXT,
                admin1_code TEXT,
                admin2_code TEXT,
                population INTEGER,
                elevation INTEGER,
                timezone TEXT
            )
        """)
        
        # Index for fast name lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_name ON geonames(name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_asciiname ON geonames(asciiname)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feature_class ON geonames(feature_class)
        """)
        
        # Feature codes reference table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feature_codes (
                code TEXT PRIMARY KEY,
                name TEXT,
                description TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        print(f"Database created at {self.db_path}")
    
    def import_feature_codes(self, file_path: str):
        """Import feature codes into database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    code = parts[0]
                    name = parts[1]
                    description = parts[2] if len(parts) > 2 else ""
                    cursor.execute("""
                        INSERT OR REPLACE INTO feature_codes (code, name, description)
                        VALUES (?, ?, ?)
                    """, (code, name, description))
        
        conn.commit()
        conn.close()
        print("Feature codes imported")
    
    def import_geonames_file(self, file_path: str, batch_size: int = 10000):
        """Import GeoNames data file into database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        batch = []
        count = 0
        
        print(f"Importing {file_path}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) < 19:
                    continue
                
                try:
                    record = (
                        int(parts[0]),  # geonameid
                        parts[1],       # name
                        parts[2],       # asciiname
                        parts[3],       # alternatenames
                        float(parts[4]) if parts[4] else None,  # latitude
                        float(parts[5]) if parts[5] else None,  # longitude
                        parts[6],       # feature_class
                        parts[7],       # feature_code
                        parts[8],       # country_code
                        parts[10],      # admin1_code
                        parts[11],      # admin2_code
                        int(parts[14]) if parts[14] else 0,  # population
                        int(parts[15]) if parts[15] else None,  # elevation
                        parts[17]       # timezone
                    )
                    batch.append(record)
                    count += 1
                    
                    if len(batch) >= batch_size:
                        cursor.executemany("""
                            INSERT OR REPLACE INTO geonames 
                            (geonameid, name, asciiname, alternatenames, latitude, longitude,
                             feature_class, feature_code, country_code, admin1_code, admin2_code,
                             population, elevation, timezone)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, batch)
                        conn.commit()
                        batch = []
                        if count % 100000 == 0:
                            print(f"  Imported {count:,} records...")
                
                except (ValueError, IndexError) as e:
                    continue
        
        if batch:
            cursor.executemany("""
                INSERT OR REPLACE INTO geonames 
                (geonameid, name, asciiname, alternatenames, latitude, longitude,
                 feature_class, feature_code, country_code, admin1_code, admin2_code,
                 population, elevation, timezone)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            conn.commit()
        
        conn.close()
        print(f"Import complete. Total records: {count:,}")
    
    def setup_complete_database(self, countries: List[str] = None):
        """Complete setup: download, create database, and import data"""
        # Create database
        self.create_database()
        
        # Download and import feature codes
        feature_codes_file = self.download_feature_codes()
        self.import_feature_codes(feature_codes_file)
        
        # Download and import geographic data
        data_files = self.download_countries_data(countries)
        for file_path in data_files:
            self.import_geonames_file(file_path)
        
        print("\nDatabase setup complete!")
        print(f"Database location: {os.path.abspath(self.db_path)}")


def main():
    """
    Example usage
    """
    downloader = GeoNamesDownloader("geonames.db")
    
    # Option 1: Download specific countries (smaller, faster)
    # US, UK, Canada, Australia
    print("Setting up GeoNames database...")
    print("This will download data for US, GB, CA, AU")
    print("For all countries, pass None instead of country list")
    
    downloader.setup_complete_database(['US', 'GB', 'CA', 'AU'])
    
    # Option 2: Download all countries (large file)
    # downloader.setup_complete_database(None)


if __name__ == "__main__":
    main()
