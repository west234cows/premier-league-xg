# setup_database.py
"""
Create PostgreSQL database schema for Premier League prediction system
"""
import psycopg2
from config import DB_PARAMS

def create_tables():
    """Create all necessary database tables"""
    
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    
    print("Creating database tables...")
    
    # 1. Fixtures table (historical matches)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fixtures (
            fixture_id INTEGER PRIMARY KEY,
            date TIMESTAMP NOT NULL,
            season VARCHAR(10),
            home_team_id INTEGER,
            home_team VARCHAR(100) NOT NULL,
            away_team_id INTEGER,
            away_team VARCHAR(100) NOT NULL,
            home_goals INTEGER,
            away_goals INTEGER,
            result VARCHAR(1),  -- 'H', 'D', 'A'
            venue VARCHAR(200),
            status VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✓ Created fixtures table")
    
    # 2. Match statistics table (enriched data)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS match_statistics (
            id SERIAL PRIMARY KEY,
            fixture_id INTEGER REFERENCES fixtures(fixture_id) ON DELETE CASCADE,
            home_shots INTEGER,
            away_shots INTEGER,
            home_shots_on_target INTEGER,
            away_shots_on_target INTEGER,
            home_possession FLOAT,
            away_possession FLOAT,
            home_corners INTEGER,
            away_corners INTEGER,
            home_fouls INTEGER,
            away_fouls INTEGER,
            home_yellow_cards INTEGER,
            away_yellow_cards INTEGER,
            home_red_cards INTEGER,
            away_red_cards INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(fixture_id)
        );
    """)
    print("✓ Created match_statistics table")
    
    # 3. Features table (engineered features for each match)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS features (
            id SERIAL PRIMARY KEY,
            fixture_id INTEGER REFERENCES fixtures(fixture_id) ON DELETE CASCADE,
            
            -- Team form features (last 5 games)
            home_goals_last5 FLOAT,
            away_goals_last5 FLOAT,
            home_goals_conceded_last5 FLOAT,
            away_goals_conceded_last5 FLOAT,
            home_shots_last5 FLOAT,
            away_shots_last5 FLOAT,
            home_possession_last5 FLOAT,
            away_possession_last5 FLOAT,
            home_wins_last5 FLOAT,
            away_wins_last5 FLOAT,
            
            -- Advanced metrics
            home_shot_accuracy FLOAT,
            away_shot_accuracy FLOAT,
            home_conversion_rate FLOAT,
            away_conversion_rate FLOAT,
            home_defensive_efficiency FLOAT,
            away_defensive_efficiency FLOAT,
            
            -- Match context
            form_differential FLOAT,
            home_advantage FLOAT,
            attack_vs_defense FLOAT,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(fixture_id)
        );
    """)
    print("✓ Created features table")
    
    # 4. Predictions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id SERIAL PRIMARY KEY,
            fixture_id INTEGER REFERENCES fixtures(fixture_id) ON DELETE CASCADE,
            prediction_date TIMESTAMP NOT NULL,
            
            -- Probabilities
            home_win_prob FLOAT NOT NULL,
            draw_prob FLOAT NOT NULL,
            away_win_prob FLOAT NOT NULL,
            
            -- Prediction metadata
            predicted_result VARCHAR(1),  -- 'H', 'D', 'A'
            confidence VARCHAR(10),  -- 'High', 'Medium', 'Low'
            model_version VARCHAR(50),
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- Ensure one prediction per fixture per day
            UNIQUE(fixture_id, prediction_date)
        );
    """)
    print("✓ Created predictions table")
    
    # 5. Prediction accuracy tracking
    cur.execute("""
        CREATE TABLE IF NOT EXISTS prediction_accuracy (
            id SERIAL PRIMARY KEY,
            fixture_id INTEGER REFERENCES fixtures(fixture_id) ON DELETE CASCADE,
            prediction_id INTEGER REFERENCES predictions(id) ON DELETE CASCADE,
            
            -- Predicted vs Actual
            predicted_result VARCHAR(1),
            actual_result VARCHAR(1),
            was_correct BOOLEAN,
            
            -- Probability details
            predicted_home_prob FLOAT,
            predicted_draw_prob FLOAT,
            predicted_away_prob FLOAT,
            confidence VARCHAR(10),
            
            tracked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(fixture_id)
        );
    """)
    print("✓ Created prediction_accuracy table")
    
    # 6. Create indexes for performance
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_fixtures_date ON fixtures(date);
        CREATE INDEX IF NOT EXISTS idx_fixtures_season ON fixtures(season);
        CREATE INDEX IF NOT EXISTS idx_fixtures_teams ON fixtures(home_team, away_team);
        CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(prediction_date);
        CREATE INDEX IF NOT EXISTS idx_predictions_fixture ON predictions(fixture_id);
    """)
    print("✓ Created indexes")
    
    # 7. Create views for common queries
    cur.execute("""
        CREATE OR REPLACE VIEW upcoming_predictions AS
        SELECT 
            f.fixture_id,
            f.date,
            f.home_team,
            f.away_team,
            p.home_win_prob,
            p.draw_prob,
            p.away_win_prob,
            p.predicted_result,
            p.confidence,
            p.prediction_date
        FROM fixtures f
        JOIN predictions p ON f.fixture_id = p.fixture_id
        WHERE f.date >= CURRENT_DATE
        ORDER BY f.date, p.home_win_prob DESC;
    """)
    print("✓ Created upcoming_predictions view")
    
    cur.execute("""
        CREATE OR REPLACE VIEW prediction_performance AS
        SELECT 
            confidence,
            COUNT(*) as total_predictions,
            SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct_predictions,
            ROUND(AVG(CASE WHEN was_correct THEN 1.0 ELSE 0.0 END) * 100, 2) as accuracy_pct
        FROM prediction_accuracy
        GROUP BY confidence
        ORDER BY 
            CASE confidence 
                WHEN 'High' THEN 1 
                WHEN 'Medium' THEN 2 
                WHEN 'Low' THEN 3 
            END;
    """)
    print("✓ Created prediction_performance view")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("\n" + "="*70)
    print("DATABASE SETUP COMPLETE!")
    print("="*70)
    print("\nTables created:")
    print("  1. fixtures - Historical match data")
    print("  2. match_statistics - Match stats (shots, possession, etc)")
    print("  3. features - Engineered features for ML")
    print("  4. predictions - Model predictions")
    print("  5. prediction_accuracy - Track prediction performance")
    print("\nViews created:")
    print("  • upcoming_predictions - Easy access to future predictions")
    print("  • prediction_performance - Accuracy by confidence level")


def verify_setup():
    """Verify database setup"""
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    
    # Check tables exist
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    
    tables = cur.fetchall()
    print("\nVerifying tables:")
    for table in tables:
        print(f"  ✓ {table[0]}")
    
    # Check views exist
    cur.execute("""
        SELECT table_name 
        FROM information_schema.views 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    
    views = cur.fetchall()
    print("\nVerifying views:")
    for view in views:
        print(f"  ✓ {view[0]}")
    
    cur.close()
    conn.close()


if __name__ == "__main__":
    print("="*70)
    print("PREMIER LEAGUE PREDICTION SYSTEM - DATABASE SETUP")
    print("="*70)
    
    try:
        create_tables()
        verify_setup()
        
        print("\n" + "="*70)
        print("NEXT STEPS:")
        print("="*70)
        print("1. Migrate CSV data: python src/migrate_csv_to_postgres.py")
        print("2. Update scripts to use PostgreSQL")
        print("3. Test with: python src/predict_upcoming.py")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()