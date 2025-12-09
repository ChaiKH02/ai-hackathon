from fastapi import APIRouter, Query
from utils.risk_engine import fetch_survey_from_db
from datetime import datetime
import pandas as pd
import numpy as np
from typing import Optional

router = APIRouter(
    prefix="/season",
    tags=["Season"]
)


def parse_event_season(event_season_str):
    """
    Parse the Event_Season string to extract season type and holiday name.
    
    Args:
        event_season_str: String like "festival: Chinese New Year" or "normal day"
    
    Returns:
        dict: {"season_type": "festival", "holiday_name": "Chinese New Year"}
    """
    if pd.isna(event_season_str) or event_season_str == "":
        return {"season_type": "normal", "holiday_name": None}
    
    event_season_str = str(event_season_str).strip()
    
    if event_season_str == "normal day":
        return {"season_type": "normal", "holiday_name": None}
    
    # Handle list format like "['festival: Chinese New Year']"
    if event_season_str.startswith("[") and event_season_str.endswith("]"):
        event_season_str = event_season_str.strip("[]'\"")
    
    if ":" in event_season_str:
        parts = event_season_str.split(":", 1)
        season_type = parts[0].strip()
        holiday_name = parts[1].strip() if len(parts) > 1 else None
        return {"season_type": season_type, "holiday_name": holiday_name}
    
    return {"season_type": "normal", "holiday_name": None}


def calculate_seasonal_metrics(df):
    """
    Calculate engagement, sentiment, and risk metrics for a dataframe.
    
    Args:
        df: DataFrame with survey responses
    
    Returns:
        dict: Calculated metrics
    """
    if df.empty:
        return {
            "response_count": 0,
            "avg_sentiment": None,
            "avg_engagement": None,
            "avg_job_satisfaction": None,
            "avg_work_life_balance": None,
            "avg_manager_support": None,
            "avg_growth_opportunities": None,
            "burnout_rate": None,
            "turnover_risk": None,
            "enps": None
        }
    
    # Calculate averages
    metrics = {
        "response_count": len(df)
    }
    
    # Sentiment score
    if "Sentiment_Score" in df.columns:
        metrics["avg_sentiment"] = float(df["Sentiment_Score"].mean()) if not df["Sentiment_Score"].isna().all() else None
    else:
        metrics["avg_sentiment"] = None
    
    # Survey questions (1-5 scale)
    if "Q1_Job_Satisfaction" in df.columns:
        metrics["avg_job_satisfaction"] = float(df["Q1_Job_Satisfaction"].mean()) if not df["Q1_Job_Satisfaction"].isna().all() else None
    else:
        metrics["avg_job_satisfaction"] = None
        
    if "Q2_Work_Life_Balance" in df.columns:
        metrics["avg_work_life_balance"] = float(df["Q2_Work_Life_Balance"].mean()) if not df["Q2_Work_Life_Balance"].isna().all() else None
    else:
        metrics["avg_work_life_balance"] = None
        
    if "Q3_Manager_Support" in df.columns:
        metrics["avg_manager_support"] = float(df["Q3_Manager_Support"].mean()) if not df["Q3_Manager_Support"].isna().all() else None
    else:
        metrics["avg_manager_support"] = None
        
    if "Q4_Growth_Opportunities" in df.columns:
        metrics["avg_growth_opportunities"] = float(df["Q4_Growth_Opportunities"].mean()) if not df["Q4_Growth_Opportunities"].isna().all() else None
    else:
        metrics["avg_growth_opportunities"] = None
    
    # Overall engagement (average of Q1-Q4)
    engagement_scores = []
    for col in ["Q1_Job_Satisfaction", "Q2_Work_Life_Balance", "Q3_Manager_Support", "Q4_Growth_Opportunities"]:
        if col in df.columns:
            engagement_scores.append(df[col])
    
    if engagement_scores:
        avg_engagement = pd.concat(engagement_scores, axis=1).mean(axis=1).mean()
        metrics["avg_engagement"] = float(avg_engagement) if not pd.isna(avg_engagement) else None
    else:
        metrics["avg_engagement"] = None
    
    # Burnout rate (percentage with both WLB and Job Sat <= 2)
    if "Q1_Job_Satisfaction" in df.columns and "Q2_Work_Life_Balance" in df.columns:
        burnout_count = ((df["Q1_Job_Satisfaction"] <= 2) & (df["Q2_Work_Life_Balance"] <= 2)).sum()
        metrics["burnout_rate"] = float((burnout_count / len(df)) * 100) if len(df) > 0 else None
    else:
        metrics["burnout_rate"] = None
    
    # Turnover risk (percentage with eNPS <= 6 and Growth <= 2)
    if "Q5_eNPS" in df.columns and "Q4_Growth_Opportunities" in df.columns:
        turnover_count = ((df["Q5_eNPS"] <= 6) & (df["Q4_Growth_Opportunities"] <= 2)).sum()
        metrics["turnover_risk"] = float((turnover_count / len(df)) * 100) if len(df) > 0 else None
    else:
        metrics["turnover_risk"] = None
    
    # eNPS calculation
    if "Q5_eNPS" in df.columns:
        enps_scores = df["Q5_eNPS"].dropna()
        if len(enps_scores) > 0:
            promoters = (enps_scores >= 9).sum()
            detractors = (enps_scores <= 6).sum()
            total = len(enps_scores)
            metrics["enps"] = float(((promoters - detractors) / total) * 100) if total > 0 else None
        else:
            metrics["enps"] = None
    else:
        metrics["enps"] = None
    
    return metrics


def aggregate_seasonal_data(df):
    """
    Group and aggregate metrics by season categories.
    
    Args:
        df: DataFrame with parsed season information
    
    Returns:
        list: Aggregated metrics by season category
    """
    seasonal_breakdown = []
    
    # Group by season_type and holiday_name
    grouped = df.groupby(["season_type", "holiday_name"])
    
    for (season_type, holiday_name), group_df in grouped:
        metrics = calculate_seasonal_metrics(group_df)
        metrics["season_category"] = season_type
        metrics["holiday_name"] = holiday_name if holiday_name else "N/A"
        seasonal_breakdown.append(metrics)
    
    # Sort by response count
    seasonal_breakdown.sort(key=lambda x: x["response_count"], reverse=True)
    
    return seasonal_breakdown


def compare_seasonal_periods(df):
    """
    Generate comparative analysis between different periods.
    
    Args:
        df: DataFrame with parsed season information
    
    Returns:
        dict: Comparative analysis
    """
    comparisons = {}
    
    # Festival vs Normal
    festival_df = df[df["season_type"] == "festival"]
    normal_df = df[df["season_type"] == "normal"]
    
    festival_metrics = calculate_seasonal_metrics(festival_df)
    normal_metrics = calculate_seasonal_metrics(normal_df)
    
    comparisons["festival_vs_normal"] = {
        "sentiment_diff": (festival_metrics["avg_sentiment"] - normal_metrics["avg_sentiment"]) if (festival_metrics["avg_sentiment"] is not None and normal_metrics["avg_sentiment"] is not None) else None,
        "engagement_diff": (festival_metrics["avg_engagement"] - normal_metrics["avg_engagement"]) if (festival_metrics["avg_engagement"] is not None and normal_metrics["avg_engagement"] is not None) else None,
        "burnout_diff": (festival_metrics["burnout_rate"] - normal_metrics["burnout_rate"]) if (festival_metrics["burnout_rate"] is not None and normal_metrics["burnout_rate"] is not None) else None,
        "turnover_diff": (festival_metrics["turnover_risk"] - normal_metrics["turnover_risk"]) if (festival_metrics["turnover_risk"] is not None and normal_metrics["turnover_risk"] is not None) else None
    }
    
    # Pre-festival vs Post-festival
    pre_festival_df = df[df["season_type"] == "pre-festival"]
    post_festival_df = df[df["season_type"] == "post-festival"]
    
    pre_metrics = calculate_seasonal_metrics(pre_festival_df)
    post_metrics = calculate_seasonal_metrics(post_festival_df)
    
    comparisons["pre_vs_post_festival"] = {
        "sentiment_diff": (pre_metrics["avg_sentiment"] - post_metrics["avg_sentiment"]) if (pre_metrics["avg_sentiment"] is not None and post_metrics["avg_sentiment"] is not None) else None,
        "engagement_diff": (pre_metrics["avg_engagement"] - post_metrics["avg_engagement"]) if (pre_metrics["avg_engagement"] is not None and post_metrics["avg_engagement"] is not None) else None
    }
    
    return comparisons


def identify_top_festivals(df):
    """
    Rank festivals by response count and impact.
    
    Args:
        df: DataFrame with parsed season information
    
    Returns:
        list: Top festivals with metrics
    """
    # Filter for festival-related responses
    festival_df = df[df["season_type"].isin(["festival", "pre-festival", "post-festival"])]
    
    if festival_df.empty:
        return []
    
    # Group by holiday name
    grouped = festival_df.groupby("holiday_name")
    
    top_festivals = []
    for holiday_name, group_df in grouped:
        if holiday_name is None or holiday_name == "N/A":
            continue
            
        metrics = calculate_seasonal_metrics(group_df)
        
        # Calculate impact score (weighted combination of sentiment and engagement)
        impact_score = 0
        if metrics["avg_sentiment"] is not None and metrics["avg_engagement"] is not None:
            # Normalize sentiment (-1 to 1) to 0-10 scale
            sentiment_normalized = (metrics["avg_sentiment"] + 1) * 5
            # Normalize engagement (1-5) to 0-10 scale
            engagement_normalized = (metrics["avg_engagement"] - 1) * 2.5
            impact_score = (sentiment_normalized * 0.4 + engagement_normalized * 0.6)
        
        top_festivals.append({
            "holiday_name": holiday_name,
            "total_responses": metrics["response_count"],
            "avg_sentiment": metrics["avg_sentiment"],
            "avg_engagement": metrics["avg_engagement"],
            "impact_score": round(impact_score, 2) if impact_score > 0 else None
        })
    
    # Sort by impact score and response count
    top_festivals.sort(key=lambda x: (x["impact_score"] or 0, x["total_responses"]), reverse=True)
    
    return top_festivals[:10]  # Return top 10


def get_sentiment_breakdown(df):
    """
    Calculate sentiment breakdown (positive, negative, neutral counts).
    
    Args:
        df: DataFrame with Sentiment_Label column
    
    Returns:
        dict: Sentiment counts and percentages
    """
    if df.empty or "Sentiment_Label" not in df.columns:
        return {
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "positive_percentage": 0.0,
            "negative_percentage": 0.0,
            "neutral_percentage": 0.0
        }
    
    # Remove NaN values
    sentiment_series = df["Sentiment_Label"].dropna()
    
    if len(sentiment_series) == 0:
        return {
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "positive_percentage": 0.0,
            "negative_percentage": 0.0,
            "neutral_percentage": 0.0
        }
    
    total = len(sentiment_series)
    
    # Convert to lowercase for case-insensitive matching
    sentiment_series = sentiment_series.str.lower().str.strip()
    sentiment_counts = sentiment_series.value_counts().to_dict()
    
    # Try multiple variations of sentiment labels
    positive_count = (
        sentiment_counts.get("positive", 0) + 
        sentiment_counts.get("pos", 0) +
        sentiment_counts.get("1", 0)
    )
    negative_count = (
        sentiment_counts.get("negative", 0) + 
        sentiment_counts.get("neg", 0) +
        sentiment_counts.get("-1", 0)
    )
    neutral_count = (
        sentiment_counts.get("neutral", 0) + 
        sentiment_counts.get("neu", 0) +
        sentiment_counts.get("0", 0)
    )
    
    return {
        "positive_count": int(positive_count),
        "negative_count": int(negative_count),
        "neutral_count": int(neutral_count),
        "positive_percentage": round((positive_count / total * 100), 2) if total > 0 else 0.0,
        "negative_percentage": round((negative_count / total * 100), 2) if total > 0 else 0.0,
        "neutral_percentage": round((neutral_count / total * 100), 2) if total > 0 else 0.0,
        "total_labeled": total,
        "unique_labels": list(sentiment_counts.keys())  # For debugging
    }


@router.get("/debug-events")
async def debug_event_seasons(
    limit: Optional[int] = Query(20, description="Number of unique events to show")
):
    """
    Debug endpoint to see raw Event_Season values and their distribution.
    """
    df = fetch_survey_from_db()
    
    if "Event_Season" not in df.columns:
        return {"error": "Event_Season column not found"}
    
    # Get value counts of raw Event_Season data
    raw_counts = df["Event_Season"].value_counts().head(limit)
    
    # Parse and get distribution
    parsed_seasons = df["Event_Season"].apply(parse_event_season)
    df["season_type"] = parsed_seasons.apply(lambda x: x["season_type"])
    df["holiday_name"] = parsed_seasons.apply(lambda x: x["holiday_name"])
    
    # Get distribution by holiday name
    holiday_counts = df["holiday_name"].value_counts().head(limit)
    season_type_counts = df["season_type"].value_counts()
    
    # Check Sentiment_Label column
    sentiment_info = {}
    if "Sentiment_Label" in df.columns:
        sentiment_counts = df["Sentiment_Label"].value_counts()
        sentiment_info = {
            "sentiment_label_exists": True,
            "sentiment_distribution": sentiment_counts.to_dict(),
            "total_non_null_sentiments": df["Sentiment_Label"].notna().sum(),
            "total_null_sentiments": df["Sentiment_Label"].isna().sum(),
            "sample_sentiment_values": df["Sentiment_Label"].dropna().head(20).tolist()
        }
    else:
        sentiment_info = {
            "sentiment_label_exists": False,
            "available_columns": df.columns.tolist()
        }
    
    return {
        "total_records": len(df),
        "raw_event_season_distribution": raw_counts.to_dict(),
        "parsed_holiday_distribution": holiday_counts.to_dict(),
        "season_type_distribution": season_type_counts.to_dict(),
        "sample_raw_values": df["Event_Season"].dropna().head(20).tolist(),
        "sentiment_info": sentiment_info
    }


@router.get("/top-events")
async def get_top_event_seasons(
    department: Optional[str] = Query(None, description="Filter by department"),
    year: Optional[int] = Query(None, description="Filter by year"),
    quarter: Optional[str] = Query(None, description="Filter by quarter (Q1-Q4)")
):
    """
    Get overview and top 10 event seasons with sentiment breakdown.
    
    Returns:
    - Overall statistics
    - Top 10 event seasons by response count
    - Sentiment breakdown (positive, negative, neutral) for each event season
    """
    # Fetch survey data from database
    df = fetch_survey_from_db()
    
    # Only filter by year if explicitly provided
    if year is not None and "Submission_Date" in df.columns:
        df["Year"] = pd.to_datetime(df["Submission_Date"], errors="coerce").dt.year
        df = df[df["Year"] == year]
    
    # Apply filters
    if department:
        df = df[df["Department"].str.lower() == department.lower()]
    
    if quarter:
        df = df[df["Quarter"].str.upper() == quarter.upper()]
    
    # Overall sentiment breakdown
    overall_sentiment = get_sentiment_breakdown(df)
    
    # Parse Event_Season field
    if "Event_Season" not in df.columns:
        return {
            "overview": {
                "total_responses": 0,
                "sentiment_breakdown": overall_sentiment
            },
            "top_10_events": [],
            "filters_applied": {
                "department": department,
                "year": year,
                "quarter": quarter
            }
        }
    
    parsed_seasons = df["Event_Season"].apply(parse_event_season)
    df["season_type"] = parsed_seasons.apply(lambda x: x["season_type"])
    df["holiday_name"] = parsed_seasons.apply(lambda x: x["holiday_name"])
    
    # Group by holiday_name (the actual festival/event name)
    # This combines festival, pre-festival, and post-festival for the same event
    df["event_name"] = df["holiday_name"].fillna("Normal Day")
    
    # Group by event_name and calculate metrics
    event_groups = df.groupby("event_name")
    
    top_events = []
    for event_name, group_df in event_groups:
        sentiment_breakdown = get_sentiment_breakdown(group_df)
        
        event_data = {
            "event_name": event_name,
            "total_responses": len(group_df),
            "sentiment_breakdown": sentiment_breakdown,
            "avg_sentiment_score": float(group_df["Sentiment_Score"].mean()) if "Sentiment_Score" in group_df.columns and not group_df["Sentiment_Score"].isna().all() else None
        }
        
        top_events.append(event_data)
    
    # Sort by total responses and get top 10
    top_events.sort(key=lambda x: x["total_responses"], reverse=True)
    top_10_events = top_events[:10]
    
    # Calculate overview
    overview = {
        "total_responses": len(df),
        "unique_events": len(top_events),
        "sentiment_breakdown": overall_sentiment
    }
    
    return {
        "overview": overview,
        "top_10_events": top_10_events,
        "filters_applied": {
            "department": department,
            "year": year,
            "quarter": quarter
        }
    }


@router.get("/insights")
async def get_seasonal_insights(
    department: Optional[str] = Query(None, description="Filter by department"),
    year: Optional[int] = Query(None, description="Filter by year"),
    quarter: Optional[str] = Query(None, description="Filter by quarter (Q1-Q4)"),
    season_type: Optional[str] = Query(None, description="Filter by season type (festival, pre-festival, post-festival, normal)")
):
    """
    Get seasonal insights from Event_Season data.
    
    Returns valuable insights including:
    - Seasonal distribution of responses
    - Sentiment trends across different festival periods
    - Engagement patterns during festivals
    - Risk indicators by season
    - Top festivals by impact
    - Comparative analysis
    """
    # Fetch survey data from database
    df = fetch_survey_from_db()
    
    # Default to current year if not specified
    if year is None:
        year = datetime.now().year
    
    # Extract year from Submission_Date
    if "Submission_Date" in df.columns:
        df["Year"] = pd.to_datetime(df["Submission_Date"], errors="coerce").dt.year
        df = df[df["Year"] == year]
    
    # Apply filters
    if department:
        df = df[df["Department"].str.lower() == department.lower()]
    
    if quarter:
        df = df[df["Quarter"].str.upper() == quarter.upper()]
    
    # Parse Event_Season field
    parsed_seasons = df["Event_Season"].apply(parse_event_season)
    df["season_type"] = parsed_seasons.apply(lambda x: x["season_type"])
    df["holiday_name"] = parsed_seasons.apply(lambda x: x["holiday_name"])
    
    # Apply season type filter
    if season_type:
        df = df[df["season_type"] == season_type.lower()]
    
    # Calculate overview statistics
    overview = {
        "total_responses": len(df),
        "festival_responses": len(df[df["season_type"] == "festival"]),
        "pre_festival_responses": len(df[df["season_type"] == "pre-festival"]),
        "post_festival_responses": len(df[df["season_type"] == "post-festival"]),
        "normal_day_responses": len(df[df["season_type"] == "normal"])
    }
    
    # Get seasonal breakdown
    seasonal_breakdown = aggregate_seasonal_data(df)
    
    # Get comparative analysis
    comparative_analysis = compare_seasonal_periods(df)
    
    # Get top festivals
    top_festivals = identify_top_festivals(df)
    
    return {
        "overview": overview,
        "seasonal_breakdown": seasonal_breakdown,
        "comparative_analysis": comparative_analysis,
        "top_festivals": top_festivals,
        "filters_applied": {
            "department": department,
            "year": year,
            "quarter": quarter,
            "season_type": season_type
        }
    }