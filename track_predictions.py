#!/usr/bin/env python3
"""
Prediction Tracking System
Fetches actual results and tracks prediction accuracy
"""

import sys
import psycopg2
from datetime import datetime
import requests
import time

# Add src to path
sys.path.append('src')
from config import API_FOOTBALL_KEY, DB_PARAMS

# API configuration
API_KEY = API_FOOTBALL_KEY
API_HOST = "v3.football.api-sports.io"


class PredictionTracker:
    """Tracks prediction accuracy"""
    
    def __init__(self):
        self.conn = None
        self.api_key = API_KEY
        self.api_host = API_HOST
        self.updated_count = 0
        self.failed_count = 0
    
    def connect_db(self):
        """Connect to database"""
        try:
            self.conn = psycopg2.connect(**DB_PARAMS)
            print("✓ Database connected")
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            sys.exit(1)
    
    def get_untracked_predictions(self):
        """Get predictions for completed matches that haven't been tracked yet"""
        cur = self.conn.cursor()
        
        query = """
            SELECT 
                p.id,
                p.fixture_id,
                f.home_team,
                f.away_team,
                f.date,
                p.predicted_result,
                p.confidence,
                p.home_win_prob,
                p.draw_prob,
                p.away_win_prob
            FROM predictions p
            JOIN fixtures f ON p.fixture_id = f.fixture_id
            LEFT JOIN prediction_accuracy pa ON p.fixture_id = pa.fixture_id
            WHERE f.date < CURRENT_TIMESTAMP
              AND pa.fixture_id IS NULL
            ORDER BY f.date DESC
            LIMIT 50
        """
        
        cur.execute(query)
        results = cur.fetchall()
        cur.close()
        
        print(f"\n📋 Found {len(results)} completed matches to track")
        return results
    
    def fetch_match_result(self, fixture_id):
        """Fetch actual match result from API"""
        url = f"https://{self.api_host}/fixtures"
        headers = {'x-apisports-key': self.api_key}
        params = {'id': fixture_id}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data['results'] == 0:
                return None
            
            fixture = data['response'][0]
            
            # Check if match is finished
            status = fixture['fixture']['status']['short']
            if status not in ['FT', 'AET', 'PEN']:
                return None
            
            # Get scores
            home_score = fixture['goals']['home']
            away_score = fixture['goals']['away']
            
            if home_score is None or away_score is None:
                return None
            
            # Determine result
            if home_score > away_score:
                actual_result = 'H'
            elif away_score > home_score:
                actual_result = 'A'
            else:
                actual_result = 'D'
            
            return {
                'home_score': home_score,
                'away_score': away_score,
                'actual_result': actual_result,
                'status': status
            }
            
        except Exception as e:
            print(f"  ✗ API error for fixture {fixture_id}: {e}")
            return None
    
    def save_accuracy(self, prediction_data, result_data):
        """Save prediction accuracy to database"""
        try:
            cur = self.conn.cursor()
            
            # Calculate if prediction was correct
            correct = prediction_data['predicted_result'] == result_data['actual_result']
            
            # Insert accuracy record
            cur.execute("""
                INSERT INTO prediction_accuracy (
                    fixture_id,
                    predicted_result,
                    actual_result,
                    was_correct,
                    predicted_home_prob,
                    predicted_draw_prob,
                    predicted_away_prob,
                    confidence,
                    tracked_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fixture_id) DO NOTHING
            """, (
                prediction_data['fixture_id'],
                prediction_data['predicted_result'],
                result_data['actual_result'],
                correct,
                float(prediction_data['home_win_prob']),
                float(prediction_data['draw_prob']),
                float(prediction_data['away_win_prob']),
                prediction_data['confidence'],
                datetime.now()
            ))
            
            self.conn.commit()
            cur.close()
            
            # Display result
            emoji = "✅" if correct else "❌"
            result_text = {'H': 'Home', 'D': 'Draw', 'A': 'Away'}
            print(f"  {emoji} {prediction_data['home_team']} vs {prediction_data['away_team']}")
            print(f"     Score: {result_data['home_score']}-{result_data['away_score']}")
            print(f"     Predicted: {result_text[prediction_data['predicted_result']]} | "
                  f"Actual: {result_text[result_data['actual_result']]}")
            
            self.updated_count += 1
            return True
            
        except Exception as e:
            print(f"  ✗ Error saving accuracy: {e}")
            self.conn.rollback()
            return False
    
    def show_summary(self):
        """Show accuracy summary"""
        try:
            cur = self.conn.cursor()
            
            # Overall accuracy
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct,
                    ROUND(AVG(CASE WHEN was_correct THEN 1.0 ELSE 0.0 END) * 100, 1) as accuracy
                FROM prediction_accuracy
            """)
            
            result = cur.fetchone()
            total, correct, accuracy = result if result else (0, 0, 0)
            
            if total and total > 0:
                print(f"\n{'='*60}")
                print(f"📊 ACCURACY SUMMARY")
                print(f"{'='*60}")
                print(f"Total tracked: {total}")
                print(f"Correct: {correct}/{total} ({accuracy}%)")
                
                # By confidence
                cur.execute("""
                    SELECT 
                        confidence,
                        COUNT(*) as total,
                        ROUND(AVG(CASE WHEN was_correct THEN 1.0 ELSE 0.0 END) * 100, 1) as accuracy
                    FROM prediction_accuracy
                    GROUP BY confidence
                    ORDER BY 
                        CASE confidence 
                            WHEN 'High' THEN 1 
                            WHEN 'Medium' THEN 2 
                            WHEN 'Low' THEN 3 
                        END
                """)
                
                print(f"\n📈 By Confidence Level:")
                for conf, count, acc in cur.fetchall():
                    print(f"  {conf.upper()}: {acc}% ({count} predictions)")
                
                print(f"{'='*60}\n")
            
            cur.close()
            
        except Exception as e:
            print(f"✗ Error showing summary: {e}")
    
    def run(self):
        """Main tracking process"""
        print("="*60)
        print("🎯 PREDICTION TRACKING SYSTEM")
        print("="*60)
        
        self.connect_db()
        
        # Get untracked predictions
        predictions = self.get_untracked_predictions()
        
        if not predictions:
            print("✓ All predictions are up to date!")
            self.show_summary()
            return
        
        print(f"\n🔄 Fetching results from API...")
        
        # Process each prediction
        for pred in predictions:
            prediction_data = {
                'id': pred[0],
                'fixture_id': pred[1],
                'home_team': pred[2],
                'away_team': pred[3],
                'date': pred[4],
                'predicted_result': pred[5],
                'confidence': pred[6],
                'home_win_prob': pred[7],
                'draw_prob': pred[8],
                'away_win_prob': pred[9]
            }
            
            # Fetch actual result
            result = self.fetch_match_result(prediction_data['fixture_id'])
            
            if result:
                self.save_accuracy(prediction_data, result)
            else:
                self.failed_count += 1
            
            # Rate limiting - be nice to API
            time.sleep(1)
        
        # Show results
        print(f"\n{'='*60}")
        print(f"✅ Updated: {self.updated_count}")
        print(f"⏭️  Skipped: {self.failed_count}")
        print(f"{'='*60}")
        
        # Show summary
        self.show_summary()
        
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    tracker = PredictionTracker()
    tracker.run()