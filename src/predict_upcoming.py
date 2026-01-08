# predict_upcoming.py
"""
Generate predictions for upcoming Premier League fixtures
Uses trained Random Forest model to predict Home Win / Draw / Away Win probabilities
"""
import pandas as pd
import numpy as np
from datetime import datetime
import joblib
from api_football_collector import APIFootballCollector
from config import API_FOOTBALL_KEY, DB_PARAMS

def load_model_and_scaler():
    """Load trained model and scaler"""
    print("="*70)
    print("Loading trained model and scaler...")
    print("="*70)
    model = joblib.load('pl_model_random_forest_20260108.pkl')
    scaler = joblib.load('pl_scaler_20260108.pkl')
    print("✓ Model and scaler loaded\n")
    return model, scaler


def calculate_team_form(df, team_id, n_games=5, as_home=None):
    """
    Calculate rolling form for a team over last n_games
    Same function from build_all_features.py
    """
    # Filter to team's matches
    if as_home is None:
        team_matches = df[(df['home_team_id'] == team_id) | (df['away_team_id'] == team_id)].copy()
    elif as_home:
        team_matches = df[df['home_team_id'] == team_id].copy()
    else:
        team_matches = df[df['away_team_id'] == team_id].copy()
    
    # Sort by date
    team_matches = team_matches.sort_values('date')
    
    # Take last n games
    recent = team_matches.tail(n_games)
    
    if len(recent) == 0:
        return None
    
    # Calculate metrics for this team's perspective
    goals_for = []
    goals_against = []
    shots_for = []
    shots_against = []
    shots_on_target_for = []
    shots_on_target_against = []
    possession = []
    corners_for = []
    corners_against = []
    wins = 0
    draws = 0
    losses = 0
    
    for _, match in recent.iterrows():
        is_home = match['home_team_id'] == team_id
        
        if is_home:
            goals_for.append(match['home_goals'])
            goals_against.append(match['away_goals'])
            shots_for.append(match['home_shots'])
            shots_against.append(match['away_shots'])
            shots_on_target_for.append(match['home_shots_on_target'])
            shots_on_target_against.append(match['away_shots_on_target'])
            possession.append(match['home_possession'])
            corners_for.append(match['home_corners'])
            corners_against.append(match['away_corners'])
            
            if match['result'] == 'H':
                wins += 1
            elif match['result'] == 'D':
                draws += 1
            else:
                losses += 1
        else:
            goals_for.append(match['away_goals'])
            goals_against.append(match['home_goals'])
            shots_for.append(match['away_shots'])
            shots_against.append(match['home_shots'])
            shots_on_target_for.append(match['away_shots_on_target'])
            shots_on_target_against.append(match['home_shots_on_target'])
            possession.append(match['away_possession'])
            corners_for.append(match['away_corners'])
            corners_against.append(match['home_corners'])
            
            if match['result'] == 'A':
                wins += 1
            elif match['result'] == 'D':
                draws += 1
            else:
                losses += 1
    
    # Calculate advanced metrics
    total_shots = sum(shots_for)
    total_shots_on_target = sum(shots_on_target_for)
    total_goals = sum(goals_for)
    
    shot_accuracy = (total_shots_on_target / total_shots * 100) if total_shots > 0 else 0
    conversion_rate = (total_goals / total_shots_on_target * 100) if total_shots_on_target > 0 else 0
    shots_against_total = sum(shots_against)
    defensive_efficiency = (sum(goals_against) / shots_against_total) if shots_against_total > 0 else 0
    
    return {
        'games_played': len(recent),
        'wins': wins,
        'draws': draws,
        'losses': losses,
        'win_pct': wins / len(recent),
        'avg_goals_for': np.mean(goals_for),
        'avg_goals_against': np.mean(goals_against),
        'avg_shots_for': np.mean(shots_for),
        'avg_shots_against': np.mean(shots_against),
        'avg_shots_on_target_for': np.mean(shots_on_target_for),
        'avg_possession': np.mean(possession),
        'avg_corners_for': np.mean(corners_for),
        'goal_difference': sum(goals_for) - sum(goals_against),
        'shot_accuracy': shot_accuracy,
        'conversion_rate': conversion_rate,
        'defensive_efficiency': defensive_efficiency,
        'points': (wins * 3) + draws
    }


def calculate_features_for_fixture(fixture, historical_data):
    """Calculate all features for an upcoming fixture"""
    home_team_id = fixture['home_team_id']
    away_team_id = fixture['away_team_id']
    
    # Calculate team form
    home_form = calculate_team_form(historical_data, home_team_id, n_games=5, as_home=None)
    home_form_home = calculate_team_form(historical_data, home_team_id, n_games=5, as_home=True)
    away_form = calculate_team_form(historical_data, away_team_id, n_games=5, as_home=None)
    away_form_away = calculate_team_form(historical_data, away_team_id, n_games=5, as_home=False)
    
    if not all([home_form, home_form_home, away_form, away_form_away]):
        return None
    
    # Stage 2: Advanced metrics
    shot_accuracy_diff = home_form['shot_accuracy'] - away_form['shot_accuracy']
    conversion_diff = home_form['conversion_rate'] - away_form['conversion_rate']
    defensive_diff = away_form['defensive_efficiency'] - home_form['defensive_efficiency']
    
    home_poss_efficiency = home_form['avg_goals_for'] / home_form['avg_possession'] if home_form['avg_possession'] > 0 else 0
    away_poss_efficiency = away_form['avg_goals_for'] / away_form['avg_possession'] if away_form['avg_possession'] > 0 else 0
    poss_efficiency_diff = home_poss_efficiency - away_poss_efficiency
    
    home_corner_effectiveness = home_form['avg_goals_for'] / home_form['avg_corners_for'] if home_form['avg_corners_for'] > 0 else 0
    away_corner_effectiveness = away_form['avg_goals_for'] / away_form['avg_corners_for'] if away_form['avg_corners_for'] > 0 else 0
    
    # Stage 3: Match context
    form_diff = home_form['win_pct'] - away_form['win_pct']
    goal_diff_comparison = home_form['goal_difference'] - away_form['goal_difference']
    points_diff = home_form['points'] - away_form['points']
    home_advantage = home_form_home['win_pct'] - away_form_away['win_pct']
    home_attack_vs_away_defense = home_form['avg_goals_for'] - away_form['avg_goals_against']
    away_attack_vs_home_defense = away_form['avg_goals_for'] - home_form['avg_goals_against']
    
    # Build feature dict (MUST MATCH TRAINING ORDER!)
    features = {
        'home_win_pct_l5': home_form['win_pct'],
        'home_avg_goals_for_l5': home_form['avg_goals_for'],
        'home_avg_goals_against_l5': home_form['avg_goals_against'],
        'home_avg_shots_for_l5': home_form['avg_shots_for'],
        'home_avg_possession_l5': home_form['avg_possession'],
        'home_win_pct_home_l5': home_form_home['win_pct'],
        'home_avg_goals_for_home_l5': home_form_home['avg_goals_for'],
        'away_win_pct_l5': away_form['win_pct'],
        'away_avg_goals_for_l5': away_form['avg_goals_for'],
        'away_avg_goals_against_l5': away_form['avg_goals_against'],
        'away_avg_shots_for_l5': away_form['avg_shots_for'],
        'away_avg_possession_l5': away_form['avg_possession'],
        'away_win_pct_away_l5': away_form_away['win_pct'],
        'away_avg_goals_for_away_l5': away_form_away['avg_goals_for'],
        'home_shot_accuracy': home_form['shot_accuracy'],
        'away_shot_accuracy': away_form['shot_accuracy'],
        'shot_accuracy_diff': shot_accuracy_diff,
        'home_conversion_rate': home_form['conversion_rate'],
        'away_conversion_rate': away_form['conversion_rate'],
        'conversion_diff': conversion_diff,
        'home_defensive_efficiency': home_form['defensive_efficiency'],
        'away_defensive_efficiency': away_form['defensive_efficiency'],
        'defensive_diff': defensive_diff,
        'home_poss_efficiency': home_poss_efficiency,
        'away_poss_efficiency': away_poss_efficiency,
        'poss_efficiency_diff': poss_efficiency_diff,
        'home_corner_effectiveness': home_corner_effectiveness,
        'away_corner_effectiveness': away_corner_effectiveness,
        'form_diff': form_diff,
        'goal_diff_comparison': goal_diff_comparison,
        'points_diff': points_diff,
        'home_advantage': home_advantage,
        'home_attack_vs_away_defense': home_attack_vs_away_defense,
        'away_attack_vs_home_defense': away_attack_vs_home_defense,
        'home_recent_points': home_form['points'],
        'away_recent_points': away_form['points']
    }
    
    return features


def get_confidence_level(max_prob):
    """Determine confidence level based on max probability"""
    if max_prob >= 0.60:
        return "High Confidence"
    elif max_prob >= 0.50:
        return "Medium Confidence"
    else:
        return "Low Confidence"


def main():
    print("="*70)
    print("PREMIER LEAGUE UPCOMING FIXTURE PREDICTIONS")
    print("="*70)
    
    # Load model
    model, scaler = load_model_and_scaler()
    
    # Initialize collector
    collector = APIFootballCollector(API_FOOTBALL_KEY, DB_PARAMS)
    
    # Get upcoming fixtures
    print("Fetching upcoming fixtures...")
    upcoming = collector.get_upcoming_fixtures(days_ahead=14)
    
    if upcoming.empty:
        print("✗ No upcoming fixtures found in next 14 days")
        return
    
    print(f"✓ Found {len(upcoming)} upcoming fixtures\n")
    
    # Load historical data
    print("Loading historical data for feature calculation...")
    historical = pd.read_csv('pl_historical_enriched_20260108.csv')
    historical['date'] = pd.to_datetime(historical['date'])
    print(f"✓ Loaded {len(historical)} historical fixtures\n")
    
    # Generate predictions
    print("="*70)
    print("GENERATING PREDICTIONS")
    print("="*70)
    predictions = []
    
    for idx, fixture in upcoming.iterrows():
        print(f"\n{fixture['home_team']} vs {fixture['away_team']}")
        print(f"Date: {fixture['date']}")
        print(f"Venue: {fixture['venue']}")
        
        # Calculate features
        features = calculate_features_for_fixture(fixture, historical)
        
        if not features:
            print("  ✗ Insufficient historical data for prediction")
            continue
        
        # Convert to array and scale
        feature_array = np.array(list(features.values())).reshape(1, -1)
        feature_scaled = scaler.transform(feature_array)
        
        # Predict probabilities
        proba = model.predict_proba(feature_scaled)[0]
        
        # proba order: [Home Win, Draw, Away Win]
        home_win_prob = proba[0]
        draw_prob = proba[1]
        away_win_prob = proba[2]
        
        # Determine predicted outcome and confidence
        max_prob = max(home_win_prob, draw_prob, away_win_prob)
        confidence = get_confidence_level(max_prob)
        
        if home_win_prob == max_prob:
            predicted_result = "Home Win"
        elif draw_prob == max_prob:
            predicted_result = "Draw"
        else:
            predicted_result = "Away Win"
        
        # Display predictions
        print(f"\n  🏆 Predicted: {predicted_result} ({max_prob*100:.1f}%)")
        print(f"  📊 Confidence: {confidence}")
        print(f"\n  Probabilities:")
        print(f"    Home Win: {home_win_prob*100:.1f}%")
        print(f"    Draw:     {draw_prob*100:.1f}%")
        print(f"    Away Win: {away_win_prob*100:.1f}%")
        
        predictions.append({
            'fixture_id': fixture['fixture_id'],
            'date': fixture['date'],
            'home_team': fixture['home_team'],
            'away_team': fixture['away_team'],
            'venue': fixture['venue'],
            'home_win_prob': round(home_win_prob * 100, 1),
            'draw_prob': round(draw_prob * 100, 1),
            'away_win_prob': round(away_win_prob * 100, 1),
            'predicted_result': predicted_result,
            'confidence': confidence,
            'max_probability': round(max_prob * 100, 1)
        })
    
    # Save predictions
    if predictions:
        pred_df = pd.DataFrame(predictions)
        output_file = f"pl_predictions_{datetime.now().strftime('%Y%m%d')}.csv"
        pred_df.to_csv(output_file, index=False)
        
        print(f"\n{'='*70}")
        print("PREDICTIONS SUMMARY")
        print(f"{'='*70}")
        print(f"✓ Generated predictions for {len(predictions)} fixtures")
        print(f"✓ Saved to: {output_file}\n")
        
        print(pred_df[['date', 'home_team', 'away_team', 'predicted_result', 
                       'max_probability', 'confidence']])
    else:
        print("\n✗ No predictions generated")

if __name__ == "__main__":
    main()
