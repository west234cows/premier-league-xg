# inspect_enriched_data.py
"""
Quick inspection of enriched historical data
"""
import pandas as pd

# Load enriched data
df = pd.read_csv('pl_historical_enriched_20260108.csv')

print("="*70)
print("ENRICHED DATA INSPECTION")
print("="*70)

print(f"\nTotal rows: {len(df)}")
print(f"Total columns: {len(df.columns)}")

print("\n" + "="*70)
print("COLUMN NAMES")
print("="*70)
for col in df.columns:
    print(f"  - {col}")

print("\n" + "="*70)
print("SAMPLE DATA (First 3 Matches)")
print("="*70)
print(df[['home_team', 'away_team', 'home_goals', 'away_goals', 
          'home_shots', 'away_shots', 'home_possession', 'result']].head(3))

print("\n" + "="*70)
print("MISSING DATA CHECK")
print("="*70)
print(df.isnull().sum())

print("\n" + "="*70)
print("BASIC STATISTICS")
print("="*70)
print(df[['home_goals', 'away_goals', 'home_shots', 'away_shots', 
          'home_possession']].describe())

print("\n" + "="*70)
print("Results Distribution")
print("="*70)
print(df['result'].value_counts())
print(df['result'].value_counts(normalize=True))


