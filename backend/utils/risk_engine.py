import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import json
import boto3
import os
from decimal import Decimal
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# --- Database Connection ---

def get_dynamodb_resource():
    """Get DynamoDB resource connection"""
    return boto3.resource(
        "dynamodb",
        region_name=os.getenv("AWS_REGION")
    )

def decimal_to_float(obj):
    """Convert Decimal objects to float for pandas compatibility"""
    if isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: decimal_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj

def fetch_employees_from_db() -> pd.DataFrame:
    """
    Fetch all employee data from DynamoDB Employees table.
    
    Returns:
    --------
    pd.DataFrame
        Columns: Employee_ID, Department, Hire_Date, Is_Active
    """
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table("Employees")
    
    # Scan all items from the table
    response = table.scan()
    items = response.get('Items', [])
    
    # Handle pagination if there are more items
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))
    
    # Convert to DataFrame
    items = decimal_to_float(items)
    df = pd.DataFrame(items)
    
    # Rename columns to match expected format
    if not df.empty:
        df.rename(columns={
            'Employee_ID': 'employee_id',
            'Department': 'department',
            'Hire_Date': 'hire_date',
            'Is_Active': 'is_active'
        }, inplace=True)
        
        # Calculate tenure_year from hire_date
        if 'hire_date' in df.columns:
            df['hire_date'] = pd.to_datetime(df['hire_date'], errors='coerce')
            current_date = pd.Timestamp.now()
            df['tenure_year'] = (current_date - df['hire_date']).dt.days / 365.25
    
    return df

def fetch_workload_from_db() -> pd.DataFrame:
    """
    Fetch all workload data from DynamoDB Employee_Workload table.
    
    Returns:
    --------
    pd.DataFrame
        Columns: Workload_ID, Employee_ID, Date, Hours_Logged
    """
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table("Employee_Workload")
    
    # Scan all items from the table
    response = table.scan()
    items = response.get('Items', [])
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))
    
    # Convert to DataFrame
    items = decimal_to_float(items)
    df = pd.DataFrame(items)
    
    # Rename columns to match expected format
    if not df.empty:
        df.rename(columns={
            'Employee_ID': 'employee_id',
            'Date': 'date',
            'Hours_Logged': 'work_load'
        }, inplace=True)
    
    return df

def fetch_survey_from_db() -> pd.DataFrame:
    """
    Fetch all survey response data from DynamoDB Processed_Survey_Response table.
    
    Returns:
    --------
    pd.DataFrame
        Columns: Response_ID, Quarter, Submission_Date, Department,
                 Q1_Job_Satisfaction, Q2_Work_Life_Balance, Q3_Manager_Support,
                 Q4_Growth_Opportunities, Q5_eNPS, Comments, Event_Season,
                 Rephrased_Comment, Categories, Sentiment_Score
    """
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table("Survey_Response")
    
    # Scan all items from the table
    response = table.scan()
    items = response.get('Items', [])
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))
    
    # Convert to DataFrame
    items = decimal_to_float(items)
    df = pd.DataFrame(items)
    
    # Rename Raw_Comment to Comments for consistency
    if not df.empty and 'Raw_Comment' in df.columns:
        df.rename(columns={'Raw_Comment': 'Comments'}, inplace=True)
    
    return df

# --- 1. Helper Logic (Pure Functions) ---

def calculate_enps_score(scores: pd.Series) -> float:
    """
    Calculates the Net Promoter Score (NPS) from a series of scores (0-10).
    Formula: % Promoters (9-10) - % Detractors (0-6)
    """
    if len(scores) == 0:
        return np.nan
    
    promoters = (scores >= 9).sum()
    detractors = (scores <= 6).sum()
    total = len(scores)
    
    return ((promoters - detractors) / total) * 100

def calculate_burnout_score(work_life_balance: pd.Series, job_satisfaction: pd.Series) -> float:
    """
    Calculates burnout indicator based on low work-life balance and job satisfaction.
    Higher score = higher burnout risk (inverse of wellness)
    """
    if len(work_life_balance) == 0:
        return np.nan
    
    # Inverse scoring: 10 - average gives us burnout indicator
    wellness_score = (work_life_balance + job_satisfaction) / 2
    burnout_score = 10 - wellness_score.mean()
    
    return burnout_score

def calculate_burnout_rate(work_life_balance: pd.Series, job_satisfaction: pd.Series) -> float:
    """
    Calculates percentage of employees at high burnout risk using tiered approach.
    
    For 1-5 scale metrics:
    - Severe burnout: BOTH WLB AND Job Sat <= 2 (bottom 40% on both)
    
    This identifies the most critical cases where employees are struggling
    in BOTH work-life balance AND job satisfaction simultaneously.
    
    Parameters:
    -----------
    work_life_balance : pd.Series
        Work-life balance scores (1-5 scale)
    job_satisfaction : pd.Series
        Job satisfaction scores (1-5 scale)
    
    Returns:
    --------
    float
        Percentage of employees at severe burnout risk
    """
    if len(work_life_balance) == 0:
        return np.nan
    
    # Align the series (only compare rows where both exist)
    common_idx = work_life_balance.index.intersection(job_satisfaction.index)
    wlb_aligned = work_life_balance.loc[common_idx]
    job_sat_aligned = job_satisfaction.loc[common_idx]
    
    if len(wlb_aligned) == 0:
        return np.nan
    
    # Severe burnout: BOTH metrics are critically low (≤ 2)
    severe_burnout = ((wlb_aligned <= 2) & (job_sat_aligned <= 2)).sum()
    
    total = len(wlb_aligned)
    
    return (severe_burnout / total) * 100

def calculate_burnout_rate_detailed(work_life_balance: pd.Series, job_satisfaction: pd.Series) -> Dict[str, float]:
    """
    Calculates detailed burnout risk breakdown with three tiers.
    
    Returns:
    --------
    dict
        {
            'severe_rate': % with both metrics ≤ 2,
            'moderate_rate': % with either metric ≤ 2,
            'at_risk_rate': % with either metric ≤ 3,
            'total_severe': count of severe cases,
            'total_moderate': count of moderate cases,
            'total_at_risk': count of at-risk cases
        }
    """
    if len(work_life_balance) == 0:
        return {
            'severe_rate': np.nan,
            'moderate_rate': np.nan,
            'at_risk_rate': np.nan,
            'total_severe': 0,
            'total_moderate': 0,
            'total_at_risk': 0
        }
    
    # Align series
    common_idx = work_life_balance.index.intersection(job_satisfaction.index)
    wlb = work_life_balance.loc[common_idx]
    job_sat = job_satisfaction.loc[common_idx]
    
    if len(wlb) == 0:
        return {
            'severe_rate': np.nan,
            'moderate_rate': np.nan,
            'at_risk_rate': np.nan,
            'total_severe': 0,
            'total_moderate': 0,
            'total_at_risk': 0
        }
    
    total = len(wlb)
    
    # Three tiers of burnout risk
    severe = ((wlb <= 2) & (job_sat <= 2)).sum()      # Critical: both very low
    moderate = ((wlb <= 2) | (job_sat <= 2)).sum()    # Concerning: at least one very low
    at_risk = ((wlb <= 3) | (job_sat <= 3)).sum()     # Watch: at least one below average
    
    return {
        'severe_rate': (severe / total) * 100,
        'moderate_rate': (moderate / total) * 100,
        'at_risk_rate': (at_risk / total) * 100,
        'total_severe': severe,
        'total_moderate': moderate,
        'total_at_risk': at_risk
    }

def calculate_turnover_risk(enps_scores: pd.Series, growth_opp: pd.Series) -> float:
    """
    Calculates percentage of employees at high turnover risk using refined criteria.
    
    High turnover risk = Detractors (eNPS ≤ 6) WHO ALSO have low growth opportunities (≤ 2)
    
    This identifies employees who are:
    1. Unlikely to recommend the company (detractors)
    2. See no career growth path
    
    For 0-10 eNPS scale: ≤ 6 = Detractor (standard NPS definition)
    For 1-5 Growth scale: ≤ 2 = Low opportunity (bottom 40%)
    
    Parameters:
    -----------
    enps_scores : pd.Series
        eNPS scores (0-10 scale)
    growth_opp : pd.Series
        Growth opportunity scores (1-5 scale)
    
    Returns:
    --------
    float
        Percentage of employees at high turnover risk
    """
    if len(enps_scores) == 0:
        return np.nan
    
    # Align the series
    common_idx = enps_scores.index.intersection(growth_opp.index)
    enps_aligned = enps_scores.loc[common_idx]
    growth_aligned = growth_opp.loc[common_idx]
    
    if len(enps_aligned) == 0:
        return np.nan
    
    # High risk: Detractors (eNPS ≤ 6) AND low growth (≤ 2)
    # Using AND because we want the intersection of both risk factors
    high_risk = ((enps_aligned <= 6) & (growth_aligned <= 2)).sum()
    
    total = len(enps_aligned)
    
    return (high_risk / total) * 100

def calculate_turnover_risk_detailed(enps_scores: pd.Series, growth_opp: pd.Series) -> Dict[str, float]:
    """
    Calculates detailed turnover risk breakdown with multiple tiers.
    
    Returns:
    --------
    dict
        {
            'high_risk_rate': % detractors with low growth,
            'moderate_risk_rate': % detractors OR low growth,
            'detractor_rate': % who are detractors (eNPS ≤ 6),
            'low_growth_rate': % with low growth opportunities (≤ 2),
            'total_high_risk': count of high risk,
            'total_detractors': count of detractors,
            'total_low_growth': count with low growth
        }
    """
    if len(enps_scores) == 0:
        return {
            'high_risk_rate': np.nan,
            'moderate_risk_rate': np.nan,
            'detractor_rate': np.nan,
            'low_growth_rate': np.nan,
            'total_high_risk': 0,
            'total_detractors': 0,
            'total_low_growth': 0
        }
    
    # Align series
    common_idx = enps_scores.index.intersection(growth_opp.index)
    enps = enps_scores.loc[common_idx]
    growth = growth_opp.loc[common_idx]
    
    if len(enps) == 0:
        return {
            'high_risk_rate': np.nan,
            'moderate_risk_rate': np.nan,
            'detractor_rate': np.nan,
            'low_growth_rate': np.nan,
            'total_high_risk': 0,
            'total_detractors': 0,
            'total_low_growth': 0
        }
    
    total = len(enps)
    
    # Calculate risk tiers
    detractors = (enps <= 6).sum()
    low_growth = (growth <= 2).sum()
    high_risk = ((enps <= 6) & (growth <= 2)).sum()        # Both conditions
    moderate_risk = ((enps <= 6) | (growth <= 2)).sum()    # Either condition
    
    return {
        'high_risk_rate': (high_risk / total) * 100,
        'moderate_risk_rate': (moderate_risk / total) * 100,
        'detractor_rate': (detractors / total) * 100,
        'low_growth_rate': (low_growth / total) * 100,
        'total_high_risk': high_risk,
        'total_detractors': detractors,
        'total_low_growth': low_growth
    }

def calculate_response_rate(actual_responses: int, total_employees: int) -> float:
    """
    Calculates response rate based on actual responses vs total employees.
    """
    if total_employees == 0:
        return np.nan
    
    return (actual_responses / total_employees) * 100

def calculate_workload_score(workload_series: pd.Series) -> float:
    """
    Calculates average workload score from workload data.
    """
    if len(workload_series) == 0:
        return np.nan
    return workload_series.mean()

# --- 2. Data Loading & Merging ---

def load_and_merge_data(
    employee_df: pd.DataFrame,
    workload_df: pd.DataFrame,
    survey_df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Merges employee, workload, and survey data at DEPARTMENT LEVEL.
    
    Employee and workload data are aggregated by department to enrich survey responses
    with average tenure and workload metrics per department.
    
    Parameters:
    -----------
    employee_df : pd.DataFrame
        Columns: employee_id, department, tenure_year
    workload_df : pd.DataFrame
        Columns: employee_id, work_load, date
    survey_df : pd.DataFrame
        Columns: Response_ID, Quarter, Submission_Date, Department, 
                 Q1_Job_Satisfaction, Q2_Work_Life_Balance, Q3_Manager_Support,
                 Q4_Growth_Opportunities, Q5_eNPS, Comments, Event_Season,
                 Rephrased_Comment, Categories, Sentiment_Score
    
    Returns:
    --------
    Tuple[pd.DataFrame, pd.DataFrame]
        (merged_data, employee_master) - merged survey data and employee master list
    """
    
    # Clean column names - remove extra spaces and standardize
    employee_df.columns = employee_df.columns.str.strip()
    workload_df.columns = workload_df.columns.str.strip()
    survey_df.columns = survey_df.columns.str.strip()
    
    # Convert dates
    if 'date' in workload_df.columns:
        workload_df['date'] = pd.to_datetime(workload_df['date'], errors='coerce')
    
    if 'Submission_Date' in survey_df.columns:
        survey_df['Submission_Date'] = pd.to_datetime(survey_df['Submission_Date'], errors='coerce')
    
    # --- Aggregate employee data by department ---
    if 'department' in employee_df.columns and 'tenure_year' in employee_df.columns:
        dept_tenure = employee_df.groupby('department').agg({
            'tenure_year': 'mean',
            'employee_id': 'count'  # Count employees per department
        }).reset_index()
        dept_tenure.rename(columns={
            'tenure_year': 'avg_dept_tenure',
            'employee_id': 'total_employees'
        }, inplace=True)
    else:
        dept_tenure = pd.DataFrame(columns=['department', 'avg_dept_tenure', 'total_employees'])
    
    # --- Aggregate workload by department ---
    # First, get average workload per employee, then average by department
    if 'employee_id' in workload_df.columns and 'work_load' in workload_df.columns:
        # Merge workload with employee to get department info
        workload_with_dept = workload_df.merge(
            employee_df[['employee_id', 'department']], 
            on='employee_id', 
            how='left'
        )
        
        # Aggregate by department
        dept_workload = workload_with_dept.groupby('department').agg({
            'work_load': 'mean'
        }).reset_index()
        dept_workload.rename(columns={'work_load': 'avg_dept_workload'}, inplace=True)
    else:
        dept_workload = pd.DataFrame(columns=['department', 'avg_dept_workload'])
    
    # --- Merge survey data with department-level aggregates ---
    merged_data = survey_df.copy()
    
    # Merge with department tenure data
    if not dept_tenure.empty and 'Department' in merged_data.columns:
        merged_data = merged_data.merge(
            dept_tenure,
            left_on='Department',
            right_on='department',
            how='left'
        )
        # Drop duplicate department column
        if 'department' in merged_data.columns:
            merged_data.drop(columns=['department'], inplace=True)
    else:
        merged_data['avg_dept_tenure'] = np.nan
        merged_data['total_employees'] = 0
    
    # Merge with department workload data
    if not dept_workload.empty and 'Department' in merged_data.columns:
        merged_data = merged_data.merge(
            dept_workload,
            left_on='Department',
            right_on='department',
            how='left'
        )
        # Drop duplicate department column
        if 'department' in merged_data.columns:
            merged_data.drop(columns=['department'], inplace=True)
    else:
        merged_data['avg_dept_workload'] = np.nan
    
    return merged_data, employee_df

# --- 3. Data Processing ---

def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepares the merged dataframe and calculates derived metrics.
    """
    data = df.copy()

    # Ensure Year column exists
    if 'Year' not in data.columns or data['Year'].isna().all():
        if 'Submission_Date' in data.columns:
            # Parse Submission_Date (YYYY-MM-DD) to extract Year
            data['Year'] = pd.to_datetime(data['Submission_Date'], format='%Y-%m-%d', errors='coerce').dt.year
        else:
            data['Year'] = datetime.now().year
    
    # Calculate row-level Overall Engagement (Average of Q1-Q4)
    engagement_cols = ['Q1_Job_Satisfaction', 'Q2_Work_Life_Balance', 
                       'Q3_Manager_Support', 'Q4_Growth_Opportunities']
    
    available_cols = [col for col in engagement_cols if col in data.columns]
    if available_cols:
        data['Overall_Engagement'] = data[available_cols].mean(axis=1)
    
    return data

def aggregate_metrics(
    merged_df: pd.DataFrame, 
    employee_df: pd.DataFrame,
    group_by: List[str] = None
) -> pd.DataFrame:
    """
    Groups data and calculates comprehensive metrics.
    
    Parameters:
    -----------
    merged_df : pd.DataFrame
        Merged survey + employee + workload data
    employee_df : pd.DataFrame
        Employee master data for calculating response rates
    group_by : List[str]
        Columns to group by (default: ['Department', 'Quarter'])
    
    Returns:
    --------
    pd.DataFrame
        Aggregated metrics by group
    """
    
    if group_by is None:
        group_by = ['Department', 'Year', 'Quarter']
    
    # Filter to only existing columns
    group_by = [col for col in group_by if col in merged_df.columns]
    
    if not group_by:
        raise ValueError("No valid grouping columns found")
    
    results = []
    
    for group_values, group_data in merged_df.groupby(group_by):
        # Handle single or multiple group_by columns
        if isinstance(group_values, tuple):
            group_dict = dict(zip(group_by, group_values))
        else:
            group_dict = {group_by[0]: group_values}
        
        # Get department for calculating response rate
        dept = group_dict.get('Department', 'Unknown')
        
        # Get total employees from department-level data (already in merged data)
        if 'total_employees' in group_data.columns:
            total_employees = group_data['total_employees'].iloc[0] if not group_data['total_employees'].isna().all() else 0
        else:
            total_employees = 0
        
        # Extract metric columns
        enps_scores = group_data['Q5_eNPS'].dropna() if 'Q5_eNPS' in group_data.columns else pd.Series([])
        wlb_scores = group_data['Q2_Work_Life_Balance'].dropna() if 'Q2_Work_Life_Balance' in group_data.columns else pd.Series([])
        job_sat_scores = group_data['Q1_Job_Satisfaction'].dropna() if 'Q1_Job_Satisfaction' in group_data.columns else pd.Series([])
        growth_scores = group_data['Q4_Growth_Opportunities'].dropna() if 'Q4_Growth_Opportunities' in group_data.columns else pd.Series([])
        
        # Count unique employees who responded (not total responses)
        # This prevents inflated response rates when employees respond multiple times
        if 'Employee_ID' in group_data.columns:
            unique_respondents = group_data['Employee_ID'].nunique()
        elif 'Response_ID' in group_data.columns:
            # Fallback: if no Employee_ID, count unique Response_IDs
            unique_respondents = group_data['Response_ID'].nunique()
        else:
            # Last resort: count total rows
            unique_respondents = len(group_data)
        
        metrics = group_dict.copy()
        metrics.update({
            'Response_Count': unique_respondents,
            'Total_Employees': total_employees,
            'Response_Rate': calculate_response_rate(unique_respondents, total_employees),
            
            # Core Engagement Metrics (1-10 scale)
            'Job_Satisfaction': job_sat_scores.mean() if len(job_sat_scores) > 0 else np.nan,
            'Work_Life_Balance': wlb_scores.mean() if len(wlb_scores) > 0 else np.nan,
            'Manager_Support': group_data['Q3_Manager_Support'].mean() if 'Q3_Manager_Support' in group_data.columns else np.nan,
            'Growth_Opportunities': growth_scores.mean() if len(growth_scores) > 0 else np.nan,
            'Overall_Engagement': group_data['Overall_Engagement'].mean() if 'Overall_Engagement' in group_data.columns else np.nan,
            
            # eNPS Metrics
            'eNPS': calculate_enps_score(enps_scores),
            'eNPS_Promoters': (enps_scores >= 9).sum() if len(enps_scores) > 0 else 0,
            'eNPS_Passives': ((enps_scores >= 7) & (enps_scores <= 8)).sum() if len(enps_scores) > 0 else 0,
            'eNPS_Detractors': (enps_scores <= 6).sum() if len(enps_scores) > 0 else 0,
            'Avg_eNPS_Score': enps_scores.mean() if len(enps_scores) > 0 else np.nan,
            
            # Burnout Metrics
            'Burnout_Score': calculate_burnout_score(wlb_scores, job_sat_scores),
            'Burnout_Rate': calculate_burnout_rate(wlb_scores, job_sat_scores),
            
            # Turnover Risk
            'Turnover_Risk': calculate_turnover_risk(enps_scores, growth_scores),
            
            # Workload Metrics (department-level average)
            'Avg_Workload': group_data['avg_dept_workload'].mean() if 'avg_dept_workload' in group_data.columns else np.nan,
            
            # Sentiment Analysis
            'Avg_Sentiment': group_data['Sentiment_Score'].mean() if 'Sentiment_Score' in group_data.columns else np.nan,
            
        })
        
        results.append(metrics)
    
    # Create DataFrame
    metrics_df = pd.DataFrame(results)
    
    # Round numeric columns
    numeric_cols = ['Job_Satisfaction', 'Work_Life_Balance', 'Manager_Support', 
                    'Growth_Opportunities', 'Overall_Engagement', 'eNPS', 'Avg_eNPS_Score',
                    'Burnout_Score', 'Burnout_Rate', 'Turnover_Risk', 'Response_Rate',
                    'Avg_Sentiment', 'Avg_Tenure_Years', 'Avg_Workload']
    
    existing_numeric_cols = [col for col in numeric_cols if col in metrics_df.columns]
    metrics_df[existing_numeric_cols] = metrics_df[existing_numeric_cols].round(2)
    
    # Sort by grouping columns
    sort_cols = [col for col in group_by if col in metrics_df.columns]
    if sort_cols:
        metrics_df = metrics_df.sort_values(sort_cols).reset_index(drop=True)
    
    return metrics_df

# --- 4. Orchestration ---

def calculate_metrics_percentage_json(
    df: pd.DataFrame, 
    scale_cols: List[str] = None, 
    keep_cols: List[str] = None
) -> List[Dict]:
    """
    Converts metric scores to percentages and returns a list of dictionaries.
    """
    
    if scale_cols is None:
        scale_cols = [
            'Job_Satisfaction', 
            'Work_Life_Balance', 
            'Manager_Support', 
            'Growth_Opportunities', 
            'Overall_Engagement',
            'Burnout_Score',
            'Avg_Workload'
        ]
    
    if keep_cols is None:
        keep_cols = ['eNPS', 'Response_Count', 'Total_Employees', 'Burnout_Rate', 
                     'Turnover_Risk', 'Response_Rate', 'Avg_Sentiment', 'Avg_Tenure_Years']

    valid_scale_cols = [c for c in scale_cols if c in df.columns]
    valid_keep_cols = [c for c in keep_cols if c in df.columns]

    output_data = []

    for _, row in df.iterrows():
        metrics_dict = {}
        
        # Convert 1-10 scale to 0-100%
        for col in valid_scale_cols:
            if pd.notna(row[col]):
                metrics_dict[col] = round(row[col] * 10, 1)
            
        # Add non-scaled metrics as is
        for col in valid_keep_cols:
            if pd.notna(row[col]):
                metrics_dict[col] = row[col]

        # Build the structure with all grouping columns
        entry = {}
        for col in df.columns:
            if col not in valid_scale_cols and col not in valid_keep_cols:
                if col in ['Quarter', 'Department', 'Year']:
                    entry[col] = row[col]
        
        entry['Metrics'] = metrics_dict
        output_data.append(entry)

    return output_data

def analyze_survey_data(
    employee_csv: str = None,
    workload_csv: str = None,
    survey_csv: str = None,
    employee_df: pd.DataFrame = None,
    workload_df: pd.DataFrame = None,
    survey_df: pd.DataFrame = None,
    group_by: List[str] = None,
    return_json: bool = False
) -> pd.DataFrame:
    """
    Main entry point function. Loads and analyzes multi-table survey data.
    
    Parameters:
    -----------
    employee_csv : str, optional
        Path to employee.csv file
    workload_csv : str, optional
        Path to workload.csv file
    survey_csv : str, optional
        Path to survey response CSV file
    employee_df : pd.DataFrame, optional
        Pre-loaded employee DataFrame
    workload_df : pd.DataFrame, optional
        Pre-loaded workload DataFrame
    survey_df : pd.DataFrame, optional
        Pre-loaded survey DataFrame
    group_by : List[str], optional
        Columns to group by (default: ['Department', 'Quarter'])
    return_json : bool
        If True, returns JSON-formatted data with percentage scores
        
    Returns:
    --------
    pd.DataFrame or List[Dict]
        Metrics summary as dataframe or JSON format
    """
    
    # Load data from CSV if paths provided
    if employee_csv and employee_df is None:
        employee_df = pd.read_csv(employee_csv)
    
    if workload_csv and workload_df is None:
        workload_df = pd.read_csv(workload_csv)
    
    if survey_csv and survey_df is None:
        survey_df = pd.read_csv(survey_csv)
    
    # Validate inputs
    if employee_df is None:
        raise ValueError("employee_df or employee_csv must be provided")
    if survey_df is None:
        raise ValueError("survey_df or survey_csv must be provided")
    if workload_df is None:
        # Create empty workload df if not provided
        workload_df = pd.DataFrame(columns=['employee_id', 'work_load', 'date'])
    
    # Merge data
    merged_data, employee_master = load_and_merge_data(employee_df, workload_df, survey_df)
    
    # Preprocess
    processed_df = preprocess_data(merged_data)
    
    # Aggregate metrics
    final_metrics = aggregate_metrics(processed_df, employee_master, group_by)
    
    if return_json:
        return calculate_metrics_percentage_json(final_metrics)
    
    return final_metrics

def analyze_survey_data_from_db(
    group_by: List[str] = None,
    return_json: bool = False
) -> pd.DataFrame:
    """
    Analyzes survey data by fetching directly from DynamoDB tables.
    
    This function replaces CSV file loading with database queries to:
    - Employees table
    - Employee_Workload table  
    - Processed_Survey_Response table
    
    Parameters:
    -----------
    group_by : List[str], optional
        Columns to group by (default: ['Department', 'Year', 'Quarter'])
    return_json : bool
        If True, returns JSON-formatted data with percentage scores
        
    Returns:
    --------
    pd.DataFrame or List[Dict]
        Metrics summary as dataframe or JSON format
        
    Example:
    --------
    >>> # Get metrics grouped by Department and Quarter
    >>> metrics = analyze_survey_data_from_db()
    >>> print_metrics_summary(metrics)
    
    >>> # Get JSON format for API response
    >>> json_data = analyze_survey_data_from_db(return_json=True)
    
    >>> # Custom grouping
    >>> metrics = analyze_survey_data_from_db(group_by=['Department', 'Quarter'])
    """
    
    print("📊 Fetching data from DynamoDB...")
    
    # Fetch data from database
    print("  ↳ Loading employee data...")
    employee_df = fetch_employees_from_db()
    print(f"    ✓ Loaded {len(employee_df)} employees")
    
    print("  ↳ Loading workload data...")
    workload_df = fetch_workload_from_db()
    print(f"    ✓ Loaded {len(workload_df)} workload records")
    
    print("  ↳ Loading survey responses...")
    survey_df = fetch_survey_from_db()
    print(f"    ✓ Loaded {len(survey_df)} survey responses")
    
    # Validate data
    if employee_df.empty:
        raise ValueError("No employee data found in database")
    if survey_df.empty:
        raise ValueError("No survey data found in database")
    
    # If workload is empty, create empty dataframe with proper structure
    if workload_df.empty:
        workload_df = pd.DataFrame(columns=['employee_id', 'work_load', 'date'])
    
    print("\n🔄 Processing data...")
    
    # Merge data
    merged_data, employee_master = load_and_merge_data(employee_df, workload_df, survey_df)
    print(f"  ✓ Merged {len(merged_data)} records")
    
    # Preprocess
    processed_df = preprocess_data(merged_data)
    print(f"  ✓ Preprocessed data")
    
    # Aggregate metrics
    final_metrics = aggregate_metrics(processed_df, employee_master, group_by)
    print(f"  ✓ Calculated metrics for {len(final_metrics)} groups\n")
    
    if return_json:
        return calculate_metrics_percentage_json(final_metrics)
    
    return final_metrics

# --- 5. Visualization / Reporting ---


def print_metrics_summary(metrics_df: pd.DataFrame):
    """
    Prints a comprehensive formatted report to the console.
    """
    divider = "=" * 100
    
    print(divider)
    print(f"{'EMPLOYEE ENGAGEMENT & WELLBEING REPORT':^100}")
    print(divider)
    
    # Per Quarter Breakdown
    if 'Quarter' in metrics_df.columns:
        for quarter in sorted(metrics_df['Quarter'].unique()):
            quarter_data = metrics_df[metrics_df['Quarter'] == quarter]
            
            print(f"\n📅 PERIOD: {quarter}")
            print("-" * 100)
            
            for _, row in quarter_data.iterrows():
                dept = row.get('Department', 'Unknown')
                print(f"🏢 {dept.upper()}")
                
                resp_count = row.get('Response_Count', 0)
                total_emp = row.get('Total_Employees', 0)
                resp_rate = row.get('Response_Rate', 0)
                engagement = row.get('Overall_Engagement', 0)
                
                print(f"   Responses: {resp_count}/{total_emp} ({resp_rate:.1f}%) | Engagement Score: {engagement:.2f}/10")
                
                if pd.notna(row.get('eNPS')):
                    print(f"   eNPS: {row['eNPS']:>5.1f}   (Promoters: {row.get('eNPS_Promoters', 0)}, "
                          f"Detractors: {row.get('eNPS_Detractors', 0)})")
                
                # Risk Indicators
                if pd.notna(row.get('Burnout_Rate')):
                    print(f"   🔥 Burnout Risk: {row['Burnout_Rate']:.1f}% (Score: {row.get('Burnout_Score', 0):.2f}/10)")
                if pd.notna(row.get('Turnover_Risk')):
                    print(f"   ⚠️  Turnover Risk: {row['Turnover_Risk']:.1f}%")
                if pd.notna(row.get('Avg_Workload')):
                    print(f"   💼 Avg Workload: {row['Avg_Workload']:.2f}")
                
                # Core metrics breakdown
                print(f"   Breakdown: [Sat: {row.get('Job_Satisfaction', 0):.1f} | "
                      f"WLB: {row.get('Work_Life_Balance', 0):.1f} | "
                      f"Mgr: {row.get('Manager_Support', 0):.1f} | "
                      f"Growth: {row.get('Growth_Opportunities', 0):.1f}]")
                print("")

    # Overall Summary
    print(divider)
    print(f"{'EXECUTIVE SUMMARY':^100}")
    print(divider)
    
    print(f"📊 Total Responses: {metrics_df['Response_Count'].sum()}")
    if 'Total_Employees' in metrics_df.columns:
        print(f"👥 Total Employees: {metrics_df['Total_Employees'].max()}")
    if 'Response_Rate' in metrics_df.columns and metrics_df['Response_Rate'].notna().any():
        print(f"📈 Overall Response Rate: {metrics_df['Response_Rate'].mean():.1f}%")
    if 'eNPS' in metrics_df.columns and metrics_df['eNPS'].notna().any():
        print(f"📈 Average eNPS: {metrics_df['eNPS'].mean():.1f}")
    if 'Burnout_Rate' in metrics_df.columns and metrics_df['Burnout_Rate'].notna().any():
        print(f"🔥 Average Burnout Rate: {metrics_df['Burnout_Rate'].mean():.1f}%")
    if 'Turnover_Risk' in metrics_df.columns and metrics_df['Turnover_Risk'].notna().any():
        print(f"⚠️  Average Turnover Risk: {metrics_df['Turnover_Risk'].mean():.1f}%")
    
    if 'Overall_Engagement' in metrics_df.columns and metrics_df['Overall_Engagement'].notna().any():
        best_row = metrics_df.loc[metrics_df['Overall_Engagement'].idxmax()]
        worst_row = metrics_df.loc[metrics_df['Overall_Engagement'].idxmin()]
        
        print(f"\n🏆 Top Performer: {best_row.get('Department', 'Unknown')} "
              f"({best_row.get('Quarter', 'N/A')}) - Engagement: {best_row['Overall_Engagement']:.2f}/10")
        print(f"⚠️  Needs Attention: {worst_row.get('Department', 'Unknown')} "
              f"({worst_row.get('Quarter', 'N/A')}) - Engagement: {worst_row['Overall_Engagement']:.2f}/10")
    
    if 'Burnout_Rate' in metrics_df.columns and metrics_df['Burnout_Rate'].notna().any():
        highest_burnout = metrics_df.loc[metrics_df['Burnout_Rate'].idxmax()]
        print(f"🔥 Highest Burnout: {highest_burnout.get('Department', 'Unknown')} "
              f"({highest_burnout.get('Quarter', 'N/A')}) - Rate: {highest_burnout['Burnout_Rate']:.1f}%")
    
    if 'Turnover_Risk' in metrics_df.columns and metrics_df['Turnover_Risk'].notna().any():
        highest_turnover = metrics_df.loc[metrics_df['Turnover_Risk'].idxmax()]
        print(f"📉 Highest Turnover Risk: {highest_turnover.get('Department', 'Unknown')} "
              f"({highest_turnover.get('Quarter', 'N/A')}) - Risk: {highest_turnover['Turnover_Risk']:.1f}%")
    
    print(divider)

# --- 6. Example Usage ---
    

if __name__ == "__main__":
    # ===== METHOD: Using Database (Recommended) =====
    print("=" * 80)
    print("Fetching data from DynamoDB")
    print("=" * 80)
    
    try:
        # Analyze data directly from database
        metrics = analyze_survey_data_from_db()
        
        # Print comprehensive report
        print_metrics_summary(metrics)
        
        # Get JSON format for API responses
        json_metrics = analyze_survey_data_from_db(return_json=True)
        print("\n📄 JSON Output (first 2 entries):")
        print(json.dumps(json_metrics[:2], indent=2))
        
        # Custom grouping example
        print("\n" + "=" * 80)
        print("Custom Grouping by Department, and Quarter")
        print("=" * 80)
        metrics_by_location = analyze_survey_data_from_db(
            group_by=['Department', 'Quarter']
        )
        print(f"\n✓ Generated {len(metrics_by_location)} metric groups")
        
    except Exception as e:
        print(f"\n❌ Error fetching from database: {str(e)}")
        print("Make sure DynamoDB tables are populated and credentials are configured.")