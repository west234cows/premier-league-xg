# ⚽ Premier League Win Probability Model

Machine learning system predicting Premier League match outcomes (Home Win / Draw / Away Win) using API-Football data.

**Current Status:** ✅ Model trained (54% accuracy), predictions working, ready for database + dashboard integration

---

## 🎯 Project Goal

Build a **mobile-accessible dashboard** that:
- Shows upcoming PL fixtures with win probabilities
- Displays confidence levels (High/Medium/Low)
- Auto-refreshes daily (tracks accuracy, updates fixtures)
- Accessible from phone anywhere via cloud deployment

**Tech Stack:** Python, API-Football, PostgreSQL (future), Streamlit (future)

---

## 📁 Project Structure

premier-league-xg/
│
├── src/                              # All Python scripts
│   ├── api_football_collector.py     # API data collection class
│   ├── collect_historical_data.py    # Fetch 3 seasons of fixtures
│   ├── enrich_historical_data.py     # Add match statistics
│   ├── build_all_features.py         # Feature engineering (42 features)
│   ├── train_model.py                # Train ML models
│   ├── predict_upcoming.py           # Generate predictions
│   ├── config.py                     # API key (NOT in Git)
│   └── config_template.py            # Template for setup
│
├── data/                             # Data files (NOT in Git)
│   ├── pl_historical_enriched_*.csv
│   ├── pl_features_complete_*.csv
│   └── pl_predictions_*.csv
│
├── models/                           # Trained models (NOT in Git)
│   ├── pl_model_random_forest_*.pkl
│   └── pl_scaler_*.pkl
│
├── docs/                             # API documentation
│
├── .gitignore
├── requirements.txt
└── README.md

---

## 🚀 Quick Start

### 1. Clone & Install Dependencies

git clone https://github.com/yourusername/premier-league-xg.git
cd premier-league-xg
pip install -r requirements.txt

### 2. Setup API Key

cp src/config_template.py src/config.py

Edit src/config.py:

API_FOOTBALL_KEY = "your_actual_api_key_here"

### 3. Run Predictions

python src/predict_upcoming.py

---

## 📊 Current Data Pipeline

### Data Collection (One-Time Setup)

# 1. Collect 3 seasons of fixtures (~3 API calls)
python src/collect_historical_data.py

# 2. Enrich with match stats (~969 API calls)
python src/enrich_historical_data.py

# 3. Build features (no API calls)
python src/build_all_features.py

# 4. Train models (no API calls)
python src/train_model.py

### Generate Predictions (Ongoing)

# Predict upcoming fixtures (1 API call)
python src/predict_upcoming.py

Output: data/pl_predictions_YYYYMMDD.csv

---

## 🤖 Model Performance

**Best Model:** Random Forest

- **Test Accuracy:** 53.9% (solid for 3-class football prediction)
- **Validation Accuracy:** 53.9% (no overfitting)

**Confidence Levels:**
- High: ≥60% probability
- Medium: 50-60% probability
- Low: <50% probability

**Feature Set:** 42 engineered features across 3 stages:
1. Team Form (14): Last 5 games rolling averages (goals, shots, possession, win %)
2. Advanced Metrics (13): Shot accuracy, conversion rate, defensive efficiency
3. Match Context (15): Form differentials, home advantage, attack vs defense matchups

---

## 📡 API Usage

**Current Plan:** 1-month API-Football subscription

- **Quota Remaining:** ~6,475 requests
- **Rate Limit:** 1 request/second (enforced in code)

**Data Collection Costs:**
- Historical data (one-time): ~972 calls
- Daily predictions: ~1 call
- Plenty of quota for development!

---

## 🔮 Next Steps - Plan B

### Phase 1: Git Push (NOW)
- ✅ Project organized
- ⏭️ Initialize Git repository
- ⏭️ Push to GitHub

### Phase 2: PostgreSQL Integration (Home Mac)
**Goal:** Store data in PostgreSQL for scalability

**Tasks:**
- Setup PostgreSQL on Mac
- Create database schema (fixtures, predictions, accuracy tracking)
- Migrate CSV data → database
- Update scripts to read from DB

### Phase 3: Streamlit Dashboard (Mobile Web App)
**Goal:** Build cloud-deployed dashboard accessible from phone

**Features:**
- Upcoming fixtures + predictions + confidence
- Prediction accuracy tracker (predicted vs actual)
- Visual indicators (🟢 High, 🟡 Medium, 🔴 Low)
- Auto-refresh daily

**Deployment:** Streamlit Cloud (free tier) → accessible anywhere

### Phase 4: Automated Daily Refresh
**Goal:** Dashboard updates automatically every day

**Implementation:**
- Cron job (Mac) or Task Scheduler (Windows)
- Fetch new completed fixtures
- Update database
- Generate new predictions
- Track prediction accuracy

---

## 🛠️ Technical Details

### Key Dependencies

requests==2.31.0          # API calls
pandas==2.1.4             # Data manipulation
scikit-learn==1.3.2       # Machine learning
xgboost==2.0.3            # Gradient boosting
psycopg2-binary==2.9.9    # PostgreSQL (future)
joblib==1.3.2             # Model serialization

### Model Training

- **Data:** 938 matches (2022-2025 seasons)
- **Split:** 70% train, 15% validation, 15% test
- **Scaling:** StandardScaler (features normalized)
- **Models Tested:** Logistic Regression, Random Forest, XGBoost

### Prediction Pipeline

1. Load trained model + scaler
2. Fetch upcoming fixtures from API
3. Calculate 42 features for each match
4. Predict probabilities [Home Win, Draw, Away Win]
5. Assign confidence level based on max probability

---

## 📝 Important Notes

### Why No xG?
API-Football does NOT provide Expected Goals (xG) data despite initial plans. Pivoted to using available statistics (shots, possession, form).

### Data Not in Git
- **data/ folder:** CSVs too large for Git
- **models/ folder:** Model files ~2 MB each
- **src/config.py:** Contains API key (security)
- **Solution:** Files excluded via .gitignore, use cloud storage or local setup

### Config Template
src/config_template.py is in Git for setup reference. Copy to src/config.py and add your API key.

---

## 🐛 Troubleshooting

**Issue:** KeyError: 'losses'
- **Fix:** Already handled - API uses 'loses' not 'losses'

**Issue:** No upcoming fixtures found
- **Fix:** Check API dashboard, increase days_ahead parameter

**Issue:** Model file not found
- **Fix:** Ensure running from project root: python src/predict_upcoming.py

---

## 👤 Author

**Bobby Poehlitz**
- Associate Business Analyst, NextEra Energy
- Email: rxp02b6@fpl.com

---

## 📅 Project Timeline

- **2026-01-08:** Data collection, feature engineering, model training complete
- **2026-01-08:** Prediction pipeline working
- **2026-01-08:** Project organized for Git
- **Next:** PostgreSQL integration + Streamlit dashboard
