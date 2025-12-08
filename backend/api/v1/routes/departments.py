from fastapi import APIRouter
import boto3
import os 
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(
    prefix="/departments",
    tags=["Departments"]
)

# Initialize boto3 resource
dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION'))
table = dynamodb.Table('Departments')

# Get all departments
@router.get('/')
def get_departments():
    response = table.scan()
    return response.get('Items', [])
