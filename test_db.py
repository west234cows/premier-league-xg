import psycopg2
from config import DB_PARAMS
try:
    connection = psycopg2.connect(**DB_PARAMS)
    print("Database connection established.")
    connection.close()
except Exception as e:
    print(f"An error occurred: {e}")