# collect_historical_data.py
"""
Collect 2-3 seasons of Premier League historical data for model training
"""
from api_football_collector import APIFootballCollector
from config import API_FOOTBALL_KEY, DB_PARAMS
import pandas as pd
import os
from datetime import datetime
from paths import DATA_DIR,require_dirs

def main():
    print("="*70)
    print("PREMIER LEAGUE HISTORICAL DATA COLLECTION")
    print("="*70)
    
    # Initialize collector
    collector = APIFootballCollector(API_FOOTBALL_KEY, DB_PARAMS)
    
    # Define seasons to collect (adjust based on current date)
    seasons = [2025, 2024, 2023]  # Last 3 completed seasons
    
    print(f"\nWill collect data for seasons: {seasons}")
    print(f"Estimated API calls: ~{len(seasons)} calls")
    print("\nStarting collection...")
    
    all_fixtures = []
    
    # Collect each season
    for season in seasons:
        print(f"\n{'='*70}")
        print(f"Season {season}/{season+1}")
        print(f"{'='*70}")
        
        fixtures_df = collector.get_all_fixtures_by_season(season)
        
        if not fixtures_df.empty:
            all_fixtures.append(fixtures_df)
            print(f"✓ Season {season}: {len(fixtures_df)} fixtures collected")
        else:
            print(f"✗ Season {season}: No data returned")
    
    # Combine all seasons
    if all_fixtures:
        combined_df = pd.concat(all_fixtures, ignore_index=True)
        
        print(f"\n{'='*70}")
        print("COLLECTION SUMMARY")
        print(f"{'='*70}")
        print(f"Total fixtures collected: {len(combined_df)}")
        print(f"\nFixtures by season:")
        print(combined_df.groupby('season').size())
        
        print(f"\nResults distribution:")
        print(combined_df['result'].value_counts())
        
        # Check Directory Exists
        require_dirs(assert_only=True)

        # Save to CSV
        filename = os.path.join(DATA_DIR, f"pl_historical_fixtures_{datetime.now().strftime('%Y%m%d')}.csv")
        combined_df.to_csv(filename, index=False)
        print(f"Saved: {filename}")
        
        print(f"\n{'='*70}")
        print("NEXT STEPS")
        print(f"{'='*70}")
        print("1. Review the CSV file")
        print("2. We'll add match statistics (shots, possession, etc.)")
        print("3. Then collect team statistics")
        
    else:
        print("\n✗ No data collected")

if __name__ == "__main__":
    main()
