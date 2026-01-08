import os
import sys
import requests

#!/usr/bin/env python3
# API_TEST_02.py

API_KEY = os.getenv("e760d89d35dc46c13bbba41d103ab528") or "e760d89d35dc46c13bbba41d103ab528"
if API_KEY == "YOUR_API_KEY_HERE":
    print("Set API key in environment variable API_FOOTBALL_KEY or replace the placeholder.")
    sys.exit(1)

URL = "https://v3.football.api-sports.io/leagues"
headers = {"x-apisports-key": API_KEY}
params = {"name": "Premier League"}

resp = requests.get(URL, headers=headers, params=params, timeout=10)
resp.raise_for_status()
data = resp.json().get("response", [])
if not data:
    print("Premier League not found in API response.")
    sys.exit(1)

seasons = data[0].get("seasons", [])
years = sorted({s.get("year") for s in seasons if s.get("year") is not None})
print("Available Premier League seasons:", years)

