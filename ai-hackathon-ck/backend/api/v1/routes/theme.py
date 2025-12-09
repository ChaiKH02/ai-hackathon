import pandas as pd
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Query, HTTPException
# Ensure you have your database utility imported here
from utils.risk_engine import fetch_survey_from_db

router = APIRouter(
    prefix="/theme",
    tags=["Theme"]
)

# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def get_dataframe_from_db() -> pd.DataFrame:
    """Fetches data and ensures consistent DataFrame format."""
    data = fetch_survey_from_db()
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = pd.DataFrame(data)
    
    # Standardize Column Names if necessary (optional safety)
    if 'Submission_Date' in df.columns:
        df['Submission_Date'] = pd.to_datetime(df['Submission_Date'])
        
    return df

def apply_filters(
    df: pd.DataFrame, 
    year: Optional[int], 
    quarter: Optional[str], 
    department: Optional[str],
    sentiment: Optional[str]
) -> pd.DataFrame:
    """Applies common filters to the DataFrame."""
    if df.empty:
        return df

    if year:
        df = df[df['Submission_Date'].dt.year == year]

    if quarter:
        # Case insensitive match for 'Q1', 'q1', etc.
        df = df[df['Quarter'].astype(str).str.lower() == quarter.lower()]

    if department and department.lower() != 'all':
        df = df[df['Department'].astype(str).str.lower() == department.lower()]

    if sentiment and sentiment.lower() != 'all':
        df = df[df['Sentiment_Label'].astype(str).str.lower() == sentiment.lower()]

    return df

def get_previous_period(year: int, quarter: Optional[str]) -> tuple[int, Optional[str]]:
    """Calculates the previous time period for comparison logic."""
    if quarter:
        # Assumes format like "Q1", "Q2"
        q_clean = quarter.upper().replace("Q", "")
        if q_clean.isdigit():
            q_num = int(q_clean)
            if q_num == 1:
                return year - 1, "Q4"
            else:
                return year, f"Q{q_num - 1}"
    # Default: Compare vs Previous Year
    return year - 1, None

def calculate_category_metrics(df_group: pd.DataFrame) -> Dict[str, float]:
    """Calculates average scores for a specific group of data."""
    return {
        "avg_job_satisfaction": df_group['Q1_Job_Satisfaction'].mean(),
        "avg_work_life_balance": df_group['Q2_Work_Life_Balance'].mean(),
        "avg_manager_support": df_group['Q3_Manager_Support'].mean(),
        "avg_enps": df_group['Q5_eNPS'].mean()
    }

# ---------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------

@router.get("/insights")
def get_theme_insights(
    year: Optional[int] = Query(None),
    quarter: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    sentiment_label: Optional[str] = Query(None),
    limit: int = Query(5)
):
    try:
        # 1. Fetch Full Data
        df_full = get_dataframe_from_db()
        
        if df_full.empty:
            return {
                "total_themes_detected": 0,
                "total_responses_processed": 0,
                "global_sentiment": {"Positive": 0, "Negative": 0, "Neutral": 0},
                "data": []
            }

        # ---------------------------------------------------------
        # FIX: Normalize Sentiment Column (Handle 'positive', 'POSITIVE', ' positive ')
        # ---------------------------------------------------------
        if 'Sentiment_Label' in df_full.columns:
            # Convert to string, strip whitespace, and convert to Title Case
            # e.g., "positive" -> "Positive", "NEGATIVE" -> "Negative"
            df_full['Sentiment_Label'] = df_full['Sentiment_Label'].astype(str).str.strip().str.title()
        # ---------------------------------------------------------

        # 2. Apply Filters (Year, Dept, etc.)
        df_current = apply_filters(df_full, year, quarter, department, sentiment_label)
        
        # 3. Clean Data (Categorized only)
        df_clean = df_current.dropna(subset=['Categories'])
        df_clean = df_clean[df_clean['Categories'] != ""]

        # --- CALCULATION START ---
        total_responses = len(df_clean)
        
        if total_responses == 0:
            return {
                "total_themes_detected": 0,
                "total_responses_processed": 0,
                "global_sentiment": {"Positive": 0, "Negative": 0, "Neutral": 0},
                "period_compared": "None",
                "data": []
            }

        # B. Global Sentiment Counts
        # Now that data is normalized to "Positive"/"Negative", this look up will work
        global_sentiment_counts = df_clean['Sentiment_Label'].value_counts().to_dict()
        
        global_sentiment = {
            "Positive": int(global_sentiment_counts.get("Positive", 0)),
            "Negative": int(global_sentiment_counts.get("Negative", 0)),
            "Neutral": int(global_sentiment_counts.get("Neutral", 0))
        }

        # C. Grouping
        grouped = df_clean.groupby('Categories')
        total_themes = len(grouped)
        
        # Previous Period Logic
        previous_metrics_map = {}
        if year:
            prev_year, prev_q = get_previous_period(year, quarter)
            df_prev = apply_filters(df_full, prev_year, prev_q, department, sentiment_label)
            df_prev = df_prev.dropna(subset=['Categories'])
            df_prev = df_prev[df_prev['Categories'] != ""]
            
            # Ensure previous data is also normalized if needed (though df_full is already done)
            if not df_prev.empty:
                for cat, group in df_prev.groupby('Categories'):
                    previous_metrics_map[cat] = calculate_category_metrics(group)

        # D. Process Themes
        results = []
        for category, group in grouped:
            # Theme-specific sentiment
            cat_sentiment_counts = group['Sentiment_Label'].value_counts().to_dict()
            
            # Normalize keys for breakdown inside the specific theme
            breakdown = {
                "Positive": int(cat_sentiment_counts.get("positive", 0)),
                "Negative": int(cat_sentiment_counts.get("negative", 0)),
                "Neutral": int(cat_sentiment_counts.get("neutral", 0))
            }
            
            dominant = max(breakdown, key=breakdown.get) if any(breakdown.values()) else "Unknown"

            # Metrics
            current_metrics = calculate_category_metrics(group)
            prev_data = previous_metrics_map.get(category, {})
            
            insights_payload = {}
            for key, val in current_metrics.items():
                current_val = round(val, 2) if pd.notnull(val) else 0
                prev_val = prev_data.get(key)
                diff = round(current_val - prev_val, 2) if prev_val is not None and pd.notnull(prev_val) else 0
                
                insights_payload[key] = current_val
                insights_payload[f"{key}_diff"] = diff

            results.append({
                "category": category,
                "response_count": len(group),
                "dominant_sentiment": dominant,
                "sentiment_breakdown": breakdown, # Useful debugging field
                "insights": insights_payload
            })

        results = sorted(results, key=lambda x: x['response_count'], reverse=True)

        return {
            "total_themes_detected": total_themes,
            "total_responses_processed": total_responses,
            "global_sentiment": global_sentiment,
            "period_compared": "Quarter" if quarter else "Year" if year else "None",
            "data": results[:limit]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent-feedback")
def get_recent_feedback(
    year: Optional[int] = Query(None),
    quarter: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    sentiment_label: Optional[str] = Query(None),
    limit: int = Query(10)
):
    """Returns raw comments sorted by date."""
    try:
        df = get_dataframe_from_db()
        
        # Apply Filters
        df = apply_filters(df, year, quarter, department, sentiment_label)

        # Remove empty comments
        df = df.dropna(subset=['Comments'])
        df = df[df['Comments'] != ""]

        # Sort by Date Descending
        df = df.sort_values(by='Submission_Date', ascending=False)

        # Slice
        df_subset = df.head(limit)

        result_data = []
        for _, row in df_subset.iterrows():
            result_data.append({
                "submission_date": row['Submission_Date'].strftime('%Y-%m-%d') if pd.notnull(row['Submission_Date']) else None,
                "category": row['Categories'] if pd.notnull(row['Categories']) and row['Categories'] != "" else "Uncategorized",
                "sentiment": row['Sentiment_Label'],
                "comment": row['Comments']
            })

        return {"count": len(result_data), "data": result_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))