import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Premier League Predictions",
    page_icon="⚽",
    layout="wide"
)

# Database connection
@st.cache_resource
def get_db_connection():
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            dbname="premier_league",
            user="pl_user",
            password="",  # Add your password if you have one
            host="localhost",
            port="5432"
        )
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

# Load predictions
@st.cache_data(ttl=300)
def load_predictions(_conn):
    """Load upcoming predictions from database"""
    query = """
        SELECT 
            f.date as fixture_date,
            f.home_team,
            f.away_team,
            f.venue,
            p.predicted_result,
            p.confidence,
            p.home_win_prob,
            p.draw_prob,
            p.away_win_prob
        FROM predictions p
        JOIN fixtures f ON p.fixture_id = f.fixture_id
        WHERE f.date >= CURRENT_DATE
        ORDER BY f.date
    """
    return pd.read_sql_query(query, _conn)

# Main app

# Main app
def main():
    st.title("⚽ Premier League Predictions")
    st.markdown("*AI-powered match predictions using Random Forest ML*")
    
    # Connect to database
    conn = get_db_connection()
    if not conn:
        st.stop()
    
    # Sidebar navigation
    st.sidebar.title("📊 Navigation")
    page = st.sidebar.radio("Go to", ["Upcoming Predictions", "Tracked Results", "About"])
    
    if page == "Upcoming Predictions":
        show_upcoming_predictions(conn)
    elif page == "Tracked Results":
        show_tracked_results(conn)
    else:
        show_about()

def show_upcoming_predictions(conn):
    """Show upcoming predictions page"""
    # Load predictions
    try:
        predictions_df = load_predictions(conn)
    except Exception as e:
        st.error(f"Error loading predictions: {e}")
        st.stop()
    
    # Show stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Predictions", len(predictions_df))
    with col2:
        high_conf = len(predictions_df[predictions_df['confidence'] == 'High'])
        st.metric("High Confidence", high_conf)
    with col3:
        st.metric("Model Accuracy", "53.8%")
    
    st.divider()
    
    # Display predictions
    st.header("📅 Upcoming Matches")
    
    if predictions_df.empty:
        st.info("No upcoming predictions available.")
        return
    
    # Group by date
    for date in predictions_df['fixture_date'].unique():
        date_str = pd.to_datetime(date).strftime('%A, %B %d, %Y')
        st.subheader(f"📆 {date_str}")
        
        day_preds = predictions_df[predictions_df['fixture_date'] == date]
        
        for _, match in day_preds.iterrows():
            col1, col2, col3 = st.columns([3, 2, 2])
            
            with col1:
                # Match info
                result_emoji = {"H": "🏠", "D": "🤝", "A": "✈️"}
                emoji = result_emoji.get(match['predicted_result'], "⚽")
                st.markdown(f"### {emoji} {match['home_team']} vs {match['away_team']}")
                st.caption(f"📍 {match['venue']}")
            
            with col2:
                # Prediction
                result_text = {"H": "Home Win", "D": "Draw", "A": "Away Win"}
                prediction = result_text.get(match['predicted_result'], "Unknown")
                
                # Color code confidence
                if match['confidence'] == 'High':
                    st.success(f"**Prediction:** {prediction}")
                    st.success(f"**Confidence:** {match['confidence']}")
                elif match['confidence'] == 'Medium':
                    st.warning(f"**Prediction:** {prediction}")
                    st.warning(f"**Confidence:** {match['confidence']}")
                else:
                    st.info(f"**Prediction:** {prediction}")
                    st.info(f"**Confidence:** {match['confidence']}")
            
            with col3:
                # Probabilities
                st.markdown("**Win Probabilities:**")
                
                # Check if probabilities exist
                if pd.notna(match['home_win_prob']):
                    home_prob = float(match['home_win_prob']) / 100
                    draw_prob = float(match['draw_prob']) / 100
                    away_prob = float(match['away_win_prob']) / 100
                    
                    st.progress(home_prob, text=f"Home: {home_prob:.1%}")
                    st.progress(draw_prob, text=f"Draw: {draw_prob:.1%}")
                    st.progress(away_prob, text=f"Away: {away_prob:.1%}")
                else:
                    st.caption("Probabilities not available")
            
            st.divider()

def show_tracked_results(conn):
    """Show tracked results page"""
    st.header("📊 Tracked Results")
    
    # Load tracked results
    try:
        query = """
            SELECT 
                f.date,
                f.home_team,
                f.away_team,
                pa.predicted_result,
                pa.actual_result,
                pa.was_correct,
                pa.predicted_home_prob,
                pa.predicted_draw_prob,
                pa.predicted_away_prob,
                pa.confidence,
                f.home_goals,
                f.away_goals
            FROM prediction_accuracy pa
            JOIN fixtures f ON pa.fixture_id = f.fixture_id
            ORDER BY f.date DESC
            LIMIT 50
        """
        results_df = pd.read_sql_query(query, conn)
    except Exception as e:
        st.error(f"Error loading results: {e}")
        return
    
    if results_df.empty:
        st.info("No tracked results yet. Run `python3 track_predictions.py` after matches finish to track accuracy!")
        return
    
    # Overall stats
    total = len(results_df)
    correct = results_df['was_correct'].sum()
    accuracy = (correct / total * 100) if total > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Tracked", total)
    with col2:
        st.metric("Correct", f"{correct}/{total}")
    with col3:
        st.metric("Accuracy", f"{accuracy:.1f}%")
    
    # By confidence
    st.subheader("📈 Accuracy by Confidence")
    conf_stats = results_df.groupby('confidence')['was_correct'].agg(['count', 'sum', 'mean'])
    
    for conf in ['High', 'Medium', 'Low']:
        if conf in conf_stats.index:
            count = conf_stats.loc[conf, 'count']
            correct_conf = conf_stats.loc[conf, 'sum']
            acc_conf = conf_stats.loc[conf, 'mean'] * 100
            st.write(f"**{conf}:** {acc_conf:.1f}% ({int(correct_conf)}/{int(count)})")
    
    st.divider()
    
    # Recent results
    st.subheader("🎯 Recent Results")
    
    for _, match in results_df.head(20).iterrows():
        col1, col2, col3 = st.columns([3, 2, 2])
        
        with col1:
            date_str = pd.to_datetime(match['date']).strftime('%b %d')
            emoji = "✅" if match['was_correct'] else "❌"
            st.markdown(f"### {emoji} {match['home_team']} vs {match['away_team']}")
            st.caption(f"📅 {date_str}")
        
        with col2:
            result_text = {"H": "Home Win", "D": "Draw", "A": "Away Win"}
            st.write(f"**Score:** {int(match['home_goals'])}-{int(match['away_goals'])}")
            st.write(f"**Predicted:** {result_text[match['predicted_result']]}")
            st.write(f"**Actual:** {result_text[match['actual_result']]}")
        
        with col3:
            st.write(f"**Confidence:** {match['confidence']}")
            home_prob = float(match['predicted_home_prob']) / 100
            draw_prob = float(match['predicted_draw_prob']) / 100
            away_prob = float(match['predicted_away_prob']) / 100
            st.caption(f"H: {home_prob:.0%} | D: {draw_prob:.0%} | A: {away_prob:.0%}")
        
        st.divider()

def show_about():
    """Show about page"""
    st.header("ℹ️ About This System")
    
    st.markdown("""
    ### 🎯 Premier League Prediction System
    
    **Model:** Random Forest Classifier  
    **Accuracy:** 53.8% (3-class prediction)  
    **Training Data:** 948 matches (3 seasons)  
    **Features:** 36 engineered features including xG, form, team strength
    
    #### 📊 How It Works:
    1. **Data Collection:** Fetches match data from API-Football
    2. **Feature Engineering:** Creates 36 statistical features
    3. **ML Prediction:** Random Forest model predicts outcomes
    4. **Tracking:** Compares predictions with actual results
    
    #### 🔄 Updates:
    - Predictions refresh daily
    - Results tracked automatically after matches
    - Model accuracy improves with more data
    
    #### 📱 Features:
    - ✅ Upcoming match predictions
    - ✅ Win probability estimates
    - ✅ Confidence levels
    - ✅ Historical accuracy tracking
    - ✅ Mobile-responsive design
    """)
    
    st.divider()
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")


if __name__ == "__main__":
    main()
