"""
API endpoints for AI-powered recommendations
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel, Field
import sys
import os

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../utils'))

from recommendation_agent import (
    generate_recommendations_with_llama
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


# ==================== Request/Response Models ====================

class RecommendationRequest(BaseModel):
    """Request model for generating recommendations"""
    department: str = Field(..., description="Department name")
    quarter: Optional[str] = Field(None, description="Quarter (e.g., 'Q1', 'Q2', 'Q3', 'Q4')")
    year: Optional[int] = Field(None, description="Year (e.g., 2024)")
    focus_areas: Optional[List[str]] = Field(
        None, 
        description="Specific areas to focus on (e.g., ['burnout', 'turnover', 'engagement'])"
    )

# ==================== API Endpoints ====================

@router.post("/generate")
async def generate_recommendations(request: RecommendationRequest):
    """
    Generate AI-powered recommendations for a specific department.

    This endpoint uses Llama 3.2 to analyze survey data, employee metrics, and workload
    to provide actionable recommendations for reducing burnout, turnover, and other risks.

    **Parameters:**
    - **department**: Department name (required)
    - **quarter**: Quarter filter (optional, e.g., 'Q1', 'Q2')
    - **year**: Year filter (optional, e.g., 2024)
    - **focus_areas**: Specific areas to focus on (optional, e.g., ['burnout', 'turnover'])

    **Returns:**
    - Clean recommendations including:
        - Priority actions with rationale and timeline
        - Recommended events/programs
        - Long-term strategies
    """
    try:
        recommendations = generate_recommendations_with_llama(
            department=request.department,
            quarter=request.quarter,
            year=request.year,
            focus_areas=request.focus_areas
        )

        if "error" in recommendations:
            raise HTTPException(status_code=404, detail=recommendations["error"])

        # Build cleaner response
        clean_response = {
            "status": "success",
            "data": {
                "department": recommendations.get("department"),
                "quarter": recommendations.get("quarter"),
                "year": recommendations.get("year"),
                "generated_at": recommendations.get("generated_at"),
                "burnout_risk_percentage": recommendations.get("context", {}).get("burnout_risk_percentage", 0.0),
                "turnover_risk_percentage": recommendations.get("context", {}).get("turnover_risk_percentage", 0.0),
                "recommendations": {
                    "priority_actions": recommendations.get("recommendations", {}).get("priority_actions", []),
                    "recommended_events": recommendations.get("recommendations", {}).get("recommended_events", []),
                    "long_term_strategies": recommendations.get("recommendations", {}).get("long_term_strategies", [])
                }
            }
        }

        return clean_response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {str(e)}")