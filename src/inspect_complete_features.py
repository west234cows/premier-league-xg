# inspect_complete_features.py
"""
Inspect complete features dataset
"""
import pandas as pd

# Load complete features
df = pd.read_csv('pl_features_complete_20260108.csv')

print("="*70)
print("COMPLETE FEATURES INSPECTION")
print("="*70)

print(f"\nTotal matches: {len(df)}")
print(f"Total features: {len(df.columns)}")

print("\n" + "="*70)
print("SAMPLE MATCH (Full Feature Set)")
print("="*70)
sample = df.iloc[5]  # Pick a match with some history
print(f"\nMatch: {sample['home_team']} vs {sample['away_team']}")
print(f"Result: {sample['result']}")
print(f"\n--- STAGE 1: TEAM FORM ---")
print(f"Home Win % (L5): {sample['home_win_pct_l5']:.1%}")
print(f"Away Win % (L5): {sample['away_win_pct_l5']:.1%}")
print(f"Home Avg Goals For: {sample['home_avg_goals_for_l5']:.2f}")
print(f"Away Avg Goals For: {sample['away_avg_goals_for_l5']:.2f}")

print(f"\n--- STAGE 2: ADVANCED METRICS ---")
print(f"Home Shot Accuracy: {sample['home_shot_accuracy']:.1f}%")
print(f"Away Shot Accuracy: {sample['away_shot_accuracy']:.1f}%")
print(f"Shot Accuracy Diff: {sample['shot_accuracy_diff']:.1f}%")
print(f"Home Conversion Rate: {sample['home_conversion_rate']:.1f}%")
print(f"Away Conversion Rate: {sample['away_conversion_rate']:.1f}%")

print(f"\n--- STAGE 3: MATCH CONTEXT ---")
print(f"Form Differential: {sample['form_diff']:.2f}")
print(f"Home Advantage: {sample['home_advantage']:.2f}")
print(f"Points Diff: {sample['points_diff']:.0f}")
print(f"Home Attack vs Away Defense: {sample['home_attack_vs_away_defense']:.2f}")

print("\n" + "="*70)
print("MISSING DATA CHECK")
print("="*70)
missing = df.isnull().sum()
if missing.sum() == 0:
    print("✓ No missing data!")
else:
    print(missing[missing > 0])

print("\n" + "="*70)
print("FEATURE STATISTICS (Key Metrics)")
print("="*70)
print(df[['home_win_pct_l5', 'away_win_pct_l5', 
          'shot_accuracy_diff', 'conversion_diff',
          'form_diff', 'points_diff']].describe())

print("\n" + "="*70)
print("RESULTS DISTRIBUTION")
print("="*70)
print(df['result'].value_counts())
print("\nProportions:")
print(df['result'].value_counts(normalize=True))
