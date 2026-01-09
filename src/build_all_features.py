# build_all_features.py
"""
Complete Feature Engineering Pipeline - All 3 Stages
Builds predictive features for Premier League win probability model
"""
import pandas as pd
import numpy as np
from datetime import datetime
import os
from paths import DATA_DIR,require_dirs

def select_latest_enriched() -> str:
    files = [f for f in os.listdir(DATA_DIR) if f.startswith("pl_historical_enriched_") and f.endswith(".csv")]
    if not files:
        raise FileNotFoundError(f"No enriched files found in {DATA_DIR}")
    try:
        latest = max(files, key=lambda x: x.rsplit("_", 1)[-1].split(".")[0])  # pick by YYYYMMDD
    except Exception:
        latest = max(files, key=lambda f: os.path.getmtime(os.path.join(DATA_DIR, f)))  # fallback by mtime
    return os.path.join(DATA_DIR, latest)

def calculate_team_form(df, team_id, n_games=5, as_home=None):
    """
    Calculate rolling form for a team over last n_games
    
    Args:
        df: Historical fixtures dataframe
        team_id: Team ID to calculate form for
        n_games: Number of recent games to consider
        as_home: None (all games), True (home only), False (away only)
    
    Returns:
        Dict with form metrics
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
    
    # Shot accuracy (shots on target / total shots)
    shot_accuracy = (total_shots_on_target / total_shots * 100) if total_shots > 0 else 0
    
    # Conversion rate (goals / shots on target)
    conversion_rate = (total_goals / total_shots_on_target * 100) if total_shots_on_target > 0 else 0
    
    # Defensive efficiency (goals conceded per shot against)
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
        'points': (wins * 3) + draws  # League points from recent form
    }


def build_complete_features(fixtures_df):
    """
    Build all features (Stages 1, 2, 3) for each match
    """
    print("Building complete feature set (Stages 1, 2, 3)...")
    
    # Sort by date to process chronologically
    fixtures_df = fixtures_df.sort_values('date').reset_index(drop=True)
    
    feature_rows = []
    
    for idx, match in fixtures_df.iterrows():
        # Get all matches before this one for form calculation
        prior_matches = fixtures_df[fixtures_df['date'] < match['date']]
        
        if len(prior_matches) < 10:  # Need some history
            continue
        
        # ====== STAGE 1: TEAM FORM FEATURES ======
        
        # Home team form (all games, last 5)
        home_form = calculate_team_form(prior_matches, match['home_team_id'], n_games=5, as_home=None)
        # Home team home-specific form (last 5 home games)
        home_form_home = calculate_team_form(prior_matches, match['home_team_id'], n_games=5, as_home=True)
        
        # Away team form (all games, last 5)
        away_form = calculate_team_form(prior_matches, match['away_team_id'], n_games=5, as_home=None)
        # Away team away-specific form (last 5 away games)
        away_form_away = calculate_team_form(prior_matches, match['away_team_id'], n_games=5, as_home=False)
        
        if not all([home_form, home_form_home, away_form, away_form_away]):
            continue
        
        # ====== STAGE 2: ADVANCED PERFORMANCE METRICS ======
        
        # Shot accuracy differential
        shot_accuracy_diff = home_form['shot_accuracy'] - away_form['shot_accuracy']
        
        # Conversion rate differential
        conversion_diff = home_form['conversion_rate'] - away_form['conversion_rate']
        
        # Defensive strength comparison
        defensive_diff = away_form['defensive_efficiency'] - home_form['defensive_efficiency']  # Lower is better for defense
        
        # Possession efficiency (goals per % possession)
        home_poss_efficiency = home_form['avg_goals_for'] / home_form['avg_possession'] if home_form['avg_possession'] > 0 else 0
        away_poss_efficiency = away_form['avg_goals_for'] / away_form['avg_possession'] if away_form['avg_possession'] > 0 else 0
        poss_efficiency_diff = home_poss_efficiency - away_poss_efficiency
        
        # Corner effectiveness (goals per corner)
        home_corner_effectiveness = home_form['avg_goals_for'] / home_form['avg_corners_for'] if home_form['avg_corners_for'] > 0 else 0
        away_corner_effectiveness = away_form['avg_goals_for'] / away_form['avg_corners_for'] if away_form['avg_corners_for'] > 0 else 0
        
        
        # ====== STAGE 3: MATCH CONTEXT FEATURES ======
        
        # Form differential (overall)
        form_diff = home_form['win_pct'] - away_form['win_pct']
        
        # Goal difference differential
        goal_diff_comparison = home_form['goal_difference'] - away_form['goal_difference']
        
        # Points differential (recent form strength)
        points_diff = home_form['points'] - away_form['points']
        
        # Home advantage factor (home form vs away form)
        home_advantage = home_form_home['win_pct'] - away_form_away['win_pct']
        
        # Attack vs Defense matchup
        home_attack_vs_away_defense = home_form['avg_goals_for'] - away_form['avg_goals_against']
        away_attack_vs_home_defense = away_form['avg_goals_for'] - home_form['avg_goals_against']
        
        # Momentum indicators
        home_recent_points = home_form['points']
        away_recent_points = away_form['points']
        
        
        # Build feature row
        features = {
            'fixture_id': match['fixture_id'],
            'date': match['date'],
            'season': match['season'],
            'home_team': match['home_team'],
            'away_team': match['away_team'],
            'result': match['result'],
            
            # ====== STAGE 1: TEAM FORM ======
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
            
            # ====== STAGE 2: ADVANCED METRICS ======
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
            
            # ====== STAGE 3: MATCH CONTEXT ======
            'form_diff': form_diff,
            'goal_diff_comparison': goal_diff_comparison,
            'points_diff': points_diff,
            'home_advantage': home_advantage,
            'home_attack_vs_away_defense': home_attack_vs_away_defense,
            'away_attack_vs_home_defense': away_attack_vs_home_defense,
            'home_recent_points': home_recent_points,
            'away_recent_points': away_recent_points
        }
        
        feature_rows.append(features)
        
        # Progress indicator
        if (idx + 1) % 100 == 0:
            print(f"  Processed {idx + 1}/{len(fixtures_df)} matches...")
    
    print(f"✓ Built complete features for {len(feature_rows)} matches")
    return pd.DataFrame(feature_rows)


def main():
    print("="*70)
    print("COMPLETE FEATURE ENGINEERING PIPELINE")
    print("Stages 1, 2, 3: Team Form + Advanced Metrics + Match Context")
    print("="*70)

    require_dirs(assert_only=True)

    # Load enriched data from data/
    print("\nLoading enriched data...")
    enriched_path = select_latest_enriched()
    df = pd.read_csv(enriched_path)
    print(f"✓ Loaded {len(df)} fixtures from {enriched_path}")

    # Convert date to datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Build all features
    features_df = build_complete_features(df)
    
    # Save to data/
    output_path = os.path.join(DATA_DIR, f"pl_features_complete_{datetime.now().strftime('%Y%m%d')}.csv")
    features_df.to_csv(output_path, index=False)
    
    print(f"\n{'='*70}")
    print("FEATURE ENGINEERING COMPLETE")
    print(f"{'='*70}")
    print(f"Total matches with features: {len(features_df)}")
    
    print(f"\n{'='*70}")
    print("FEATURE SUMMARY")
    print(f"{'='*70}")
    
    stage1_features = [c for c in features_df.columns if any(x in c for x in ['win_pct', 'avg_goals', 'avg_shots', 'avg_possession'])]
    stage2_features = [c for c in features_df.columns if any(x in c for x in ['accuracy', 'conversion', 'defensive_efficiency', 'poss_efficiency', 'corner_effectiveness'])]
    stage3_features = [c for c in features_df.columns if any(x in c for x in ['diff', 'advantage', 'attack_vs', 'points'])]
    
    print(f"\nStage 1 - Team Form Features ({len(stage1_features)}):")
    for f in stage1_features[:5]:
        print(f"  - {f}")
    print(f"  ... and {len(stage1_features) - 5} more")
    
    print(f"\nStage 2 - Advanced Metrics ({len(stage2_features)}):")
    for f in stage2_features:
        print(f"  - {f}")
    
    print(f"\nStage 3 - Match Context ({len(stage3_features)}):")
    for f in stage3_features:
        print(f"  - {f}")
    
    print(f"\n✓ Saved to: {output_path}")
    
    # Show sample
    print(f"\n{'='*70}")
    print("SAMPLE FEATURES (first match):")
    print(f"{'='*70}")
    sample = features_df.iloc[0]
    print(f"\nMatch: {sample['home_team']} vs {sample['away_team']}")
    print(f"Result: {sample['result']}")
    print(f"\nForm:")
    print(f"  Home Win % (L5): {sample['home_win_pct_l5']:.1%}")
    print(f"  Away Win % (L5): {sample['away_win_pct_l5']:.1%}")
    print(f"\nAdvanced:")
    print(f"  Shot Accuracy Diff: {sample['shot_accuracy_diff']:.1f}%")
    print(f"  Conversion Diff: {sample['conversion_diff']:.1f}%")
    print(f"\nContext:")
    print(f"  Form Differential: {sample['form_diff']:.2f}")
    print(f"  Home Advantage: {sample['home_advantage']:.2f}")
    
    print(f"\n{'='*70}")
    print("NEXT STEPS")
    print(f"{'='*70}")
    print("1. Review the complete features CSV")
    print("2. We'll train machine learning models")
    print("3. Then make predictions on upcoming fixtures!")

if __name__ == "__main__":
    main()
