from decimal import Decimal
import boto3
import pandas as pd
import math
import uuid
import os
from dotenv import load_dotenv
load_dotenv()
def safe_decimal(value):
    """Convert a value to Decimal, handling NaN and float types"""
    if pd.isna(value) or (isinstance(value, float) and math.isnan(value)):
        return Decimal('0')
    return Decimal(str(value))

def safe_string(value):
    """Convert a value to string, handling NaN values"""
    if pd.isna(value):
        return ""
    return str(value)

def add_data(table_name, item):
    table = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION")).Table(table_name)
    table.put_item(
        Item=item
    )

# add department
add_data("Departments", {"Department_ID": "1", "Department_Name": "Marketing"})
add_data("Departments", {"Department_ID": "2", "Department_Name": "Sales"})
add_data("Departments", {"Department_ID": "3", "Department_Name": "HR"})
add_data("Departments", {"Department_ID": "4", "Department_Name": "IT"})
add_data("Departments", {"Department_ID": "5", "Department_Name": "Finance"})
add_data("Departments", {"Department_ID": "6", "Department_Name": "Product"})


# # table employees
# employee_df = pd.read_csv("../mock/employees.csv")
# for index, row in employee_df.iterrows():
#     add_data("Employees", {"Employee_ID": row["Employee_ID"], "Name": row["Name"], "Department": row["Department"], "Role": row["Role"], "Hire_Date": row["Hire_Date"], "Is_Active": row["Is_Active"]})

# print("Employees added")

# employee_workload_df = pd.read_csv("../mock/Employee_Workload.csv")
# employee table
# Employee_ID,Name,Department,Role,Hire_Date,Is_Active
# processed survey response table
# Workload_ID,Employee_ID,Date,Hours_Logged
# processed survey table
# Response_ID	Quarter	Submission_Date	Department	Q1_Job_Satisfaction	Q2_Work_Life_Balance	Q3_Manager_Support	Q4_Growth_Opportunities	Q5_eNPS	Comments	Event_Season	Quarter	Rephrased_Comment	Categories	Sentiment_Score
# survey_response_df = pd.read_csv("../mock/processed_survey_response.csv", delimiter="\t")
# employee_df = pd.read_csv("../mock/Employees.csv")


# for index, row in employee_workload_df.iterrows():
#     add_data("Employee_Workload", {"Workload_ID": row["Workload_ID"], "Employee_ID": row["Employee_ID"], "Date": row["Date"], "Hours_Logged": safe_decimal(row["Hours_Logged"])})

# for index, row in employee_df.iterrows():
#     add_data("Employees", {"Employee_ID": row["Employee_ID"], "Department": row["Department"], "Hire_Date": row["Hire_Date"], "Is_Active": row["Is_Active"]})

# for index, row in survey_response_df.iterrows():
#     add_data("Processed_Survey_Response", {
#         "Response_ID": str(uuid.uuid4()), 
#         "Quarter": row["Quarter"], 
#         "Submission_Date": row["Submission_Date"], 
#         "Department": row["Department"], 
#         "Q1_Job_Satisfaction": safe_decimal(row["Q1_Job_Satisfaction"]), 
#         "Q2_Work_Life_Balance": safe_decimal(row["Q2_Work_Life_Balance"]), 
#         "Q3_Manager_Support": safe_decimal(row["Q3_Manager_Support"]), 
#         "Q4_Growth_Opportunities": safe_decimal(row["Q4_Growth_Opportunities"]), 
#         "Q5_eNPS": safe_decimal(row["Q5_eNPS"]), 
#         "Raw_Comment": safe_string(row["Comments"]), 
#         "Event_Season": safe_string(row["Event_Season"]), 
#         "Rephrased_Comment": safe_string(row["Rephrased_Comment"]), 
#         "Categories": safe_string(row["Categories"]), 
#         "Sentiment_Score": safe_decimal(row["Sentiment_Score"])
#     })


# table = dynamodb.Table("Processed_Survey_Response")
# print(table.scan().get("Items")[:10])