import boto3
import pandas as pd
import math
import os
from decimal import Decimal
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize DynamoDB Resource
dynamodb = boto3.resource(
    "dynamodb",
    region_name=os.getenv("AWS_REGION"),
)

def safe_decimal(value):
    """Convert a value to Decimal, handling NaN and float types for DynamoDB"""
    if pd.isna(value) or (isinstance(value, float) and math.isnan(value)):
        return Decimal('0')
    return Decimal(str(value))

def safe_string(value):
    """Convert a value to string, handling NaN values"""
    if pd.isna(value):
        return ""
    return str(value)

def add_data(table_name, item):
    """Uploads a single item to the specified DynamoDB table"""
    try:
        table = dynamodb.Table(table_name)
        table.put_item(Item=item)
        # print(f"Added item to {table_name}") # Uncomment for verbose output
    except Exception as e:
        print(f"Error adding item to {table_name}: {e}")

# --- Upload Functions for each CSV ---

def upload_departments():
    print("Uploading Departments...")
    df = pd.read_csv('../mock/departments.csv')
    for _, row in df.iterrows():
        item = {
            'department_id': safe_string(row['department_id']),
            'department_name': safe_string(row['department_name'])
        }
        add_data('Departments', item)
    print("Departments uploaded.")

# def upload_employees():
#     print("Uploading Employees...")
#     df = pd.read_csv('../mock/employees.csv')
#     for _, row in df.iterrows():
#         item = {
#             'Employee_ID': safe_string(row['Employee_ID']),
#             'job_grade': safe_string(row['job_grade']),
#             'position': safe_string(row['position']),
#             'birthdate': safe_string(row['birthdate']),
#             'hire_date': safe_string(row['hire_date']),
#             'gender': safe_string(row['gender']),
#             'location': safe_string(row['location']),
#             'employee_level': safe_string(row['employee_level']),
#             'division': safe_string(row['division']),
#             'union_membership': safe_string(row['union_membership'])
#         }
#         add_data('Employees', item)
#     print("Employees uploaded.")

# def upload_pulse_surveys():
#     print("Uploading Pulse Survey Responses (this may take a moment)...")
#     # Assuming filename is pulse_survey_response_2025_full.csv based on previous turn
#     filename = 'survery_response_v2.csv' 
#     if not os.path.exists(filename):
#         print(f"{filename} not found, skipping.")
#         return

#     df = pd.read_csv(filename)
#     for _, row in df.iterrows():
#         item = {
#             'response_id': safe_string(row['response_id']),
#             'employee_id': safe_string(row['employee_id']),
#             'submission_date': safe_string(row['submission_date']),
#             'department': safe_string(row['department']),
#             'location': safe_string(row['location']),
#             # Add scores dynamically or explicitly
#         }
        
#         # Loop through Q1 to Q30 to add them as Decimals
#         for i in range(1, 31):
#             col_name = [col for col in df.columns if col.startswith(f"Q{i}_")][0]
#             item[col_name] = safe_decimal(row[col_name])
            
#         add_data('PulseSurveyResponses', item)
#     print("Pulse Surveys uploaded.")

# def upload_comments():
#     print("Uploading Survey Comments...")
#     df = pd.read_csv('feedbacks.csv')
#     for _, row in df.iterrows():
#         item = {
#             'comment_id': safe_string(row['comment_id']),
#             'employee_id': safe_string(row['employee_id']),
#             'comments': safe_string(row['comments'])
#         }
#         add_data('SurveyComments', item)
#     print("Comments uploaded.")
import random
def upload_workload():
    print("Uploading Employee Workload...")
    df = pd.read_csv('../mock/employee_workload.csv')
    for _, row in df.iterrows():
        item = {
            'checkin_id': safe_string(row['checkin_id']),
            'employee_id': safe_string(row['employee_id']), 
            'date': safe_string(row['date']),
            'hours_logged': safe_decimal(row['hours_logged']),
            'work_mode': random.choice(['Onsite', 'WFH'])
        }
        add_data('Employee_Workload', item)
    print("Workload uploaded.")

# --- Main Execution ---

if __name__ == "__main__":
    # Ensure all CSV files generated in previous steps are in the folder
    # upload_departments()
    # upload_employees()
    upload_workload()
    # upload_comments()
    # upload_pulse_surveys()
    print("All uploads complete!")