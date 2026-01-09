# enrich_historical_data.py
"""
Enrich historical fixtures with match statistics
"""
import os
from api_football_collector import APIFootballCollector
from config import API_FOOTBALL_KEY, DB_PARAMS
import pandas as pd
from datetime import datetime
from paths import DATA_DIR,require_dirs


def select_latest(prefix: str, suffix: str = ".csv") -> str:
    files = [f for f in os.listdir(DATA_DIR) if f.startswith(prefix) and f.endswith(suffix)]
    if not files:
        raise FileNotFoundError(f"No files found in {DATA_DIR} with prefix '{prefix}'")
    # Prefer date token at the end of the name; fallback to modified time
    try:
        latest = max(files, key=lambda x: x.rsplit("_", 1)[-1].split(".")[0])
    except Exception:
        latest = max(files, key=lambda f: os.path.getmtime(os.path.join(DATA_DIR, f)))
    return os.path.join(DATA_DIR, latest)

def main():
    print("="*70)
    print("ENRICHING HISTORICAL DATA WITH MATCH STATISTICS")
    print("="*70)

    require_dirs(assert_only=True)

    # Load the latest historical fixtures from data/
    csv_path = select_latest("pl_historical_fixtures_")
    print(f"\nLoading: {csv_path}")
    fixtures_df = pd.read_csv(csv_path)
    print(f"✓ Loaded {len(fixtures_df)} fixtures")


    # Initialize collector
    collector = APIFootballCollector(API_FOOTBALL_KEY, DB_PARAMS)
    
    print(f"\nEstimated API calls: {len(fixtures_df)}")
    print("This will take approximately 15-20 minutes...")
    print("\nStarting enrichment...")
    
    # Enrich with statistics
    enriched_df = collector.enrich_fixtures_with_statistics(fixtures_df)
    
    # Save enriched data
    output_path = os.path.join(DATA_DIR, f"pl_historical_enriched_{datetime.now().strftime('%Y%m%d')}.csv")
    enriched_df.to_csv(output_path, index=False)
    
    print(f"\n{'='*70}")
    print("ENRICHMENT SUMMARY")
    print(f"{'='*70}")
    print(f"Total fixtures: {len(enriched_df)}")
    print(f"\nNew columns added:")
    new_cols = [col for col in enriched_df.columns if col not in fixtures_df.columns]
    for col in new_cols:
        print(f"  - {col}")
    
    print(f"\n✓ Saved to: {output_path}")
    
    print(f"\n{'='*70}")
    print("NEXT STEPS")
    print(f"{'='*70}")
    print("1. Review the enriched CSV")
    print("2. We'll create features from this data")
    print("3. Then build the ML model")

if __name__ == "__main__":
    main()
