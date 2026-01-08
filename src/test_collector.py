# test_collector.py
"""
Quick test to see what data API-Football returns
"""
from api_football_collector import APIFootballCollector
from config import API_FOOTBALL_KEY, DB_PARAMS
import json

def test_api_calls():
    """Test a few API calls to see the data structure"""
    
    print("="*60)
    print("Testing API-Football Data Collection")
    print("="*60)
    
    collector = APIFootballCollector(API_FOOTBALL_KEY, DB_PARAMS)
    
    # Test 1: Get a few recent fixtures
    print("\n" + "="*60)
    print("TEST 1: Recent Premier League Fixtures")
    print("="*60)
    
    recent_fixtures = collector.get_historical_fixtures(last_n_rounds=2)
    
    if not recent_fixtures.empty:
        print(f"\n✓ Found {len(recent_fixtures)} fixtures")
        print("\nColumns available:")
        print(recent_fixtures.columns.tolist())
        
        print("\nSample fixture data:")
        print(recent_fixtures[['home_team', 'away_team', 'home_goals', 'away_goals', 'home_shots', 'away_shots']].head(3))
        
        # Save to CSV for inspection
        recent_fixtures.to_csv('test_fixtures.csv', index=False)
        print("\n✓ Saved to 'test_fixtures.csv' for inspection")
    else:
        print("\n✗ No fixtures returned")
    
    
    # Test 2: Get team statistics for one team
    if not recent_fixtures.empty:
        print("\n" + "="*60)
        print("TEST 2: Team Statistics")
        print("="*60)
        
        # Get first team from fixtures
        team_id = recent_fixtures.iloc[0]['home_team_id']
        team_name = recent_fixtures.iloc[0]['home_team']
        
        print(f"\nFetching stats for: {team_name} (ID: {team_id})")
        
        stats = collector.get_team_statistics(team_id)
        
        if stats:
            print("\n✓ Team statistics retrieved")
            print("\nAvailable stats:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        else:
            print("\n✗ No stats returned")
    
    
    # Test 3: Check API quota
    print("\n" + "="*60)
    print("API Usage Summary")
    print("="*60)
    print("Check your API dashboard for remaining requests")
    print("Dashboard: https://dashboard.api-football.com")
    
    print("\n" + "="*60)
    print("Tests Complete!")
    print("="*60)

if __name__ == "__main__":
    test_api_calls()
