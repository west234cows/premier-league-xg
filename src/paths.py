# paths.py

import os

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(REPO_ROOT, "data")
MODELS_DIR = os.path.join(REPO_ROOT, "models")

def require_dirs(assert_only: bool = True):
    if assert_only:
        if not os.path.isdir(DATA_DIR):
            raise OSError(f"Expected data directory not found: {DATA_DIR}")
        if not os.path.isdir(MODELS_DIR):
            raise OSError(f"Expected models directory not found: {MODELS_DIR}")
    else:
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(MODELS_DIR, exist_ok=True)