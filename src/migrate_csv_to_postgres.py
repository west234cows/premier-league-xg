# migrate_csv_to_postgres.py
"""
Migrate CSV data to PostgreSQL database
Transfers historical fixtures, statistics, and features
"""
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import os
from datetime import datetime
from config import DB_PARAMS
from paths import DATA_DIR

def select_latest_csv(prefix):
    """Find the most recent CSV file with given prefix"""
    files = [f for f in os.listdir(DATA_DIR) if f.startswith(prefix) and f.endswith('.csv')]
    if not files:
        return None
    try:
        latest = max(files, key=lambda x: x.rsplit('_', 1)[-1].split('.')[0])
    except Exception:
        latest = max(files, key=lambda f: os.path.getmtime(os.path.join(DATA_DIR, f)))
    return os.path.join(DATA_DIR, latest)

def migrate_fixtures():
    """Migrate historical fixtures to database"""
    print("\n" + "="*70)
    print("MIGRATING FIXTURES")
    print("="*70)
    
    # Find latest enriched data (has the most complete info)
    enriched_file = select_latest_csv('pl_historical_enriched_')
    if not enriched_file:
        print("✗ No enriched historical data found")
        return 0
    
    print(f"\nLoading: {os.path.basename(enriched_file)}")
    df = pd.read_csv(enriched_file)
    print(f"✓ Loaded {len(df)} matches")
    
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    
    # Prepare fixture data
    fixture_data = []
    stats_data = []
    
    for _, row in df.iterrows():
        # Fixtures table data
        fixture_data.append((
            int(row['fixture_id']),
            pd.to_datetime(row['date']),
            row.get('season', '2024-2025'),  # Default season if not present
            int(row['home_team_id']),
            row['home_team'],
            int(row['away_team_id']),
            row['away_team'],
            int(row['home_goals']) if pd.notna(row['home_goals']) else None,
            int(row['away_goals']) if pd.notna(row['away_goals']) else None,
            row['result'] if pd.notna(row['result']) else None,
            row.get('venue', ''),
            row.get('status', 'FT')
        ))
        
        # Match statistics data (if columns exist)
        if 'home_shots' in df.columns:
            stats_data.append((
                int(row['fixture_id']),
                int(row['home_shots']) if pd.notna(row['home_shots']) else None,
                int(row['away_shots']) if pd.notna(row['away_shots']) else None,
                int(row['home_shots_on_target']) if pd.notna(row['home_shots_on_target']) else None,
                int(row['away_shots_on_target']) if pd.notna(row['away_shots_on_target']) else None,
                float(row['home_possession']) if pd.notna(row['home_possession']) else None,
                float(row['away_possession']) if pd.notna(row['away_possession']) else None,
                int(row['home_corners']) if 'home_corners' in df.columns and pd.notna(row['home_corners']) else None,
                int(row['away_corners']) if 'away_corners' in df.columns and pd.notna(row['away_corners']) else None,
                int(row['home_fouls']) if 'home_fouls' in df.columns and pd.notna(row['home_fouls']) else None,
                int(row['away_fouls']) if 'away_fouls' in df.columns and pd.notna(row['away_fouls']) else None,
                int(row['home_yellow_cards']) if 'home_yellow_cards' in df.columns and pd.notna(row['home_yellow_cards']) else None,
                int(row['away_yellow_cards']) if 'away_yellow_cards' in df.columns and pd.notna(row['away_yellow_cards']) else None,
                int(row['home_red_cards']) if 'home_red_cards' in df.columns and pd.notna(row['home_red_cards']) else None,
                int(row['away_red_cards']) if 'away_red_cards' in df.columns and pd.notna(row['away_red_cards']) else None,
            ))
    
    # Insert fixtures
    print("\nInserting fixtures...")
    execute_values(cur, """
        INSERT INTO fixtures (
            fixture_id, date, season, home_team_id, home_team, 
            away_team_id, away_team, home_goals, away_goals, result, venue, status
        ) VALUES %s
        ON CONFLICT (fixture_id) DO UPDATE SET
            home_goals = EXCLUDED.home_goals,
            away_goals = EXCLUDED.away_goals,
            result = EXCLUDED.result,
            status = EXCLUDED.status,
            updated_at = CURRENT_TIMESTAMP
    """, fixture_data)
    print(f"✓ Inserted {len(fixture_data)} fixtures")
    
    # Insert match statistics
    if stats_data:
        print("\nInserting match statistics...")
        execute_values(cur, """
            INSERT INTO match_statistics (
                fixture_id, home_shots, away_shots, home_shots_on_target, 
                away_shots_on_target, home_possession, away_possession,
                home_corners, away_corners, home_fouls, away_fouls,
                home_yellow_cards, away_yellow_cards, home_red_cards, away_red_cards
            ) VALUES %s
            ON CONFLICT (fixture_id) DO UPDATE SET
                home_shots = EXCLUDED.home_shots,
                away_shots = EXCLUDED.away_shots,
                home_possession = EXCLUDED.home_possession,
                away_possession = EXCLUDED.away_possession
        """, stats_data)
        print(f"✓ Inserted {len(stats_data)} match statistics")
    
    conn.commit()
    cur.close()
    conn.close()
    
    return len(fixture_data)

def migrate_features():
    """Migrate engineered features to database"""
    print("\n" + "="*70)
    print("MIGRATING FEATURES")
    print("="*70)
    
    features_file = select_latest_csv('pl_features_complete_')
    if not features_file:
        print("✗ No features file found")
        return 0
    
    print(f"\nLoading: {os.path.basename(features_file)}")
    df = pd.read_csv(features_file)
    print(f"✓ Loaded {len(df)} feature sets")
    
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    
    # Map CSV columns to database columns
    # Adjust these based on your actual feature names
    feature_mappings = {
        'home_goals_last5': 'home_goals_last5',
        'away_goals_last5': 'away_goals_last5',
        'home_goals_conceded_last5': 'home_goals_conceded_last5',
        'away_goals_conceded_last5': 'away_goals_conceded_last5',
        'home_shots_last5': 'home_shots_last5',
        'away_shots_last5': 'away_shots_last5',
        'home_possession_last5': 'home_possession_last5',
        'away_possession_last5': 'away_possession_last5',
        'home_wins_last5': 'home_wins_last5',
        'away_wins_last5': 'away_wins_last5',
        'home_shot_accuracy': 'home_shot_accuracy',
        'away_shot_accuracy': 'away_shot_accuracy',
        'home_conversion_rate': 'home_conversion_rate',
        'away_conversion_rate': 'away_conversion_rate',
        'home_defensive_efficiency': 'home_defensive_efficiency',
        'away_defensive_efficiency': 'away_defensive_efficiency',
        'form_differential': 'form_differential',
        'home_advantage': 'home_advantage',
        'attack_vs_defense': 'attack_vs_defense',
    }
    
    features_data = []
    for _, row in df.iterrows():
        feature_values = [int(row['fixture_id'])]
        
        for csv_col, db_col in feature_mappings.items():
            if csv_col in df.columns:
                val = row[csv_col]
                feature_values.append(float(val) if pd.notna(val) else None)
            else:
                feature_values.append(None)
        
        features_data.append(tuple(feature_values))
    
    # Build column list dynamically
    db_columns = ['fixture_id'] + list(feature_mappings.values())
    columns_str = ', '.join(db_columns)
    
    print("\nInserting features...")
    execute_values(cur, f"""
        INSERT INTO features ({columns_str})
        VALUES %s
        ON CONFLICT (fixture_id) DO UPDATE SET
            home_goals_last5 = EXCLUDED.home_goals_last5,
            away_goals_last5 = EXCLUDED.away_goals_last5,
            home_wins_last5 = EXCLUDED.home_wins_last5,
            away_wins_last5 = EXCLUDED.away_wins_last5
    """, features_data)
    print(f"✓ Inserted {len(features_data)} feature sets")
    
    conn.commit()
    cur.close()
    conn.close()
    
    return len(features_data)

def verify_migration():
    """Verify data was migrated successfully"""
    print("\n" + "="*70)
    print("VERIFYING MIGRATION")
    print("="*70)
    
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    
    # Check fixtures
    cur.execute("SELECT COUNT(*) FROM fixtures")
    fixtures_count = cur.fetchone()[0]
    print(f"\nFixtures: {fixtures_count} records")
    
    # Check match statistics
    cur.execute("SELECT COUNT(*) FROM match_statistics")
    stats_count = cur.fetchone()[0]
    print(f"Match Statistics: {stats_count} records")
    
    # Check features
    cur.execute("SELECT COUNT(*) FROM features")
    features_count = cur.fetchone()[0]
    print(f"Features: {features_count} records")
    
    # Show sample data
    print("\nSample fixture:")
    cur.execute("""
        SELECT fixture_id, date, home_team, away_team, home_goals, away_goals, result
        FROM fixtures
        ORDER BY date DESC
        LIMIT 1
    """)
    sample = cur.fetchone()
    if sample:
        print(f"  ID: {sample[0]}")
        print(f"  Date: {sample[1]}")
        print(f"  Match: {sample[2]} vs {sample[3]}")
        print(f"  Score: {sample[4]}-{sample[5]} ({sample[6]})")
    
    cur.close()
    conn.close()

def main():
    print("="*70)
    print("CSV TO POSTGRESQL MIGRATION")
    print("="*70)
    
    try:
        # Migrate data
        fixtures_migrated = migrate_fixtures()
        features_migrated = migrate_features()
        
        # Verify
        verify_migration()
        
        print("\n" + "="*70)
        print("MIGRATION COMPLETE!")
        print("="*70)
        print(f"\nMigrated:")
        print(f"  • {fixtures_migrated} fixtures with match statistics")
        print(f"  • {features_migrated} feature sets")
        
        print("\n" + "="*70)
        print("NEXT STEPS:")
        print("="*70)
        print("1. Update predict_upcoming.py to use PostgreSQL")
        print("2. Create prediction tracking system")
        print("3. Build Streamlit dashboard")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()