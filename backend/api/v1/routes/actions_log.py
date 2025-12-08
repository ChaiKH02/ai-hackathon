import os
import uuid
import boto3
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, HTTPException
from typing import Optional
from boto3.dynamodb.conditions import Attr

# Import utils
from utils.risk_engine import analyze_survey_data_from_db
from utils.quarter import get_quarter


router = APIRouter(
    prefix="/actions_log",
    tags=["Actions Log"]
)

# DynamoDB init
dynamodb = boto3.resource(
    "dynamodb",
    region_name=os.getenv("AWS_REGION")
)

table = dynamodb.Table("Actions_Log")


def generate_action_id(department, quarter):
    return f"action_{department}_{quarter}_{uuid.uuid4()}"


@router.post("/add")
async def save_activity(payload: dict):
    """
    Saves a single recommendation activity (event/action/strategy)
    + stores burnout & turnover risk snapshots
    """

    try:
        # Extract fields
        department = payload.get("department")
        quarter = payload.get("quarter")
        year = payload.get("year")
        activity_type = payload.get("activity_type")  
        description = payload.get("description")     
        impact = payload.get("impact")                
        activity_status = payload.get("activity_status", "pending")
        assigned_to = payload.get("assigned_to")
        activity_title = payload.get("activity_title")

        # ✅ Extract risk metrics (from context)
        context = payload.get("context", {})
        burnout_risk = context.get("burnout_risk_percentage")
        turnover_risk = context.get("turnover_risk_percentage")

        # Validation
        if not all([department, quarter, year, activity_type, description]):
            raise HTTPException(
                status_code=400,
                detail="Missing required fields"
            )

        # Validate activity types
        valid_types = ["events", "actions", "long_term"]
        if activity_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid activity_type. Must be one of {valid_types}"
            )

        valid_status = ["pending", "on-going", "completed"]
        if activity_status not in valid_status:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid activity_status. Must be one of {valid_status}"
            )

        # Generate ID
        action_id = generate_action_id(department, quarter)

        # Save timestamp
        saved_at = datetime.utcnow().isoformat()

        # ✅ Build DynamoDB item (with snapshot values)
        item = {
            "Action_ID": action_id,
            "Department": department,
            "Quarter": quarter,
            "Year": int(year),
            "Saved_at": saved_at,
            "Activity_status": activity_status,
            "Activity_type": activity_type,
            "Assigned_to": assigned_to,
            "Activity_title": activity_title,

            # Snapshot metrics (for later comparison)
            # Snapshot metrics (for later comparison)
            "Baseline_Burnout_Risk": Decimal(str(burnout_risk)) if burnout_risk is not None else None,
            "Baseline_Turnover_Risk": Decimal(str(turnover_risk)) if turnover_risk is not None else None,

            "Impact": impact if impact else None,
            "Description": description
        }

        # Write to DynamoDB
        table.put_item(Item=item)

        return {
            "status": "success",
            "Action_ID": action_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update/{action_id}")
async def update_activity_status(action_id: str, payload: dict):
    """
    Update activity_status using action_id
    When status becomes 'completed', calculate burnout/turnover impact
    """

    try:
        new_status = payload.get("Activity_status")

        # ✅ Fixed typo
        allowed_status = ["pending", "on-going", "completed", "cancelled"]

        if new_status not in allowed_status:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Allowed values: {allowed_status}"
            )

        # Step 1: Get existing record
        record = table.get_item(Key={"Action_ID": action_id}).get("Item")

        if not record:
            raise HTTPException(status_code=404, detail="Action not found")

        update_expr = "SET Activity_status = :s"
        expr_values = {":s": new_status}

        # ✅ Step 2: If completed → calculate impact
        if new_status == "completed":
            department = record.get("Department")
            
            # Use current time for "latest" Comparison, not the record's quarter
            now = datetime.now()
            current_year = now.year
            current_quarter = get_quarter(now.strftime("%Y-%m-%d"))

            # Baseline values saved earlier
            baseline_burnout = record.get("Baseline_Burnout_Risk")
            baseline_turnover = record.get("Baseline_Turnover_Risk")

            print(f"Calculating impact for Department: {department}, Date: {now}, Quarter: {current_quarter}, Year: {current_year}")
            
            try:
                # Fetch metrics grouped by Department, Year, Quarter (returns list of dicts)
                all_metrics = analyze_survey_data_from_db(
                    group_by=['Department', 'Year', 'Quarter'],
                    return_json=True
                )
                print(f"DEBUG: Fetched {len(all_metrics)} metrics.")
                if all_metrics:
                    print(f"DEBUG: Sample Metric Keys: {all_metrics[0].keys()}")
                    print(f"DEBUG: Sample Metric Year: {all_metrics[0].get('Year')} (Type: {type(all_metrics[0].get('Year'))})")
                    print(f"DEBUG: Sample Metric Dept: {all_metrics[0].get('Department')}")
                    print(f"DEBUG: Target: Dept={department}, Year={current_year}, Q={current_quarter}")
                else:
                    print("DEBUG: No metrics returned from analyze_survey_data_from_db")
                
                # Find the specific metric for this department, year, quarter
                latest_metric = next(
                    (item for item in all_metrics 
                     if item.get('Department') == department
                     and int(item.get('Year', 0)) == current_year 
                     and item.get('Quarter') == current_quarter),
                    None
                )
                print(f"Latest Metric: {latest_metric}")
                
                latest_burnout = None
                latest_turnover = None
                
                if latest_metric and 'Metrics' in latest_metric:
                    metrics_data = latest_metric['Metrics']
                    latest_burnout = metrics_data.get('Burnout_Rate')
                    latest_turnover = metrics_data.get('Turnover_Risk')
                
                print(f"Latest Burnout: {latest_burnout}, Latest Turnover: {latest_turnover}")
                print(f"Baseline Burnout: {baseline_burnout}, Baseline Turnover: {baseline_turnover}")

                # ✅ Calculate impact (Latest - Baseline)
                # "-" when decreased (Risk went down)
                # "+" when increased (Risk went up)
                burnout_diff = "0"
                turnover_diff = "0"

                if baseline_burnout is not None and latest_burnout is not None:
                    diff = Decimal(str(latest_burnout)) - Decimal(str(baseline_burnout))
                    if diff > 0:
                        burnout_diff = f"+{diff}"
                    elif diff < 0:
                        burnout_diff = f"{diff}"
                    else:
                        burnout_diff = "0"

                if baseline_turnover is not None and latest_turnover is not None:
                    diff = Decimal(str(latest_turnover)) - Decimal(str(baseline_turnover))
                    if diff > 0:
                        turnover_diff = f"+{diff}"
                    elif diff < 0:
                        turnover_diff = f"{diff}"
                    else:
                        turnover_diff = "0"

                # ✅ Update expressions
                update_expr += ", Completed_at = :c, Impact_Burnout = :b, Impact_Turnover = :t"
                expr_values.update({
                    ":c": now.isoformat(),
                    ":b": burnout_diff,
                    ":t": turnover_diff
                })
                
            except Exception as calc_error:
                print(f"Error calculating impact: {calc_error}")
                # Update completed_at even if impact calc fails
                update_expr += ", Completed_at = :c"
                expr_values.update({
                    ":c": now.isoformat()
                })

        # Step 3: Update DynamoDB
        response = table.update_item(
            Key={"Action_ID": action_id},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values,
            ReturnValues="UPDATED_NEW"
        )

        return {
            "status": "success",
            "action_id": action_id,
            "updated_fields": response.get("Attributes", {})
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/all")
async def get_all_actions(
    department: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None
):
    filter_expression = None

    # --- Department filter ---
    if department:
        filter_expression = Attr("Department").eq(department)

    # --- Year filter (from Saved_at: YYYY-MM-DD) ---
    if year:
        year_condition = Attr("Saved_at").begins_with(str(year))
        if filter_expression:
            filter_expression &= year_condition
        else:
            filter_expression = year_condition

    # --- Month filter (YYYY-MM-DD) ---
    if month:
        month_str = f"{month:02d}"  # 01, 02, ...
        month_condition = Attr("Saved_at").contains(f"-{month_str}-")
        if filter_expression:
            filter_expression &= month_condition
        else:
            filter_expression = month_condition

    # --- Scan with filters ---
    if filter_expression:
        response = table.scan(FilterExpression=filter_expression)
    else:
        response = table.scan()

    return response.get("Items", [])
    
