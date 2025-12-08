from utils.risk_engine import analyze_survey_data_from_db
from fastapi import APIRouter, Query
import json
import pandas as pd

router = APIRouter(
    prefix="/metrics",
    tags=["Metrics"]
)

from datetime import datetime

def filter_metrics(df, department: str = None, quarter: str = None, year: int = None, group_by: str = None):
    # print(df[df["Year"] == year])
    print(department)
    print(quarter)
    print(year)

    # ✅ 1. If no year → use current year
    if year is None:
        year = datetime.now().year

    if "Year" in df.columns:
        df = df[df["Year"] == year]
        
    # ✅ Handle Group By Quarter (Trend Data)
    if group_by == "quarter":
        results = []
        # Get all quarters present in the data or fixed Q1-Q4
        # tailored to the filtered dataframe
        
        # Apply department filter first if present
        if department:
            df = df[df["Department"].str.lower() == department.lower()]
            
        quarters = ["Q1", "Q2", "Q3", "Q4"]
        for q in quarters:
            # Aggregate for this quarter
            # We pass the specific quarter to aggregate_dataframe logic
            # Note: We must filter the df for each quarter agg or let aggregate_dataframe handle it?
            # aggregate_dataframe assumes we pass it a df. 
            # We should probably filter the df for the quarter first to be safe/calcuations correct.
            
            q_df = df[df["Quarter"].str.upper() == q.upper()]
            
            if q_df.empty:
                # Add empty/zero record or skip? 
                # Better to have zero-ed record for chart continuity or nulls
                # For now let's skip or handle in frontend. 
                # Let's return a basic structure so frontend doesn't crash
                res = {
                    "Department": department if department else "All",
                    "Quarter": q,
                    "Year": year,
                    "Response_Count": 0,
                    "Burnout_Rate": 0,
                    "Turnover_Risk": 0,
                    "eNPS": 0,
                    "Overall_Engagement": 0
                }
                results.append(res)
            else:
                res = aggregate_dataframe(
                    q_df,
                    department_name=department if department else "All",
                    year=year,
                    quarter=q
                )
                results.append(res)
        return results

    # ✅ 2. Apply quarter filter even when department is missing
    if quarter:
        df = df[df["Quarter"].str.upper() == quarter.upper()]
        print(df.head())

    # ✅ 3. Apply department filter when present
    if department:
        df = df[df["Department"].str.lower() == department.lower()]

        # Case A: department + quarter → detailed rows
        if quarter:
            return df.applymap(lambda x: x.item() if hasattr(x, "item") else x)\
                     .to_dict(orient="records")

        # Case B: department only → aggregate all quarters
        result = aggregate_dataframe(
            df,
            department_name=department,
            year=year,
            quarter="All"
        )
        return [result]

    # ✅ Case C: quarter only → aggregate all departments
    if quarter and not department:
        result = aggregate_dataframe(
            df,
            department_name="All",
            year=year,
            quarter=quarter
        )
        return [result]

    # ✅ Case D: no dept, no quarter → aggregate everything
    result = aggregate_dataframe(
        df,
        department_name="All",
        year=year,
        quarter="All"
    )
    return [result]




def aggregate_dataframe(df, department_name, year=None, quarter=None):
    sum_columns = [
        "Response_Count",
        "Total_Employees",
        "eNPS_Promoters",
        "eNPS_Passives",
        "eNPS_Detractors"
    ]

    mean_columns = [
        "Response_Rate",
        "Job_Satisfaction",
        "Work_Life_Balance",
        "Manager_Support",
        "Growth_Opportunities",
        "Overall_Engagement",
        "eNPS",
        "Avg_eNPS_Score",
        "Burnout_Score",
        "Burnout_Rate",
        "Turnover_Risk",
        "Avg_Workload",
        "Avg_Sentiment"
    ]

    aggregated = {}

    for col in df.columns:
        if col in sum_columns:
            aggregated[col] = int(df[col].sum())
        elif col in mean_columns:
            aggregated[col] = float(df[col].mean())
        else:
            aggregated[col] = "All"

    aggregated["Department"] = department_name
    aggregated["Quarter"] = quarter
    aggregated["Year"] = year

    return aggregated



@router.get("/")
async def get_metrics(
    departments: str | None = Query(None),
    quarter: str | None = Query(None),
    year: int | None = Query(None),
    group_by: str | None = Query(None)
):
    if year is None:
        from datetime import datetime
        year = datetime.now().year

    df = analyze_survey_data_from_db()

    filtered = filter_metrics(
        df,
        department=departments,
        quarter=quarter,
        year=year,
        group_by=group_by
    )

    return filtered

