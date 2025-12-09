from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from api.v1.routes.upload import router as upload_router
from api.v1.routes.recommendations import router as recommendations_router
from api.v1.routes.metrics import router as metrics_router
from api.v1.routes.actions_log import router as actions_log_router
from api.v1.routes.departments import router as departments_router
from api.v1.routes.manager import router as manager_router
from api.v1.routes.season import router as season_router
from api.v1.routes.theme import router as theme_router

app = FastAPI(
    title="AI Hackathon - Employee Wellbeing API",
    description="API for analyzing employee surveys and generating AI-powered recommendations",
    version="1.0.0"
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, prefix="/api/v1")
app.include_router(recommendations_router, prefix="/api/v1")
app.include_router(metrics_router, prefix="/api/v1")
app.include_router(actions_log_router, prefix="/api/v1")
app.include_router(departments_router, prefix="/api/v1")
app.include_router(manager_router, prefix="/api/v1")
app.include_router(season_router, prefix="/api/v1")
app.include_router(theme_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "Employee Wellbeing API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/api/v1/upload",
            "recommendations": "/api/v1/recommendations",
            "metrics": "/api/v1/metrics",
            "actions_log": "/api/v1/actions_log",
            "departments": "/api/v1/departments",
            "manager": "/api/v1/manager",
            "season": "/api/v1/season",
            "theme": "/api/v1/theme",
            "docs": "/docs"
        }
    }