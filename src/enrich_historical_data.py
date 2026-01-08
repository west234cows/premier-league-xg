# enrich_historical_data.py
"""
Enrich historical fixtures with match statistics
"""
from api_football_collector import APIFootballCollector
from config import API_FOOTBALL_KEY, DB_PARAMS
import pandas as pd
from datetime import datetime

def main():
    print("="*70)
    print("ENRICHING HISTORICAL DATA WITH MATCH STATISTICS")
    print("="*70)
    
    # Load the historical fixtures CSV
    csv_file = "pl_historical_fixtures_20260108.csv"
    
    print(f"\nLoading: {csv_file}")
    fixtures_df = pd.read_csv(csv_file)
    print(f"✓ Loaded {len(fixtures_df)} fixtures")
    
    # Initialize collector
    collector = APIFootballCollector(API_FOOTBALL_KEY, DB_PARAMS)
    
    print(f"\nEstimated API calls: {len(fixtures_df)}")
    print("This will take approximately 15-20 minutes...")
    print("\nStarting enrichment...")
    
    # Enrich with statistics
    enriched_df = collector.enrich_fixtures_with_statistics(fixtures_df)
    
    # Save enriched data
    output_file = f"pl_historical_enriched_{datetime.now().strftime('%Y%m%d')}.csv"
    enriched_df.to_csv(output_file, index=False)
    
    print(f"\n{'='*70}")
    print("ENRICHMENT SUMMARY")
    print(f"{'='*70}")
    print(f"Total fixtures: {len(enriched_df)}")
    print(f"\nNew columns added:")
    new_cols = [col for col in enriched_df.columns if col not in fixtures_df.columns]
    for col in new_cols:
        print(f"  - {col}")
    
    print(f"\n✓ Saved to: {output_file}")
    
    print(f"\n{'='*70}")
    print("NEXT STEPS")
    print(f"{'='*70}")
    print("1. Review the enriched CSV")
    print("2. We'll create features from this data")
    print("3. Then build the ML model")

if __name__ == "__main__":
    main()
