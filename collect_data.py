# collect_data.py
from api_football_collector import APIFootballCollector
from config import API_FOOTBALL_KEY, DB_PARAMS

def main():
    print("="*60)
    print("Premier League Data Collection")
    print("="*60)
    
    # Initialize collector
    print("\n1. Initializing collector...")
    collector = APIFootballCollector(API_FOOTBALL_KEY, DB_PARAMS)
    
    # Setup database
    print("\n2. Setting up database tables...")
    try:
        collector.setup_database()
        print("   ✓ Database tables created")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return
    
    # Collect historical data
    print("\n3. Collecting historical fixtures (last 20 rounds)...")
    print("   This will use approximately 20-30 API requests")
    print("   Please wait...")
    
    try:
        historical_fixtures = collector.get_historical_fixtures(last_n_rounds=20)
        
        if not historical_fixtures.empty:
            print(f"   ✓ Found {len(historical_fixtures)} historical fixtures")
            collector.save_fixtures_to_db(historical_fixtures)
            print("   ✓ Saved to database")
            print(f"\n   Sample data:")
            print(historical_fixtures[['date', 'home_team', 'away_team', 'home_goals', 'away_goals']].head(3))
        else:
            print("   ✗ No historical fixtures found")
    except Exception as e:
        print(f"   ✗ Error collecting historical data: {e}")
    
    # Collect upcoming fixtures
    print("\n4. Collecting upcoming fixtures (next 14 days)...")
    print("   This will use approximately 5-10 API requests")
    
    try:
        upcoming_fixtures = collector.get_upcoming_fixtures(days_ahead=14)
        
        if not upcoming_fixtures.empty:
            print(f"   ✓ Found {len(upcoming_fixtures)} upcoming fixtures")
            collector.save_fixtures_to_db(upcoming_fixtures)
            print("   ✓ Saved to database")
            print(f"\n   Upcoming matches:")
            print(upcoming_fixtures[['date', 'home_team', 'away_team']].head(5))
        else:
            print("   ✗ No upcoming fixtures found")
            print("   (This might be normal if it's off-season)")
    except Exception as e:
        print(f"   ✗ Error collecting upcoming data: {e}")
    
    # Collect team statistics
    print("\n5. Collecting team statistics...")
    
    try:
        if not upcoming_fixtures.empty:
            import pandas as pd
            unique_teams = pd.concat([
                upcoming_fixtures[['home_team_id', 'home_team']].rename(
                    columns={'home_team_id': 'team_id', 'home_team': 'team'}
                ),
                upcoming_fixtures[['away_team_id', 'away_team']].rename(
                    columns={'away_team_id': 'team_id', 'away_team': 'team'}
                )
            ]).drop_duplicates()
            
            print(f"   Fetching stats for {len(unique_teams)} teams...")
            success_count = 0
            for idx, team in unique_teams.iterrows():
                print(f"   - {team['team']}...", end='', flush=True)
                stats = collector.get_team_statistics(team['team_id'])
                if stats:
                    collector.save_team_stats_to_db(stats)
                    print(" ✓")
                    success_count += 1
                else:
                    print(" ✗")
            
            print(f"\n   ✓ Collected stats for {success_count}/{len(unique_teams)} teams")
    except Exception as e:
        print(f"   ✗ Error collecting team stats: {e}")
    
    print("\n" + "="*60)
    print("Data collection complete!")
    print("="*60)
    print("\nYour database now contains:")
    print("  - Historical match data with xG statistics")
    print("  - Upcoming fixtures")
    print("  - Team statistics")
    print("\nNext steps:")
    print("  1. Open Jupyter Notebook")
    print("  2. Open: premier_league_model.ipynb")
    print("  3. Run all cells to train your model")

if __name__ == "__main__":
    main()