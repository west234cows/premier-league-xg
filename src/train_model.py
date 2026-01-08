# train_model.py
"""
Train Premier League Win Probability Models
Part 1: Data Preparation and Model Training
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, log_loss
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import joblib

def prepare_data(features_file):
    """Load and prepare data for modeling"""
    print("="*70)
    print("DATA PREPARATION")
    print("="*70)
    
    # Load features
    print("\nLoading feature data...")
    df = pd.read_csv(features_file)
    print(f"✓ Loaded {len(df)} matches")
    
    # Define feature columns (exclude metadata and target)
    feature_cols = [col for col in df.columns if col not in 
                   ['fixture_id', 'date', 'season', 'home_team', 'away_team', 'result']]
    
    print(f"\nTotal features: {len(feature_cols)}")
    
    # Separate features and target
    X = df[feature_cols]
    y = df['result']
    
    # Encode target: H=0, D=1, A=2
    result_mapping = {'H': 0, 'D': 1, 'A': 2}
    y_encoded = y.map(result_mapping)
    
    print("\nTarget distribution:")
    print(y.value_counts())
    print("\nEncoded as:")
    print("  H (Home Win) = 0")
    print("  D (Draw) = 1")
    print("  A (Away Win) = 2")
    
    # Split data: 70% train, 15% validation, 15% test
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y_encoded, test_size=0.30, random_state=42, stratify=y_encoded
    )
    
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
    )
    
    print(f"\nData split:")
    print(f"  Training: {len(X_train)} matches ({len(X_train)/len(df)*100:.1f}%)")
    print(f"  Validation: {len(X_val)} matches ({len(X_val)/len(df)*100:.1f}%)")
    print(f"  Test: {len(X_test)} matches ({len(X_test)/len(df)*100:.1f}%)")
    
    # Scale features
    print("\nScaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)
    print("✓ Features scaled")
    
    return {
        'X_train': X_train_scaled,
        'X_val': X_val_scaled,
        'X_test': X_test_scaled,
        'y_train': y_train,
        'y_val': y_val,
        'y_test': y_test,
        'feature_names': feature_cols,
        'scaler': scaler,
        'result_mapping': result_mapping
    }


def train_models(data):
    """Train multiple classification models"""
    print("\n" + "="*70)
    print("MODEL TRAINING")
    print("="*70)
    
    models = {}
    
    # 1. Logistic Regression (Baseline)
    print("\n1. Training Logistic Regression...")
    lr_model = LogisticRegression(
        max_iter=1000,
        multi_class='multinomial',
        random_state=42
    )
    lr_model.fit(data['X_train'], data['y_train'])
    models['Logistic Regression'] = lr_model
    print("✓ Logistic Regression trained")
    
    # 2. Random Forest
    print("\n2. Training Random Forest...")
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(data['X_train'], data['y_train'])
    models['Random Forest'] = rf_model
    print("✓ Random Forest trained")
    
    # 3. XGBoost
    print("\n3. Training XGBoost...")
    xgb_model = XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        eval_metric='mlogloss'
    )
    xgb_model.fit(data['X_train'], data['y_train'])
    models['XGBoost'] = xgb_model
    print("✓ XGBoost trained")
    
    return models


def evaluate_models(models, data):
    """Evaluate all models on validation and test sets"""
    print("\n" + "="*70)
    print("MODEL EVALUATION")
    print("="*70)
    
    results = []
    
    for model_name, model in models.items():
        print(f"\n{'='*70}")
        print(f"{model_name}")
        print(f"{'='*70}")
        
        # Validation set predictions
        val_pred = model.predict(data['X_val'])
        val_pred_proba = model.predict_proba(data['X_val'])
        
        # Test set predictions
        test_pred = model.predict(data['X_test'])
        test_pred_proba = model.predict_proba(data['X_test'])
        
        # Calculate metrics
        val_accuracy = accuracy_score(data['y_val'], val_pred)
        test_accuracy = accuracy_score(data['y_test'], test_pred)
        
        val_logloss = log_loss(data['y_val'], val_pred_proba)
        test_logloss = log_loss(data['y_test'], test_pred_proba)
        
        print(f"\nValidation Set:")
        print(f"  Accuracy: {val_accuracy:.4f}")
        print(f"  Log Loss: {val_logloss:.4f}")
        
        print(f"\nTest Set:")
        print(f"  Accuracy: {test_accuracy:.4f}")
        print(f"  Log Loss: {test_logloss:.4f}")
        
        print(f"\nClassification Report (Test Set):")
        print(classification_report(
            data['y_test'], 
            test_pred,
            target_names=['Home Win', 'Draw', 'Away Win']
        ))
        
        # Store results
        results.append({
            'Model': model_name,
            'Val Accuracy': val_accuracy,
            'Test Accuracy': test_accuracy,
            'Val Log Loss': val_logloss,
            'Test Log Loss': test_logloss
        })
    
    # Summary table
    results_df = pd.DataFrame(results)
    print("\n" + "="*70)
    print("MODEL COMPARISON SUMMARY")
    print("="*70)
    print(results_df.to_string(index=False))
    
    # Find best model
    best_model_name = results_df.loc[results_df['Test Accuracy'].idxmax(), 'Model']
    print(f"\n🏆 Best Model: {best_model_name}")
    
    return results_df, best_model_name


def main():
    print("="*70)
    print("PREMIER LEAGUE WIN PROBABILITY MODEL TRAINING")
    print("="*70)
    
    # Prepare data
    data = prepare_data('pl_features_complete_20260108.csv')
    
    # Train models
    models = train_models(data)
    
    # Evaluate models
    results, best_model = evaluate_models(models, data)
    
    # Save best model
    print(f"\n{'='*70}")
    print("SAVING MODELS")
    print(f"{'='*70}")
    
    model_file = f"pl_model_{best_model.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.pkl"
    scaler_file = f"pl_scaler_{datetime.now().strftime('%Y%m%d')}.pkl"
    
    joblib.dump(models[best_model], model_file)
    joblib.dump(data['scaler'], scaler_file)
    
    print(f"✓ Best model saved: {model_file}")
    print(f"✓ Scaler saved: {scaler_file}")
    
    print(f"\n{'='*70}")
    print("TRAINING COMPLETE!")
    print(f"{'='*70}")
    print("\nNext steps:")
    print("1. Review model performance above")
    print("2. We'll make predictions on upcoming fixtures")
    print("3. Then build the web app!")

if __name__ == "__main__":
    main()
