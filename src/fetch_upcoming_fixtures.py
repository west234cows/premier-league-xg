# fetch_upcoming_fixtures.py
"""
Fetch upcoming Premier League fixtures from API and insert into PostgreSQL
"""
import requests
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timedelta
from config import API_FOOTBALL_KEY, DB_PARAMS

def fetch_upcoming_fixtures(days_ahead=14):
    """Fetch upcoming fixtures from API-Football"""
    print("="*70)
    print("FETCHING UPCOMING FIXTURES FROM API")
    print("="*70)
    
    today = datetime.now().strftime('%Y-%m-%d')
    future = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
    
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        'x-apisports-key': API_FOOTBALL_KEY,
        'x-rapidapi-host': 'v3.football.api-sports.io'
    }
    
    params = {
        'league': 39,  # Premier League
        'season': 2025,
        'from': today,
        'to': future
    }
    
    print(f"\nFetching fixtures from {today} to {future}...")
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        requests_remaining = response.headers.get('X-RateLimit-requests-Remaining')
        print(f"API Requests remaining: {requests_remaining}")
        
        if 'response' not in data or len(data['response']) == 0:
            print("✗ No upcoming fixtures found")
            return []
        
        fixtures = []
        for match in data['response']:
            # Only get fixtures that haven't been played yet
            status = match['fixture']['status']['short']
            if status in ['NS', 'TBD']:  # Not started or To be determined
                fixtures.append({
                    'fixture_id': match['fixture']['id'],
                    'date': match['fixture']['date'],
                    'home_team_id': match['teams']['home']['id'],
                    'home_team': match['teams']['home']['name'],
                    'away_team_id': match['teams']['away']['id'],
                    'away_team': match['teams']['away']['name'],
                    'venue': match['fixture']['venue']['name'],
                    'status': status
                })
        
        print(f"✓ Found {len(fixtures)} upcoming fixtures")
        return fixtures
        
    except Exception as e:
        print(f"✗ Error fetching fixtures: {e}")
        return []

def insert_fixtures_to_db(fixtures):
    """Insert upcoming fixtures into PostgreSQL"""
    if not fixtures:
        print("\nNo fixtures to insert")
        return
    
    print("\n" + "="*70)
    print("INSERTING FIXTURES INTO DATABASE")
    print("="*70)
    
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    
    fixture_data = []
    for fixture in fixtures:
        fixture_data.append((
            fixture['fixture_id'],
            fixture['date'],
            '2024-2025',  # Current season
            fixture['home_team_id'],
            fixture['home_team'],
            fixture['away_team_id'],
            fixture['away_team'],
            None,  # home_goals
            None,  # away_goals
            None,  # result
            fixture['venue'],
            fixture['status']
        ))
    
    execute_values(cur, """
        INSERT INTO fixtures (
            fixture_id, date, season, home_team_id, home_team,
            away_team_id, away_team, home_goals, away_goals, result, venue, status
        ) VALUES %s
        ON CONFLICT (fixture_id) DO UPDATE SET
            date = EXCLUDED.date,
            status = EXCLUDED.status
    """, fixture_data)
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"✓ Inserted {len(fixture_data)} fixtures into database")
    
    # Display the fixtures
    print("\nUpcoming fixtures:")
    for fixture in fixtures:
        print(f"  {fixture['date']}: {fixture['home_team']} vs {fixture['away_team']}")

def main():
    print("="*70)
    print("FETCH UPCOMING PREMIER LEAGUE FIXTURES")
    print("="*70)
    
    try:
        fixtures = fetch_upcoming_fixtures(days_ahead=14)
        insert_fixtures_to_db(fixtures)
        
        print("\n" + "="*70)
        print("COMPLETE!")
        print("="*70)
        print("\nNext step: Run predictions")
        print("  python src/predict_upcoming.py")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()