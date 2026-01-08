"""
Premier League Win Probability Model - Data Collection
Collects data from API-Football and stores in PostgreSQL
"""

import requests
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timedelta
import time
import json
from typing import Dict, List, Optional

class APIFootballCollector:
    """Collects Premier League data from API-Football"""
    
    def __init__(self, api_key: str, db_params: Dict[str, str]):
        """
        Initialize collector with API key and database parameters
        
        Args:
            api_key: Your API-Football key
            db_params: Dict with keys: host, database, user, password, port
        """
        self.api_key = api_key
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
             'x-apisports-key': api_key,  # Changed from x-rapidapi-key
            'x-rapidapi-host': 'v3.football.api-sports.io'
        }
        self.db_params = db_params
        self.premier_league_id = 39  # API-Football ID for Premier League
        self.current_season = 2025  # Adjust as needed
        
    def _make_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Make API request with rate limiting"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Check API limits (free tier: 100 requests/day)
            requests_remaining = response.headers.get('X-RateLimit-requests-Remaining')
            print(f"Requests remaining: {requests_remaining}")
            
            # Rate limiting
            time.sleep(1)  # Be respectful to API
            
            return data
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return None
    
    def get_upcoming_fixtures(self, days_ahead: int = 14) -> pd.DataFrame:
        """Get upcoming Premier League fixtures"""
        today = datetime.now().strftime('%Y-%m-%d')
        future = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
        
        params = {
            'league': self.premier_league_id,
            'season': self.current_season,
            'from': today,
            'to': future
        }
        
        data = self._make_request('fixtures', params)
        
        if not data or 'response' not in data:
            return pd.DataFrame()
        
        fixtures = []
        for match in data['response']:
            fixtures.append({
                'fixture_id': match['fixture']['id'],
                'date': match['fixture']['date'],
                'home_team_id': match['teams']['home']['id'],
                'home_team': match['teams']['home']['name'],
                'away_team_id': match['teams']['away']['id'],
                'away_team': match['teams']['away']['name'],
                'venue': match['fixture']['venue']['name'],
                'status': match['fixture']['status']['short']
            })
        
        return pd.DataFrame(fixtures)
    
    def get_team_statistics(self, team_id: int, season: int = None) -> Dict:
        """Get team statistics for the season"""
        if season is None:
            season = self.current_season
            
        params = {
            'league': self.premier_league_id,
            'season': season,
            'team': team_id
        }
        
        data = self._make_request('teams/statistics', params)
        
        if not data or 'response' not in data:
            return {}
        
        stats = data['response']
        
        # Extract key statistics
        return {
            'team_id': team_id,
            'games_played': stats['fixtures']['played']['total'],
            'wins': stats['fixtures']['wins']['total'],
            'draws': stats['fixtures']['draws']['total'],
            'losses': stats['fixtures']['losses']['total'],
            'goals_for': stats['goals']['for']['total']['total'],
            'goals_against': stats['goals']['against']['total']['total'],
            'avg_goals_for': stats['goals']['for']['average']['total'],
            'avg_goals_against': stats['goals']['against']['average']['total'],
            'form': stats['form'],
            'home_wins': stats['fixtures']['wins']['home'],
            'home_draws': stats['fixtures']['draws']['home'],
            'home_losses': stats['fixtures']['losses']['home'],
            'away_wins': stats['fixtures']['wins']['away'],
            'away_draws': stats['fixtures']['draws']['away'],
            'away_losses': stats['fixtures']['losses']['away']
        }
    
    def get_fixture_statistics(self, fixture_id: int) -> Dict:
        """Get detailed statistics for a completed fixture (including xG)"""
        params = {'fixture': fixture_id}
        data = self._make_request('fixtures/statistics', params)
        
        if not data or 'response' not in data or len(data['response']) < 2:
            return {}
        
        home_stats = data['response'][0]
        away_stats = data['response'][1]
        
        def extract_stat(stats, stat_name):
            for stat in stats['statistics']:
                if stat['type'] == stat_name:
                    value = stat['value']
                    # Handle percentage strings
                    if isinstance(value, str) and '%' in value:
                        return float(value.replace('%', ''))
                    return value if value is not None else 0
            return 0
        
        return {
            'fixture_id': fixture_id,
            'home_xg': extract_stat(home_stats, 'expected_goals'),
            'away_xg': extract_stat(away_stats, 'expected_goals'),
            'home_shots': extract_stat(home_stats, 'Total Shots'),
            'away_shots': extract_stat(away_stats, 'Total Shots'),
            'home_shots_on_target': extract_stat(home_stats, 'Shots on Goal'),
            'away_shots_on_target': extract_stat(away_stats, 'Shots on Goal'),
            'home_possession': extract_stat(home_stats, 'Ball Possession'),
            'away_possession': extract_stat(away_stats, 'Ball Possession')
        }
    
    def get_historical_fixtures(self, last_n_rounds: int = 10) -> pd.DataFrame:
        """Get historical fixtures with statistics"""
        params = {
            'league': self.premier_league_id,
            'season': self.current_season,
            'last': last_n_rounds
        }
        
        data = self._make_request('fixtures', params)
        
        if not data or 'response' not in data:
            return pd.DataFrame()
        
        fixtures = []
        for match in data['response']:
            # Only process completed matches
            if match['fixture']['status']['short'] == 'FT':
                fixture_data = {
                    'fixture_id': match['fixture']['id'],
                    'date': match['fixture']['date'],
                    'home_team_id': match['teams']['home']['id'],
                    'home_team': match['teams']['home']['name'],
                    'away_team_id': match['teams']['away']['id'],
                    'away_team': match['teams']['away']['name'],
                    'home_goals': match['goals']['home'],
                    'away_goals': match['goals']['away'],
                    'result': self._get_result(match['goals']['home'], match['goals']['away'])
                }
                
                # Get detailed statistics including xG
                stats = self.get_fixture_statistics(match['fixture']['id'])
                fixture_data.update(stats)
                
                fixtures.append(fixture_data)
        
        return pd.DataFrame(fixtures)
    
    def _get_result(self, home_goals: int, away_goals: int) -> str:
        """Determine match result"""
        if home_goals > away_goals:
            return 'H'  # Home win
        elif away_goals > home_goals:
            return 'A'  # Away win
        else:
            return 'D'  # Draw
    
    def get_head_to_head(self, team1_id: int, team2_id: int, last_n: int = 5) -> pd.DataFrame:
        """Get head-to-head statistics between two teams"""
        params = {
            'h2h': f"{team1_id}-{team2_id}",
            'last': last_n
        }
        
        data = self._make_request('fixtures/headtohead', params)
        
        if not data or 'response' not in data:
            return pd.DataFrame()
        
        h2h = []
        for match in data['response']:
            h2h.append({
                'date': match['fixture']['date'],
                'home_team': match['teams']['home']['name'],
                'away_team': match['teams']['away']['name'],
                'home_goals': match['goals']['home'],
                'away_goals': match['goals']['away']
            })
        
        return pd.DataFrame(h2h)
    
    def setup_database(self):
        """Create necessary database tables"""
        conn = psycopg2.connect(**self.db_params)
        cur = conn.cursor()
        
        # Fixtures table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fixtures (
                fixture_id INTEGER PRIMARY KEY,
                date TIMESTAMP,
                home_team_id INTEGER,
                home_team VARCHAR(100),
                away_team_id INTEGER,
                away_team VARCHAR(100),
                venue VARCHAR(200),
                status VARCHAR(20),
                home_goals INTEGER,
                away_goals INTEGER,
                result VARCHAR(1),
                home_xg FLOAT,
                away_xg FLOAT,
                home_shots INTEGER,
                away_shots INTEGER,
                home_shots_on_target INTEGER,
                away_shots_on_target INTEGER,
                home_possession FLOAT,
                away_possession FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Team statistics table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS team_statistics (
                id SERIAL PRIMARY KEY,
                team_id INTEGER,
                season INTEGER,
                games_played INTEGER,
                wins INTEGER,
                draws INTEGER,
                losses INTEGER,
                goals_for INTEGER,
                goals_against INTEGER,
                avg_goals_for FLOAT,
                avg_goals_against FLOAT,
                form VARCHAR(20),
                home_wins INTEGER,
                home_draws INTEGER,
                home_losses INTEGER,
                away_wins INTEGER,
                away_draws INTEGER,
                away_losses INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(team_id, season)
            )
        """)
        
        # Predictions table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id SERIAL PRIMARY KEY,
                fixture_id INTEGER REFERENCES fixtures(fixture_id),
                home_win_prob FLOAT,
                draw_prob FLOAT,
                away_win_prob FLOAT,
                predicted_home_goals FLOAT,
                predicted_away_goals FLOAT,
                confidence_score FLOAT,
                model_version VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("Database tables created successfully!")
    
    def save_fixtures_to_db(self, fixtures_df: pd.DataFrame):
        """Save fixtures to database"""
        if fixtures_df.empty:
            print("No fixtures to save")
            return
        
        conn = psycopg2.connect(**self.db_params)
        cur = conn.cursor()
        
        # Prepare data for insertion
        columns = fixtures_df.columns.tolist()
        values = [tuple(row) for row in fixtures_df.values]
        
        # Build insert query with ON CONFLICT
        cols_str = ', '.join(columns)
        placeholders = ', '.join(['%s'] * len(columns))
        
        query = f"""
            INSERT INTO fixtures ({cols_str})
            VALUES %s
            ON CONFLICT (fixture_id) DO UPDATE SET
                status = EXCLUDED.status,
                home_goals = EXCLUDED.home_goals,
                away_goals = EXCLUDED.away_goals,
                result = EXCLUDED.result,
                home_xg = EXCLUDED.home_xg,
                away_xg = EXCLUDED.away_xg
        """
        
        execute_values(cur, query, values, template=None, page_size=100)
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"Saved {len(fixtures_df)} fixtures to database")
    
    def save_team_stats_to_db(self, stats_dict: Dict):
        """Save team statistics to database"""
        if not stats_dict:
            return
        
        conn = psycopg2.connect(**self.db_params)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO team_statistics 
            (team_id, season, games_played, wins, draws, losses, goals_for, 
             goals_against, avg_goals_for, avg_goals_against, form,
             home_wins, home_draws, home_losses, away_wins, away_draws, away_losses)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (team_id, season) DO UPDATE SET
                games_played = EXCLUDED.games_played,
                wins = EXCLUDED.wins,
                draws = EXCLUDED.draws,
                losses = EXCLUDED.losses,
                goals_for = EXCLUDED.goals_for,
                goals_against = EXCLUDED.goals_against,
                form = EXCLUDED.form,
                updated_at = CURRENT_TIMESTAMP
        """, (
            stats_dict['team_id'], self.current_season,
            stats_dict['games_played'], stats_dict['wins'], 
            stats_dict['draws'], stats_dict['losses'],
            stats_dict['goals_for'], stats_dict['goals_against'],
            stats_dict['avg_goals_for'], stats_dict['avg_goals_against'],
            stats_dict['form'], stats_dict['home_wins'],
            stats_dict['home_draws'], stats_dict['home_losses'],
            stats_dict['away_wins'], stats_dict['away_draws'],
            stats_dict['away_losses']
        ))
        
        conn.commit()
        cur.close()
        conn.close()


