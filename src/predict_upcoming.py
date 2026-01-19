# predict_upcoming.py
"""
Generate predictions for upcoming Premier League fixtures using PostgreSQL
"""
import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
import joblib
import os
from datetime import datetime, timedelta
from config import DB_PARAMS
from paths import MODELS_DIR

def select_latest_model():
    """Find the most recent trained model"""
    model_files = [f for f in os.listdir(MODELS_DIR) if f.startswith('pl_model_') and f.endswith('.pkl')]
    if not model_files:
        raise FileNotFoundError(f"No model files found in {MODELS_DIR}")
    
    latest_model = max(model_files, key=lambda f: os.path.getmtime(os.path.join(MODELS_DIR, f)))
    model_path = os.path.join(MODELS_DIR, latest_model)
    
    # Find corresponding scaler
    timestamp = latest_model.split('_')[-1].replace('.pkl', '')
    scaler_path = os.path.join(MODELS_DIR, f'pl_scaler_{timestamp}.pkl')
    
    if not os.path.exists(scaler_path):
        raise FileNotFoundError(f"Scaler not found: {scaler_path}")
    
    return model_path, scaler_path

def load_model():
    """Load trained model and scaler"""
    print("="*70)
    print("LOADING MODEL")
    print("="*70)
    
    model_path, scaler_path = select_latest_model()
    
    print(f"\nModel: {os.path.basename(model_path)}")
    print(f"Scaler: {os.path.basename(scaler_path)}")
    
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    
    print("✓ Model and scaler loaded")
    
    return model, scaler, os.path.basename(model_path)

def get_upcoming_fixtures():
    """Fetch upcoming fixtures from PostgreSQL"""
    print("\n" + "="*70)
    print("FETCHING UPCOMING FIXTURES")
    print("="*70)
    
    conn = psycopg2.connect(**DB_PARAMS)
    
    # Get fixtures in the next 14 days that don't have results yet
    query = """
        SELECT 
            fixture_id,
            date,
            home_team,
            away_team,
            home_team_id,
            away_team_id
        FROM fixtures
        WHERE date >= CURRENT_DATE
        AND date <= CURRENT_DATE + INTERVAL '14 days'
        AND result IS NULL
        ORDER BY date
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    print(f"\n✓ Found {len(df)} upcoming fixtures")
    
    if len(df) > 0:
        print("\nUpcoming matches:")
        for _, row in df.head(10).iterrows():
            print(f"  {row['date']}: {row['home_team']} vs {row['away_team']}")
    
    return df

def calculate_team_features(team_id, is_home=True, lookback=5):
    """Calculate features for a team based on recent matches"""
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    
    # Get team's recent matches (overall)
    cur.execute("""
        SELECT 
            f.fixture_id,
            f.date,
            f.home_team_id,
            f.away_team_id,
            f.home_goals,
            f.away_goals,
            f.result,
            ms.home_shots,
            ms.away_shots,
            ms.home_shots_on_target,
            ms.away_shots_on_target,
            ms.home_possession,
            ms.away_possession,
            ms.home_corners,
            ms.away_corners
        FROM fixtures f
        LEFT JOIN match_statistics ms ON f.fixture_id = ms.fixture_id
        WHERE (f.home_team_id = %s OR f.away_team_id = %s)
        AND f.result IS NOT NULL
        AND f.date < CURRENT_DATE
        ORDER BY f.date DESC
        LIMIT %s
    """, (team_id, team_id, lookback))
    
    overall_matches = cur.fetchall()
    
    # Get team's recent home/away matches
    if is_home:
        cur.execute("""
            SELECT 
                f.home_goals, f.away_goals, f.result,
                ms.home_shots, ms.home_shots_on_target,
                ms.home_possession, ms.home_corners
            FROM fixtures f
            LEFT JOIN match_statistics ms ON f.fixture_id = ms.fixture_id
            WHERE f.home_team_id = %s
            AND f.result IS NOT NULL
            AND f.date < CURRENT_DATE
            ORDER BY f.date DESC
            LIMIT %s
        """, (team_id, lookback))
    else:
        cur.execute("""
            SELECT 
                f.away_goals, f.home_goals, f.result,
                ms.away_shots, ms.away_shots_on_target,
                ms.away_possession, ms.away_corners
            FROM fixtures f
            LEFT JOIN match_statistics ms ON f.fixture_id = ms.fixture_id
            WHERE f.away_team_id = %s
            AND f.result IS NOT NULL
            AND f.date < CURRENT_DATE
            ORDER BY f.date DESC
            LIMIT %s
        """, (team_id, lookback))
    
    venue_matches = cur.fetchall()
    
    cur.close()
    conn.close()
    
    # Calculate overall features
    if len(overall_matches) < lookback:
        return None  # Not enough data
    
    goals_for = []
    goals_against = []
    shots_for = []
    shots_on_target = []
    possession = []
    corners = []
    wins = 0
    points = 0
    
    for match in overall_matches:
        _, _, home_id, away_id, home_goals, away_goals, result, \
        home_shots, away_shots, home_sot, away_sot, home_poss, away_poss, \
        home_corners, away_corners = match
        
        if home_id == team_id:  # Team was home
            goals_for.append(home_goals or 0)
            goals_against.append(away_goals or 0)
            shots_for.append(home_shots or 0)
            shots_on_target.append(home_sot or 0)
            possession.append(home_poss or 50)
            corners.append(home_corners or 0)
            if result == 'H':
                wins += 1
                points += 3
            elif result == 'D':
                points += 1
        else:  # Team was away
            goals_for.append(away_goals or 0)
            goals_against.append(home_goals or 0)
            shots_for.append(away_shots or 0)
            shots_on_target.append(away_sot or 0)
            possession.append(away_poss or 50)
            corners.append(away_corners or 0)
            if result == 'A':
                wins += 1
                points += 3
            elif result == 'D':
                points += 1
    
    # Calculate venue-specific features
    venue_goals = []
    venue_wins = 0
    
    if len(venue_matches) >= 3:  # Need at least 3 venue matches
        for match in venue_matches:
            gf, ga, result, _, _, _, _ = match
            venue_goals.append(gf or 0)
            if (is_home and result == 'H') or (not is_home and result == 'A'):
                venue_wins += 1
    
    # Aggregated metrics
    avg_goals_for = np.mean(goals_for)
    avg_goals_against = np.mean(goals_against)
    avg_shots = np.mean(shots_for)
    avg_possession = np.mean(possession)
    
    total_shots = sum(shots_for)
    total_sot = sum(shots_on_target)
    shot_accuracy = (total_sot / total_shots * 100) if total_shots > 0 else 0
    
    total_goals = sum(goals_for)
    conversion_rate = (total_goals / total_shots * 100) if total_shots > 0 else 0
    
    defensive_efficiency = max(0, 100 - (avg_goals_against / max(avg_goals_for, 0.1) * 100))
    
    poss_efficiency = (avg_goals_for / max(avg_possession, 1) * 100) if avg_possession > 0 else 0
    
    total_corners = sum(corners)
    corner_effectiveness = (total_goals / total_corners * 100) if total_corners > 0 else 0
    
    win_pct = wins / lookback
    
    avg_venue_goals = np.mean(venue_goals) if venue_goals else avg_goals_for
    venue_win_pct = venue_wins / len(venue_matches) if venue_matches else win_pct
    
    return {
        'win_pct_l5': win_pct,
        'avg_goals_for_l5': avg_goals_for,
        'avg_goals_against_l5': avg_goals_against,
        'avg_shots_for_l5': avg_shots,
        'avg_possession_l5': avg_possession,
        'win_pct_venue_l5': venue_win_pct,
        'avg_goals_for_venue_l5': avg_venue_goals,
        'shot_accuracy': shot_accuracy,
        'conversion_rate': conversion_rate,
        'defensive_efficiency': defensive_efficiency,
        'poss_efficiency': poss_efficiency,
        'corner_effectiveness': corner_effectiveness,
        'recent_points': points
    }


def build_prediction_features(upcoming_fixtures):
    
    """Build feature set for upcoming fixtures matching training format"""
    print("\n" + "="*70)
    print("BUILDING FEATURES FOR PREDICTION")
    print("="*70)
    
    features_list = []
    
    for _, fixture in upcoming_fixtures.iterrows():
        # Get features for both teams
        home_features = calculate_team_features(fixture['home_team_id'], is_home=True)
        away_features = calculate_team_features(fixture['away_team_id'], is_home=False)
        
        if home_features is None or away_features is None:
            print(f"⚠ Skipping {fixture['home_team']} vs {fixture['away_team']} - insufficient data")
            continue
        
        # Build feature dictionary matching EXACT training column names
        feature_dict = {
            # Team form features (last 5 games)
            'home_win_pct_l5': home_features['win_pct_l5'],
            'home_avg_goals_for_l5': home_features['avg_goals_for_l5'],
            'home_avg_goals_against_l5': home_features['avg_goals_against_l5'],
            'home_avg_shots_for_l5': home_features['avg_shots_for_l5'],
            'home_avg_possession_l5': home_features['avg_possession_l5'],
            'home_win_pct_home_l5': home_features['win_pct_venue_l5'],
            'home_avg_goals_for_home_l5': home_features['avg_goals_for_venue_l5'],
            
            'away_win_pct_l5': away_features['win_pct_l5'],
            'away_avg_goals_for_l5': away_features['avg_goals_for_l5'],
            'away_avg_goals_against_l5': away_features['avg_goals_against_l5'],
            'away_avg_shots_for_l5': away_features['avg_shots_for_l5'],
            'away_avg_possession_l5': away_features['avg_possession_l5'],
            'away_win_pct_away_l5': away_features['win_pct_venue_l5'],
            'away_avg_goals_for_away_l5': away_features['avg_goals_for_venue_l5'],
            
            # Advanced metrics
            'home_shot_accuracy': home_features['shot_accuracy'],
            'away_shot_accuracy': away_features['shot_accuracy'],
            'shot_accuracy_diff': home_features['shot_accuracy'] - away_features['shot_accuracy'],
            
            'home_conversion_rate': home_features['conversion_rate'],
            'away_conversion_rate': away_features['conversion_rate'],
            'conversion_diff': home_features['conversion_rate'] - away_features['conversion_rate'],
            
            'home_defensive_efficiency': home_features['defensive_efficiency'],
            'away_defensive_efficiency': away_features['defensive_efficiency'],
            'defensive_diff': home_features['defensive_efficiency'] - away_features['defensive_efficiency'],
            
            'home_poss_efficiency': home_features['poss_efficiency'],
            'away_poss_efficiency': away_features['poss_efficiency'],
            'poss_efficiency_diff': home_features['poss_efficiency'] - away_features['poss_efficiency'],
            
            'home_corner_effectiveness': home_features['corner_effectiveness'],
            'away_corner_effectiveness': away_features['corner_effectiveness'],
            
            # Match context
            'form_diff': home_features['win_pct_l5'] - away_features['win_pct_l5'],
            'goal_diff_comparison': home_features['avg_goals_for_l5'] - away_features['avg_goals_for_l5'],
            'points_diff': home_features['recent_points'] - away_features['recent_points'],
            'home_advantage': 1.0,  # Always 1 for home team
            'home_attack_vs_away_defense': home_features['avg_goals_for_l5'] - away_features['avg_goals_against_l5'],
            'away_attack_vs_home_defense': away_features['avg_goals_for_l5'] - home_features['avg_goals_against_l5'],
            'home_recent_points': home_features['recent_points'],
            'away_recent_points': away_features['recent_points']
        }
        
        features_list.append(feature_dict)
    
    features_df = pd.DataFrame(features_list)
    print(f"✓ Built {len(features_df)} feature sets")
    
    # Ensure column order matches training (important for some models)
    expected_cols = [
        'home_win_pct_l5', 'home_avg_goals_for_l5', 'home_avg_goals_against_l5',
        'home_avg_shots_for_l5', 'home_avg_possession_l5', 'home_win_pct_home_l5',
        'home_avg_goals_for_home_l5', 'away_win_pct_l5', 'away_avg_goals_for_l5',
        'away_avg_goals_against_l5', 'away_avg_shots_for_l5', 'away_avg_possession_l5',
        'away_win_pct_away_l5', 'away_avg_goals_for_away_l5', 'home_shot_accuracy',
        'away_shot_accuracy', 'shot_accuracy_diff', 'home_conversion_rate',
        'away_conversion_rate', 'conversion_diff', 'home_defensive_efficiency',
        'away_defensive_efficiency', 'defensive_diff', 'home_poss_efficiency',
        'away_poss_efficiency', 'poss_efficiency_diff', 'home_corner_effectiveness',
        'away_corner_effectiveness', 'form_diff', 'goal_diff_comparison',
        'points_diff', 'home_advantage', 'home_attack_vs_away_defense',
        'away_attack_vs_home_defense', 'home_recent_points', 'away_recent_points'
    ]
    
    features_df = features_df[expected_cols]

    print("\nDEBUG: Sample feature values")
    print(features_df.head(1).T)
    print("Feature Stats:")
    print(features_df.describe())
    
    return features_df

def generate_predictions(model, scaler, upcoming_fixtures, features_df):
    """Generate predictions for upcoming fixtures"""
    print("\n" + "="*70)
    print("GENERATING PREDICTIONS")
    print("="*70)
    
    # Scale features
    features_scaled = scaler.transform(features_df)
    
    # Predict probabilities
    probabilities = model.predict_proba(features_scaled)
    predictions = model.predict(features_scaled)
    
    # Map back to H/D/A
    result_mapping = {0: 'H', 1: 'D', 2: 'A'}
    
    # Build results dataframe
    results = upcoming_fixtures.copy()
    results['home_win_prob'] = probabilities[:, 0] * 100
    results['draw_prob'] = probabilities[:, 1] * 100
    results['away_win_prob'] = probabilities[:, 2] * 100
    results['predicted_result'] = [result_mapping[p] for p in predictions]
    
    # Calculate confidence
    max_probs = probabilities.max(axis=1) * 100
    results['confidence'] = pd.cut(
        max_probs,
        bins=[0, 50, 60, 100],
        labels=['Low', 'Medium', 'High']
    )
    
    print(f"✓ Generated {len(results)} predictions")
    
    return results

def save_predictions_to_db(predictions, model_version):
    """Save predictions to PostgreSQL"""
    print("\n" + "="*70)
    print("SAVING PREDICTIONS TO DATABASE")
    print("="*70)
    
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    
    prediction_date = datetime.now().date()
    
    predictions_data = []
    for _, row in predictions.iterrows():
        predictions_data.append((
            int(row['fixture_id']),
            prediction_date,
            float(row['home_win_prob']),
            float(row['draw_prob']),
            float(row['away_win_prob']),
            row['predicted_result'],
            row['confidence'],
            model_version
        ))
    
    execute_values(cur, """
        INSERT INTO predictions (
            fixture_id, prediction_date, home_win_prob, draw_prob, away_win_prob,
            predicted_result, confidence, model_version
        ) VALUES %s
        ON CONFLICT (fixture_id, prediction_date) DO UPDATE SET
            home_win_prob = EXCLUDED.home_win_prob,
            draw_prob = EXCLUDED.draw_prob,
            away_win_prob = EXCLUDED.away_win_prob,
            predicted_result = EXCLUDED.predicted_result,
            confidence = EXCLUDED.confidence,
            model_version = EXCLUDED.model_version
    """, predictions_data)
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"✓ Saved {len(predictions_data)} predictions to database")

def display_predictions(predictions):
    """Display predictions in a nice format"""
    print("\n" + "="*70)
    print("PREDICTIONS SUMMARY")
    print("="*70)
    
    for _, row in predictions.iterrows():
        print(f"\n{row['date']}")
        print(f"{row['home_team']} vs {row['away_team']}")
        print(f"  Home Win: {row['home_win_prob']:.1f}%")
        print(f"  Draw:     {row['draw_prob']:.1f}%")
        print(f"  Away Win: {row['away_win_prob']:.1f}%")
        print(f"  Prediction: {row['predicted_result']} ({row['confidence']} confidence)")

def main():
    print("="*70)
    print("PREMIER LEAGUE MATCH PREDICTION SYSTEM")
    print("Using PostgreSQL Database")
    print("="*70)
    
    try:
        # Load model
        model, scaler, model_version = load_model()
        
        # Get upcoming fixtures
        upcoming = get_upcoming_fixtures()
        
        if len(upcoming) == 0:
            print("\n✗ No upcoming fixtures found in next 14 days")
            return
        
        # Build features
        features = build_prediction_features(upcoming)
        
        # Generate predictions
        predictions = generate_predictions(model, scaler, upcoming, features)
        
        # Save to database
        save_predictions_to_db(predictions, model_version)
        
        # Display results
        display_predictions(predictions)
        
        print("\n" + "="*70)
        print("PREDICTION COMPLETE!")
        print("="*70)
        print("\nPredictions saved to PostgreSQL database")
        print("Query them with: SELECT * FROM upcoming_predictions;")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()