#!/usr/bin/env python3
"""
Daily Automation Pipeline
Runs all necessary tasks to keep predictions up-to-date
"""

import subprocess
import sys
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/daily_automation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def run_command(command, description):
    """Run a command and log results"""
    logger.info(f"{'='*60}")
    logger.info(f"RUNNING: {description}")
    logger.info(f"{'='*60}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Log output
        if result.stdout:
            logger.info(result.stdout)
        
        if result.returncode == 0:
            logger.info(f"✅ SUCCESS: {description}")
            return True
        else:
            logger.error(f"❌ FAILED: {description}")
            if result.stderr:
                logger.error(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"⏱️ TIMEOUT: {description} took longer than 5 minutes")
        return False
    except Exception as e:
        logger.error(f"❌ ERROR: {description} - {str(e)}")
        return False


def main():
    """Run all daily tasks"""
    logger.info("="*60)
    logger.info("🤖 DAILY AUTOMATION PIPELINE")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)
    
    success_count = 0
    total_tasks = 4
    
    # Task 1: Fetch upcoming fixtures
    if run_command(
        "python3 src/fetch_upcoming_fixtures.py",
        "Fetch Upcoming Fixtures"
    ):
        success_count += 1
    
    # Task 2: Generate predictions
    if run_command(
        "python3 src/predict_upcoming.py",
        "Generate Predictions"
    ):
        success_count += 1
    
    # Task 3: Track completed results
    if run_command(
        "python3 track_predictions.py",
        "Track Prediction Accuracy"
    ):
        success_count += 1
    
    # Task 4: Database maintenance (optional)
    if run_command(
        'psql -h localhost -U pl_user -d premier_league -c "VACUUM ANALYZE;"',
        "Database Maintenance"
    ):
        success_count += 1
    
    # Summary
    logger.info("="*60)
    logger.info("📊 AUTOMATION SUMMARY")
    logger.info("="*60)
    logger.info(f"Completed: {success_count}/{total_tasks} tasks")
    logger.info(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)
    
    # Exit with appropriate code
    if success_count == total_tasks:
        logger.info("✅ All tasks completed successfully!")
        sys.exit(0)
    else:
        logger.warning(f"⚠️ {total_tasks - success_count} task(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
