import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
import re

# Import risk engine functions
from risk_engine import (
    fetch_employees_from_db,
    fetch_workload_from_db,
    fetch_survey_from_db,
    get_dynamodb_resource,
    decimal_to_float,
    calculate_burnout_rate_detailed,
    calculate_turnover_risk_detailed
)

load_dotenv()

# Initialize Ollama client for Llama 3.2
client = OpenAI(
    base_url="http://localhost:11434/v1", 
    api_key="ollama"
)

# ==================== Pydantic Models for Structured Output ====================

class PriorityAction(BaseModel):
    """Model for a priority action recommendation"""
    action: str = Field(..., description="Description of the action to take")
    rationale: str = Field(..., description="Why this action is important")
    timeline: str = Field(..., description="When to implement this action")

class RecommendedEvent(BaseModel):
    """Model for a recommended event or program"""
    event: str = Field(..., description="Name of the event or program")
    description: str = Field(..., description="Details about the event")
    expected_impact: str = Field(..., description="What this will improve")

class LongTermStrategy(BaseModel):
    """Model for a long-term strategy"""
    strategy: str = Field(..., description="Description of the strategy")
    implementation: Optional[str] = Field(None, description="How to implement this strategy")

class RecommendationOutput(BaseModel):
    """Model for the complete recommendation output from AI"""
    priority_actions: List[PriorityAction] = Field(
        default_factory=list,
        description="Top 3 priority actions to address critical issues"
    )
    recommended_events: List[RecommendedEvent] = Field(
        default_factory=list,
        description="Recommended team-building activities, workshops, or initiatives"
    )
    long_term_strategies: List[LongTermStrategy] = Field(
        default_factory=list,
        description="Sustainable changes to improve department culture"
    )
    metrics_to_track: List[str] = Field(
        default_factory=list,
        description="KPIs to monitor improvement"
    )

class RiskContext(BaseModel):
    """Model for risk context data"""
    department: str
    quarter: Optional[str] = None
    year: Optional[int] = None
    total_employees: int = 0
    total_responses: int = 0
    bad_sentiment_count: int = 0
    bad_score_count: int = 0
    burnout_risk_percentage: Optional[float] = None
    turnover_risk_percentage: Optional[float] = None
    avg_job_satisfaction: Optional[float] = None
    avg_work_life_balance: Optional[float] = None
    avg_manager_support: Optional[float] = None
    avg_growth_opportunities: Optional[float] = None
    avg_enps: Optional[float] = None
    avg_sentiment: Optional[float] = None
    avg_workload: Optional[float] = None
    common_bad_categories: List[str] = Field(default_factory=list)
    sample_bad_comments: List[str] = Field(default_factory=list)

class RecommendationResponse(BaseModel):
    """Complete recommendation response model"""
    department: str
    quarter: Optional[str] = None
    year: Optional[int] = None
    context: RiskContext
    recommendations: RecommendationOutput
    generated_at: str
    error: Optional[str] = None

# ==================== Database Retrieval Functions ====================

def get_survey_responses_by_filters(
    department: Optional[str] = None,
    quarter: Optional[str] = None,
    year: Optional[int] = None,
    min_sentiment_score: Optional[float] = None,
    max_sentiment_score: Optional[float] = None,
    bad_score_threshold: float = 5.0
) -> pd.DataFrame:
    """
    Retrieve survey responses from database with filters for bad sentiment, bad scores, etc.
    
    Parameters:
    -----------
    department : str, optional
        Filter by department
    quarter : str, optional
        Filter by quarter (e.g., 'Q1', 'Q2', 'Q3', 'Q4')
    year : int, optional
        Filter by year
    min_sentiment_score : float, optional
        Minimum sentiment score filter
    max_sentiment_score : float, optional
        Maximum sentiment score filter (use this to get bad sentiment)
    bad_score_threshold : float
        Threshold for considering a score as "bad" (default: 5.0)
    
    Returns:
    --------
    pd.DataFrame
        Filtered survey responses with relevant columns
    """
    # Fetch all survey data
    survey_df = fetch_survey_from_db()
    
    if survey_df.empty:
        return pd.DataFrame()
    
    # Apply filters
    filtered_df = survey_df.copy()
    
    if department:
        filtered_df = filtered_df[filtered_df['Department'].str.lower() == department.lower()]
    
    if quarter:
        filtered_df = filtered_df[filtered_df['Quarter'].str.contains(quarter, na=False)]
    
    if year:
        # Extract year from Quarter or Submission_Date
        if 'Submission_Date' in filtered_df.columns:
            filtered_df['Year'] = pd.to_datetime(filtered_df['Submission_Date'], errors='coerce').dt.year
            filtered_df = filtered_df[filtered_df['Year'] == year]

    
    # Filter by sentiment score
    if 'Sentiment_Score' in filtered_df.columns:
        if min_sentiment_score is not None:
            filtered_df = filtered_df[filtered_df['Sentiment_Score'] >= min_sentiment_score]
        if max_sentiment_score is not None:
            filtered_df = filtered_df[filtered_df['Sentiment_Score'] <= max_sentiment_score]
    
    # Identify bad scores (Job Satisfaction, Work-Life Balance, etc.)
    score_columns = ['Q1_Job_Satisfaction', 'Q2_Work_Life_Balance', 
                     'Q3_Manager_Support', 'Q4_Growth_Opportunities', 'Q5_eNPS']
    
    # Add flag for bad scores
    filtered_df['Has_Bad_Score'] = False
    for col in score_columns:
        if col in filtered_df.columns:
            filtered_df['Has_Bad_Score'] |= (filtered_df[col] <= bad_score_threshold)
    
    return filtered_df


def get_risk_summary_by_department(
    department: str,
    quarter: Optional[str] = None,
    year: Optional[int] = None
) -> Dict:
    """
    Get comprehensive risk summary for a specific department.
    
    Parameters:
    -----------
    department : str
        Department name
    quarter : str, optional
        Quarter filter
    year : int, optional
        Year filter
    
    Returns:
    --------
    Dict
        Risk summary including burnout, turnover, and other metrics
    """
    # Get ALL filtered survey data (not just bad sentiment)
    print(department, quarter, year)
    survey_df = get_survey_responses_by_filters(
        department=department,
        quarter=quarter,
        year=year
        # Removed max_sentiment_score filter to get ALL responses
    )
    
    if survey_df.empty:
        return {
            "department": department,
            "quarter": quarter,
            "year": year,
            "error": "No data found for the specified filters"
        }
    
    # Calculate risk metrics with CORRECTED thresholds
    summary = {
        "department": department,
        "quarter": quarter,
        "year": year,
        "total_responses": len(survey_df),
        "bad_sentiment_count": len(survey_df[survey_df['Sentiment_Score'] <= 5.0]) if 'Sentiment_Score' in survey_df.columns else 0,
        "bad_score_count": survey_df['Has_Bad_Score'].sum() if 'Has_Bad_Score' in survey_df.columns else 0,
    }
    
    # Calculate average scores
    score_columns = {
        'Q1_Job_Satisfaction': 'avg_job_satisfaction',
        'Q2_Work_Life_Balance': 'avg_work_life_balance',
        'Q3_Manager_Support': 'avg_manager_support',
        'Q4_Growth_Opportunities': 'avg_growth_opportunities',
        'Q5_eNPS': 'avg_enps',
        'Sentiment_Score': 'avg_sentiment'
    }
    
    for col, key in score_columns.items():
        if col in survey_df.columns:
            summary[key] = float(survey_df[col].mean()) if not survey_df[col].isna().all() else None
    
    # Get common categories from bad responses
    if 'Categories' in survey_df.columns:
        bad_responses = survey_df[survey_df['Has_Bad_Score'] == True]
        categories = bad_responses['Categories'].dropna().tolist()
        summary['common_bad_categories'] = list(set(categories))[:5]  # Top 5 unique categories
    
    # Get sample comments with bad sentiment
    if 'Rephrased_Comment' in survey_df.columns:
        bad_comments = survey_df[
            (survey_df['Sentiment_Score'] <= 5.0) | (survey_df['Has_Bad_Score'] == True)
        ]['Rephrased_Comment'].dropna().head(5).tolist()
        summary['sample_bad_comments'] = bad_comments
    
    # Calculate burnout and turnover risk - Using shared logic from risk_engine
    if 'Q2_Work_Life_Balance' in survey_df.columns and 'Q1_Job_Satisfaction' in survey_df.columns:
        burnout_metrics = calculate_burnout_rate_detailed(
            survey_df['Q2_Work_Life_Balance'], 
            survey_df['Q1_Job_Satisfaction']
        )
        summary['burnout_risk_count'] = int(burnout_metrics['total_severe'])
        # Handle NaN if series was empty
        summary['burnout_risk_percentage'] = round(burnout_metrics['severe_rate'], 2) if pd.notna(burnout_metrics['severe_rate']) else 0.0
    
    if 'Q5_eNPS' in survey_df.columns and 'Q4_Growth_Opportunities' in survey_df.columns:
        turnover_metrics = calculate_turnover_risk_detailed(
            survey_df['Q5_eNPS'], 
            survey_df['Q4_Growth_Opportunities']
        )
        summary['turnover_risk_count'] = int(turnover_metrics['total_high_risk'])
        # Handle NaN if series was empty
        summary['turnover_risk_percentage'] = round(turnover_metrics['high_risk_rate'], 2) if pd.notna(turnover_metrics['high_risk_rate']) else 0.0
    
    # OPTIONAL: Add additional risk breakdowns
    if 'Q2_Work_Life_Balance' in survey_df.columns:
        summary['low_wlb_count'] = int((survey_df['Q2_Work_Life_Balance'] <= 2).sum())
        summary['low_wlb_percentage'] = round((summary['low_wlb_count'] / len(survey_df)) * 100, 2)
    
    if 'Q1_Job_Satisfaction' in survey_df.columns:
        summary['low_job_sat_count'] = int((survey_df['Q1_Job_Satisfaction'] <= 2).sum())
        summary['low_job_sat_percentage'] = round((summary['low_job_sat_count'] / len(survey_df)) * 100, 2)
    
    if 'Q5_eNPS' in survey_df.columns:
        # eNPS breakdown
        summary['detractors_count'] = int((survey_df['Q5_eNPS'] <= 6).sum())
        summary['passives_count'] = int(((survey_df['Q5_eNPS'] >= 7) & (survey_df['Q5_eNPS'] <= 8)).sum())
        summary['promoters_count'] = int((survey_df['Q5_eNPS'] >= 9).sum())
        
        # Calculate eNPS score: (% Promoters - % Detractors)
        total = len(survey_df)
        enps_score = ((summary['promoters_count'] - summary['detractors_count']) / total) * 100 if total > 0 else 0
        summary['enps_score'] = round(enps_score, 2)
    
    if 'Q4_Growth_Opportunities' in survey_df.columns:
        summary['low_growth_count'] = int((survey_df['Q4_Growth_Opportunities'] <= 2).sum())
        summary['low_growth_percentage'] = round((summary['low_growth_count'] / len(survey_df)) * 100, 2)
    
    return summary

def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(i) for i in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    return o


def get_enriched_context_for_recommendations(
    department: str,
    quarter: Optional[str] = None,
    year: Optional[int] = None
) -> Dict:
    """
    Get enriched context including employee and workload data for better recommendations.
    
    Parameters:
    -----------
    department : str
        Department name
    quarter : str, optional
        Quarter filter
    year : int, optional
        Year filter
    
    Returns:
    --------
    Dict
        Enriched context with employee, workload, and survey data
    """
    # Get risk summary
    risk_summary = get_risk_summary_by_department(department, quarter, year)
    
    # Get employee data for the department
    employee_df = fetch_employees_from_db()
    dept_employees = employee_df[employee_df['department'] == department.lower()]
    
    # Get workload data
    workload_df = fetch_workload_from_db()

    
    # Merge to get department workload
    if not workload_df.empty and not dept_employees.empty:
        dept_workload = workload_df.merge(
            dept_employees[['employee_id', 'department']], 
            on='employee_id', 
            how='inner'
        )
        avg_workload = dept_workload['work_load'].mean() if not dept_workload.empty else None
    else:
        avg_workload = None
    
    # Enrich context
    context = {
        **risk_summary,
        "total_employees": len(dept_employees),
        "avg_workload": float(avg_workload) if avg_workload is not None else None,
    }
    
    return context


# ==================== AI Recommendation Engine ====================

def clean_llm_json(raw_text: str):
    """
    Cleans and fixes invalid JSON responses produced by LLMs.
    Returns a Python dictionary.
    """

    # 1. Remove invalid Unicode control characters
    raw_text = re.sub(r"[\x00-\x1F\x7F]", "", raw_text)

    # 2. Replace smart quotes with normal quotes
    raw_text = raw_text.replace("“", '"').replace("”", '"')
    raw_text = raw_text.replace("‘", "'").replace("’", "'")

    # 3. Escape internal quotes inside values: "Example: "text" here"
    # Exclude whitespace from the lookahead to avoid breaking valid JSON like "value" ,
    raw_text = re.sub(r'":\s*"([^"]*?)"([^",}\s])', r'": "\1\"\2', raw_text)

    # 4. Fix missing closing quotes (common LLM mistake)
    raw_text = re.sub(r'\"([^"]*?)\n', r'"\1",\n', raw_text)

    # 5. Remove trailing commas before } or ]
    raw_text = re.sub(r',\s*([}\]])', r'\1', raw_text)

    # 6. Fix malformed event lines like:
    #     "event": "Team-building..., 
    raw_text = re.sub(r'":\s*"([^"]*?),\n', r'": "\1",\n', raw_text)

    # Try parsing normally
    try:
        return json.loads(raw_text)
    except Exception:
        pass  # Try repair pass below

    # 7. Last-resort attempt: Quote unquoted keys using regex
    raw_text = re.sub(r'(\s*)([A-Za-z0-9_]+):', r'\1"\2":', raw_text)

    # Final attempt to parse
    try:
        return json.loads(raw_text)
    except Exception as e:
        raise ValueError(f"Failed to clean/parse JSON: {e}\nCleaned text:\n{raw_text}")

def generate_recommendations_with_llama(
    department: str,
    quarter: Optional[str] = None,
    year: Optional[int] = None,
    focus_areas: Optional[List[str]] = None
) -> Dict:
    """
    Generate actionable recommendations using Llama 3.2 based on retrieved data.
    
    Parameters:
    -----------
    department : str
        Department name
    quarter : str, optional
        Quarter filter (e.g., 'Q1', 'Q2')
    year : int, optional
        Year filter
    focus_areas : List[str], optional
        Specific areas to focus on (e.g., ['burnout', 'turnover', 'engagement'])
    
    Returns:
    --------
    Dict
        Recommendations including actions, events, and strategies
    """
    # Get enriched context
    context = get_enriched_context_for_recommendations(department, quarter, year)
    
    # Check if we have data
    if "error" in context:
        return {
            "department": department,
            "quarter": quarter,
            "year": year,
            "error": context["error"],
            "recommendations": []
        }
    
    # Build prompt for Llama
    prompt = f"""You are an expert HR consultant analyzing employee wellbeing data. Based on the following data for the {department} department, provide specific, actionable recommendations to improve employee satisfaction and reduce risks.

**Department Data Summary:**
- Department: {department}
- Quarter: {quarter or 'All quarters'}
- Year: {year or 'All years'}
- Total Employees: {context.get('total_employees', 'N/A')}
- Total Survey Responses: {context.get('total_responses', 'N/A')}
- Average Workload: {context.get('avg_workload', 'N/A')} hours

**Risk Metrics:**
- Burnout Risk: {context.get('burnout_risk_percentage', 'N/A'):.1f}%
- Turnover Risk: {context.get('turnover_risk_percentage', 'N/A'):.1f}%
- Bad Sentiment Count: {context.get('bad_sentiment_count', 'N/A')} out of {context.get('total_responses', 'N/A')}
- Bad Score Count: {context.get('bad_score_count', 'N/A')} responses

**Average Scores (1-10 scale):**
- Job Satisfaction: {f"{context.get('avg_job_satisfaction'):.2f}" if context.get('avg_job_satisfaction') is not None else 'N/A'}
- Work-Life Balance: {f"{context.get('avg_work_life_balance'):.2f}" if context.get('avg_work_life_balance') is not None else 'N/A'}
- Manager Support: {f"{context.get('avg_manager_support'):.2f}" if context.get('avg_manager_support') is not None else 'N/A'}
- Growth Opportunities: {f"{context.get('avg_growth_opportunities'):.2f}" if context.get('avg_growth_opportunities') is not None else 'N/A'}
- eNPS: {f"{context.get('avg_enps'):.2f}" if context.get('avg_enps') is not None else 'N/A'}
- Sentiment: {f"{context.get('avg_sentiment'):.2f}" if context.get('avg_sentiment') is not None else 'N/A'}

**Common Issues (Categories):**
{', '.join(context.get('common_bad_categories', [])) if context.get('common_bad_categories') else 'None identified'}

**Sample Employee Comments:**
{chr(10).join(['- ' + comment for comment in context.get('sample_bad_comments', [])[:3]]) if context.get('sample_bad_comments') else 'No comments available'}

**Focus Areas:** {', '.join(focus_areas) if focus_areas else 'All areas'}

Based on this data, provide:
1. **Top 3 Priority Actions** - Immediate steps to address the most critical issues
2. **Recommended Events/Programs** - Specific team-building activities, workshops, or initiatives
3. **Long-term Strategies** - Sustainable changes to improve department culture
4. **Metrics to Track** - KPIs to monitor improvement

Format your response as a JSON object with the following structure:
{{
    "priority_actions": [
        {{"action": "description", "rationale": "why this is important", "timeline": "when to implement"}}
    ],
    "recommended_events": [
        {{"event": "name", "description": "details", "expected_impact": "what this will improve"}}
    ],
    "long_term_strategies": [
        {{"strategy": "description", "implementation": "how to implement"}}
    ],
    "metrics_to_track": ["metric1", "metric2", "metric3"]
}}

Provide only the JSON response, no additional text."""

    try:
        # Call Llama 3.2 via Ollama
        response = client.chat.completions.create(
            model="llama3.2",
            messages=[
                {"role": "system", "content": "You are an expert HR consultant specializing in employee wellbeing and organizational development. Provide data-driven, actionable recommendations in JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Extract response
        recommendation_text = response.choices[0].message.content.strip()
        
        # Try to parse JSON and validate with Pydantic
        try:
            # Remove markdown code blocks if present
            if recommendation_text.startswith("```json"):
                recommendation_text = recommendation_text.split("```json")[1].split("```")[0].strip()
            elif recommendation_text.startswith("```"):
                recommendation_text = recommendation_text.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            recommendations_dict = json.loads(recommendation_text)
            
            # Validate with Pydantic model
            try:
                recommendations = RecommendationOutput(**recommendations_dict)
                recommendations_dict = recommendations.model_dump()
            except Exception as validation_error:
                # If Pydantic validation fails, use raw dict
                print(f"⚠️  Pydantic validation warning: {validation_error}")
                # Keep the raw dict but ensure it has the expected structure
                if not isinstance(recommendations_dict, dict):
                    recommendations_dict = {"raw_response": str(recommendations_dict)}
                    
        except json.JSONDecodeError as e:
            # If JSON parsing fails, return raw text
            recommendations_dict = {
                "raw_response": recommendation_text,
                "note": f"Failed to parse JSON: {str(e)}"
            }
        
        # Validate context with Pydantic
        try:
            validated_context = RiskContext(**context)
            context_dict = validated_context.model_dump()
        except Exception as e:
            print(f"⚠️  Context validation warning: {e}")
            context_dict = context

        try:
            recommendations_dict = RecommendationOutput(**recommendations_dict).model_dump()
        except Exception as e:
            print(f"⚠️  Recommendations validation warning: {e}")
            recommendations_dict = {"raw_response": str(recommendations_dict)}
        
        # Build final response
        result = {
            "department": department,
            "quarter": quarter,
            "year": year,
            "context": context_dict,
            "recommendations": recommendations_dict,
            "generated_at": pd.Timestamp.now().isoformat()
        }
        
        # Clean and validate JSON response
        try:
            cleaned_json = clean_llm_json(recommendation_text)
            recommendations_dict = RecommendationOutput(**cleaned_json).model_dump()
        except Exception as e:
            print(f"⚠️  JSON cleaning error: {e}")
            recommendations_dict = {"raw_response": recommendation_text}
        
        return result
        
    except Exception as e:
        return {
            "department": department,
            "quarter": quarter,
            "year": year,
            "error": f"Failed to generate recommendations: {str(e)}",
            "context": context
        }



# ==================== Utility Functions ====================


def print_recommendations_summary(recommendations: Dict):
    """Print a formatted summary of recommendations."""
    print("\n" + "=" * 80)
    print(f"RECOMMENDATIONS FOR {recommendations['department'].upper()}")
    print("=" * 80)
    
    if "error" in recommendations:
        print(f"\n❌ Error: {recommendations['error']}")
        return
    
    context = recommendations.get('context', {})
    print(f"\n📊 Context:")
    print(f"   Quarter: {recommendations['quarter'] or 'All'}")
    print(f"   Year: {recommendations['year'] or 'All'}")
    print(f"   Total Employees: {context.get('total_employees', 'N/A')}")
    print(f"   Burnout Risk: {context.get('burnout_risk_percentage', 0):.1f}%")
    print(f"   Turnover Risk: {context.get('turnover_risk_percentage', 0):.1f}%")
    
    recs = recommendations.get('recommendations', {})
    
    if isinstance(recs, dict) and 'priority_actions' in recs:
        print(f"\n🎯 Priority Actions:")
        for i, action in enumerate(recs['priority_actions'], 1):
            print(f"   {i}. {action.get('action', 'N/A')}")
            print(f"      Rationale: {action.get('rationale', 'N/A')}")
            print(f"      Timeline: {action.get('timeline', 'N/A')}\n")
        
        print(f"🎉 Recommended Events:")
        for i, event in enumerate(recs.get('recommended_events', []), 1):
            print(f"   {i}. {event.get('event', 'N/A')}")
            print(f"      {event.get('description', 'N/A')}")
            print(f"      Expected Impact: {event.get('expected_impact', 'N/A')}\n")
        
        print(f"📈 Long-term Strategies:")
        for i, strategy in enumerate(recs.get('long_term_strategies', []), 1):
            print(f"   {i}. {strategy.get('strategy', 'N/A')}")
            print(f"      Implementation: {strategy.get('implementation', 'N/A')}\n")
        
        print(f"📊 Metrics to Track:")
        for metric in recs.get('metrics_to_track', []):
            print(f"   - {metric}")
    else:
        print(f"\n📝 Raw Response:")
        print(json.dumps(recs, indent=2))
    
    print("\n" + "=" * 80)


# ==================== Example Usage ====================

if __name__ == "__main__":
    print("=" * 80)
    print("EMPLOYEE WELLBEING RECOMMENDATION AGENT")
    print("Powered by Llama 3.2")
    print("=" * 80)
    
    # Example 1: Generate recommendations for a specific department
    print("\n📋 Example 1: Single Department Recommendations")
    recommendations = generate_recommendations_with_llama(
        department="Marketing",
        quarter="Q4",
        year=2024,
        focus_areas=["burnout", "work_life_balance"]
    )
    print_recommendations_summary(recommendations)
    
    
