# inspect_features.py
"""
Inspect Stage 1 features
"""
import pandas as pd

# Load features
df = pd.read_csv('pl_features_stage1_20260108.csv')

print("="*70)
print("STAGE 1 FEATURES INSPECTION")
print("="*70)

print(f"\nTotal matches with features: {len(df)}")

print("\n" + "="*70)
print("SAMPLE MATCHES")
print("="*70)
print(df[['home_team', 'away_team', 'result', 
          'home_win_pct_l5', 'away_win_pct_l5',
          'home_avg_goals_for_l5', 'away_avg_goals_for_l5']].head(10))

print("\n" + "="*70)
print("FEATURE STATISTICS")
print("="*70)
print(df[['home_win_pct_l5', 'home_avg_goals_for_l5', 
          'home_avg_goals_against_l5', 'home_avg_shots_for_l5',
          'away_win_pct_l5', 'away_avg_goals_for_l5']].describe())

print("\n" + "="*70)
print("RESULTS DISTRIBUTION")
print("="*70)
print(df['result'].value_counts())
print(df['result'].value_counts(normalize=True))

print("\n" + "="*70)
print("CHECK FOR MISSING VALUES")
print("="*70)
print(df.isnull().sum())
