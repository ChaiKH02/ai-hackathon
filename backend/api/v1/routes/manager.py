import boto3
import os
from fastapi import APIRouter, Query
from boto3.dynamodb.conditions import Attr, Key
from fastapi import HTTPException

router = APIRouter(
    prefix="/manager",
    tags=["manager"]
)

# DynamoDB init
dynamodb = boto3.resource(
    "dynamodb",
    region_name=os.getenv("AWS_REGION")
)
table = dynamodb.Table("Employees")

@router.get("/")
def get_managers(
    department: str = Query(..., description="Department name to filter by")
):
    """
    Get all active managers for a specific department.
    """
    try:
        response = table.scan(
            FilterExpression=Attr("Role").eq("Manager") & 
                           Attr("Department").eq(department) & 
                           Attr("Is_Active").eq(True)
        )
        return response.get("Items", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))