from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
import os
import tempfile
import shutil
import pandas as pd
import uuid
import math
import decimal
from decimal import Decimal
from utils.process_data import process_csv_data
from dynamo.connection import dynamo
import boto3
import traceback

router = APIRouter(
    prefix="/upload",
    tags=["Upload"]
)

# In-memory storage for task status
# Format: {task_id: {"status": "processing"|"completed"|"failed", "message": "...", "result": {...}}}
upload_tasks = {}

def safe_decimal(value, allow_none=True):
    """
    Convert a value to Decimal, handling NaN, None, and empty values.
    
    Args:
        value: The value to convert
        allow_none: If True, returns None for null values. If False, returns Decimal('0')
        
    Returns:
        Decimal or None
    """
    # Handle None
    if value is None:
        return None if allow_none else Decimal('0')
    
    # Handle pandas NaN
    if pd.isna(value):
        return None if allow_none else Decimal('0')
    
    # Handle empty strings
    if isinstance(value, str) and value.strip() == '':
        return None if allow_none else Decimal('0')
    
    # Handle float NaN
    if isinstance(value, float) and math.isnan(value):
        return None if allow_none else Decimal('0')
    
    # Try to convert to Decimal
    try:
        return Decimal(str(value))
    except (ValueError, TypeError, decimal.InvalidOperation):
        # If conversion fails, return None or 0
        return None if allow_none else Decimal('0')

def safe_string(value):
    """Convert a value to string, handling NaN values"""
    if pd.isna(value):
        return ""
    return str(value)

def add_to_dynamodb(table_name, item):
    """Add a single item to DynamoDB table"""
    dynamodb = boto3.resource(
        "dynamodb",
        region_name=os.getenv("AWS_REGION")
    )
    table = dynamodb.Table(table_name)
    table.put_item(Item=item)

def get_partial_data_from_dynamodb(table_name, limit=10):
    """Retrieve partial data from DynamoDB table"""
    dynamodb = boto3.resource(
        "dynamodb",
        region_name=os.getenv("AWS_REGION")
    )
    table = dynamodb.Table(table_name)
    response = table.scan(Limit=limit)
    return response.get("Items", [])

def process_file_background(task_id: str, file_path: str, original_filename: str):
    """
    Background task to process the CSV file.
    """
    try:
        upload_tasks[task_id]["status"] = "processing"
        upload_tasks[task_id]["message"] = "Reading file and initializing NLP pipeline..."
        
        # Read the uploaded CSV to get total row count
        print(f"Reading uploaded file: {original_filename}")
        df_input = pd.read_csv(file_path)
        total_uploaded_rows = len(df_input)
        print(f"Processing all {total_uploaded_rows} rows")
        
        # Process the CSV file through the NLP pipeline
        output_path = file_path.replace("input.csv", "processed_output.csv")
        
        upload_tasks[task_id]["message"] = "Running AI analysis on survey responses... (This may take a few minutes)"
        process_csv_data(file_path, output_path)
        
        # Read the processed data
        df = pd.read_csv(output_path)
        total_rows = len(df)
        
        # Save all processed data to DynamoDB
        upload_tasks[task_id]["message"] = f"Saving {total_rows} records to database..."
        print(f"Saving {total_rows} rows to DynamoDB...")
        saved_count = 0
        
        for index, row in df.iterrows():
            try:
                # Q1-Q5 can be None for open-text feedback
                # Sentiment is required for all records
                item = {
                    "Response_ID": str(uuid.uuid4()),
                    "Employee_ID": safe_string(row.get("Employee_ID", "")),
                    "Quarter": safe_string(row.get("Quarter", "")),
                    "Submission_Date": safe_string(row.get("Submission_Date", "")),
                    "Department": safe_string(row.get("Department", "")),
                    "Q1_Job_Satisfaction": safe_decimal(row.get("Q1_Job_Satisfaction"), allow_none=True),
                    "Q2_Work_Life_Balance": safe_decimal(row.get("Q2_Work_Life_Balance"), allow_none=True),
                    "Q3_Manager_Support": safe_decimal(row.get("Q3_Manager_Support"), allow_none=True),
                    "Q4_Growth_Opportunities": safe_decimal(row.get("Q4_Growth_Opportunities"), allow_none=True),
                    "Q5_eNPS": safe_decimal(row.get("Q5_eNPS"), allow_none=True),
                    "Raw_Comment": safe_string(row.get("Comments", "")),
                    "Event_Season": safe_string(row.get("Event_Season", "")),
                    "Rephrased_Comment": safe_string(row.get("Rephrased_Comment", "")),
                    "Categories": safe_string(row.get("Categories", "")),
                    "Sentiment_Score": safe_decimal(row.get("Sentiment_Score", 5), allow_none=False),
                    "Sentiment_Label": safe_string(row.get("Sentiment_Label", "neutral"))
                }
                
                add_to_dynamodb("Survey_Response", item)
                saved_count += 1
                # Optional: Update progress for every N items if needed, but simple message is usually fine
                
            except Exception as e:
                print(f"\nError saving row {index}: {str(e)}")
                continue
        
        print(f"\n✓ Successfully saved {saved_count} rows to DynamoDB")
        
        # Retrieve partial data from DynamoDB (first 10 rows)
        partial_data = get_partial_data_from_dynamodb("Survey_Response", limit=10)
        
        # Convert Decimal to float for JSON serialization
        def decimal_to_float(obj):
            if isinstance(obj, list):
                return [decimal_to_float(item) for item in obj]
            elif isinstance(obj, dict):
                return {key: decimal_to_float(value) for key, value in obj.items()}
            elif isinstance(obj, Decimal):
                return float(obj)
            return obj
        
        partial_data = decimal_to_float(partial_data)
        
        # Calculate survey vs open-text feedback statistics
        survey_cols = ['Q1_Job_Satisfaction', 'Q2_Work_Life_Balance', 
                       'Q3_Manager_Support', 'Q4_Growth_Opportunities', 'Q5_eNPS']
        
        def has_survey_scores(row):
            """Check if row has at least one valid Q1-Q5 value"""
            for col in survey_cols:
                if col in df.columns:
                    val = row.get(col)
                    if pd.notna(val) and val != 0:
                        return True
            return False
        
        # Count survey responses vs open-text only
        survey_response_count = sum(df.apply(has_survey_scores, axis=1))
        open_text_only_count = total_rows - survey_response_count
        
        result = {
            "status": "success",
            "filename": original_filename,
            "total_rows_uploaded": total_uploaded_rows,
            "total_rows_processed": total_rows,
            "total_rows_saved_to_db": saved_count,
            "database_table": "Survey_Response",
            "returned_rows_count": len(partial_data),
            "statistics": {
                # Response breakdown
                "survey_responses_count": survey_response_count,
                "open_text_feedback_count": open_text_only_count,
                
                # Comment analysis (all records)
                "total_comments_processed": int(df['Comments'].notna().sum()) if 'Comments' in df.columns else 0,
                "average_sentiment_score": float(df['Sentiment_Score'].mean()) if 'Sentiment_Score' in df.columns else None,
                "sentiment_distribution": df['Sentiment_Label'].value_counts().to_dict() if 'Sentiment_Label' in df.columns else {},
                "unique_categories": int(df['Categories'].nunique()) if 'Categories' in df.columns else 0,
                
                # Other metadata
                "unique_quarters": df['Quarter'].unique().tolist() if 'Quarter' in df.columns else []
            },
            "sample_data_from_database": partial_data
        }
        
        upload_tasks[task_id]["status"] = "completed"
        upload_tasks[task_id]["message"] = "Processing complete!"
        upload_tasks[task_id]["result"] = result
        
    except Exception as e:
        print(f"Error in background processing: {e}")
        traceback.print_exc()
        upload_tasks[task_id]["status"] = "failed"
        upload_tasks[task_id]["message"] = f"Error: {str(e)}"
    finally:
        # Clean up temporary files
        temp_dir = os.path.dirname(file_path)
        shutil.rmtree(temp_dir, ignore_errors=True)

@router.post("/csv")
async def upload_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Initiate background CSV upload and processing.
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only CSV files are accepted."
        )
    
    # Create temporary directory for processing
    temp_dir = tempfile.mkdtemp()
    input_path = os.path.join(temp_dir, "input.csv")
    
    try:
        # Save uploaded file to temporary location
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        task_id = str(uuid.uuid4())
        upload_tasks[task_id] = {
            "status": "pending",
            "message": "File uploaded, starting processing...",
            "result": None
        }
        
        background_tasks.add_task(process_file_background, task_id, input_path, file.filename)
        
        return {"task_id": task_id, "message": "Upload started. Check status with /status/{task_id}"}
        
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{task_id}")
async def get_upload_status(task_id: str):
    """
    Get the status of a background upload task.
    """
    if task_id not in upload_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return upload_tasks[task_id]
