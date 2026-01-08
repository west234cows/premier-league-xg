import requests
from config import API_FOOTBALL_KEY

url = "https://v3.football.api-sports.io/status"

headers = {
    "x-apisports-key": API_FOOTBALL_KEY,
    'x-rapidapi-host': "v3.football.api-sports.io"}

try:
    response = requests.get(url, headers=headers)
    print(f"Response Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("API Status Workks")
    elif response.status_code == 401:
        print("Invalid API Key")
    elif response.status_code == 403:
        print("API Key Quota Exceeded")
    else:
        print(f"Unexpected Error: {response.status_code}")
except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")