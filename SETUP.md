# 🔧 Setup Guide

## Initial Setup (Any Machine)

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/premier-league-xg.git
cd premier-league-xg
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

**Mac Users Only:** Install OpenMP for XGBoost:
```bash
brew install libomp
```

### 3. Setup Configuration
```bash
cp src/config_template.py src/config.py
# Edit config.py and add your API-Football key
```

---

## Syncing Between Machines

### Update from GitHub
```bash
git pull origin main
pip install -r requirements.txt  # If dependencies changed
```

### Push Your Changes
```bash
git add .
git commit -m "Your message"
git push origin main
```

---

## Important Notes

- **Never commit** `src/config.py` (contains API key)
- **data/** and **models/** folders not in Git (too large)
- **Regenerate data/models** on new machines or use cloud storage

---

## Quick Test
```bash
python src/train_model.py
```