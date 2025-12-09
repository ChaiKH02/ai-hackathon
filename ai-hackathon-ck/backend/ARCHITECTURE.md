# Recommendation Agent - System Architecture

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACE                               │
│                                                                       │
│  ┌─────────────────┐              ┌──────────────────┐              │
│  │   REST API      │              │  Python Scripts  │              │
│  │   (FastAPI)     │              │  (Direct Calls)  │              │
│  └────────┬────────┘              └────────┬─────────┘              │
│           │                                 │                         │
└───────────┼─────────────────────────────────┼─────────────────────────┘
            │                                 │
            └─────────────┬───────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    RECOMMENDATION AGENT                               │
│                  (recommendation_agent.py)                            │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  1. DATA RETRIEVAL LAYER                                   │     │
│  │                                                             │     │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────┐ │     │
│  │  │ Survey Responses │  │    Employees     │  │ Workload │ │     │
│  │  │   from DynamoDB  │  │  from DynamoDB   │  │from DB   │ │     │
│  │  └──────────────────┘  └──────────────────┘  └──────────┘ │     │
│  └────────────────────────────────────────────────────────────┘     │
│                          │                                           │
│                          ▼                                           │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  2. FILTERING & ANALYSIS LAYER                             │     │
│  │                                                             │     │
│  │  • Filter by: Department, Quarter, Year                    │     │
│  │  • Identify: Bad Sentiment (≤5.0)                          │     │
│  │  • Identify: Bad Scores (≤5.0)                             │     │
│  │  • Calculate: Burnout Risk %                               │     │
│  │  • Calculate: Turnover Risk %                              │     │
│  │  • Extract: Common Categories                              │     │
│  └────────────────────────────────────────────────────────────┘     │
│                          │                                           │
│                          ▼                                           │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  3. CONTEXT ENRICHMENT LAYER                               │     │
│  │                                                             │     │
│  │  • Aggregate: Employee Data by Department                  │     │
│  │  • Aggregate: Workload Data by Department                  │     │
│  │  • Combine: Survey + Employee + Workload                   │     │
│  │  • Extract: Sample Bad Comments                            │     │
│  │  • Calculate: Average Metrics                              │     │
│  └────────────────────────────────────────────────────────────┘     │
│                          │                                           │
│                          ▼                                           │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  4. AI RECOMMENDATION ENGINE                               │     │
│  │                                                             │     │
│  │  • Build: Comprehensive Prompt                             │     │
│  │  • Include: Context, Metrics, Comments                     │     │
│  │  • Send to: Llama 3.2 (via Ollama)                         │     │
│  │  • Parse: JSON Response                                    │     │
│  └────────────────────────────────────────────────────────────┘     │
└───────────────────────────┬──────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      LLAMA 3.2 (Ollama)                               │
│                                                                       │
│  Analyzes context and generates:                                     │
│  • Priority Actions (with rationale & timeline)                      │
│  • Recommended Events/Programs                                       │
│  • Long-term Strategies                                              │
│  • Metrics to Track                                                  │
└───────────────────────────┬──────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    STRUCTURED RECOMMENDATIONS                         │
│                                                                       │
│  {                                                                    │
│    "department": "Engineering",                                       │
│    "context": { ... },                                                │
│    "recommendations": {                                               │
│      "priority_actions": [...],                                       │
│      "recommended_events": [...],                                     │
│      "long_term_strategies": [...],                                   │
│      "metrics_to_track": [...]                                        │
│    }                                                                  │
│  }                                                                    │
└──────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
┌─────────┐
│  User   │
└────┬────┘
     │
     │ 1. Request Recommendations
     │    (Department: Engineering, Quarter: Q4, Year: 2024)
     │
     ▼
┌────────────────────┐
│   API Endpoint     │
│   /generate        │
└────────┬───────────┘
         │
         │ 2. Call Agent Function
         │
         ▼
┌──────────────────────────────────────────────────────────┐
│  get_enriched_context_for_recommendations()              │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Step 2a: Fetch Survey Data                      │    │
│  │ ┌─────────────────────────────────────────┐     │    │
│  │ │ DynamoDB: Survey_Response               │     │    │
│  │ │ Filter: Department = "Engineering"      │     │    │
│  │ │         Quarter = "Q4"                  │     │    │
│  │ │         Year = 2024                     │     │    │
│  │ └─────────────────────────────────────────┘     │    │
│  │ Result: 45 survey responses                     │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Step 2b: Identify Bad Responses                 │    │
│  │ • Sentiment Score ≤ 5.0: 12 responses           │    │
│  │ • Job Satisfaction ≤ 5.0: 8 responses           │    │
│  │ • Work-Life Balance ≤ 5.0: 16 responses         │    │
│  │ • Total with bad scores: 20 responses           │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Step 2c: Calculate Risk Metrics                 │    │
│  │ • Burnout Risk: 35.5% (16/45)                   │    │
│  │ • Turnover Risk: 28.3% (13/45)                  │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Step 2d: Fetch Employee Data                    │    │
│  │ ┌─────────────────────────────────────────┐     │    │
│  │ │ DynamoDB: Employees                     │     │    │
│  │ │ Filter: Department = "Engineering"      │     │    │
│  │ └─────────────────────────────────────────┘     │    │
│  │ Result: 50 employees                            │    │
│  │ Avg Tenure: 3.2 years                           │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Step 2e: Fetch Workload Data                    │    │
│  │ ┌─────────────────────────────────────────┐     │    │
│  │ │ DynamoDB: Employee_Workload             │     │    │
│  │ │ Join with Employees on Employee_ID      │     │    │
│  │ │ Filter: Department = "Engineering"      │     │    │
│  │ └─────────────────────────────────────────┘     │    │
│  │ Result: Avg Workload = 48.5 hours/week          │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Step 2f: Extract Context                        │    │
│  │ • Common Bad Categories: ["workload",           │    │
│  │   "management", "career_growth"]                │    │
│  │ • Sample Bad Comments: [                        │    │
│  │   "Too much work, not enough time",             │    │
│  │   "Need better support from management"         │    │
│  │ ]                                                │    │
│  └─────────────────────────────────────────────────┘    │
└───────────────────────┬───────────────────────────────────┘
                        │
                        │ 3. Enriched Context
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│  generate_recommendations_with_llama()                   │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Step 3a: Build Prompt                           │    │
│  │                                                  │    │
│  │ "You are an expert HR consultant...             │    │
│  │                                                  │    │
│  │ Department: Engineering                          │    │
│  │ Total Employees: 50                              │    │
│  │ Burnout Risk: 35.5%                              │    │
│  │ Turnover Risk: 28.3%                             │    │
│  │ Avg Job Satisfaction: 6.2/10                     │    │
│  │ Avg Work-Life Balance: 5.8/10                    │    │
│  │ Avg Workload: 48.5 hours/week                    │    │
│  │                                                  │    │
│  │ Common Issues: workload, management              │    │
│  │                                                  │    │
│  │ Sample Comments:                                 │    │
│  │ - Too much work, not enough time                 │    │
│  │ - Need better support from management            │    │
│  │                                                  │    │
│  │ Provide recommendations in JSON format..."       │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Step 3b: Send to Llama 3.2                      │    │
│  │ ┌─────────────────────────────────────────┐     │    │
│  │ │ Ollama API (localhost:11434)            │     │    │
│  │ │ Model: llama3.2                         │     │    │
│  │ │ Temperature: 0.7                        │     │    │
│  │ │ Max Tokens: 2000                        │     │    │
│  │ └─────────────────────────────────────────┘     │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Step 3c: Parse JSON Response                    │    │
│  │ {                                                │    │
│  │   "priority_actions": [                          │    │
│  │     {                                            │    │
│  │       "action": "Implement flexible hours",      │    │
│  │       "rationale": "35.5% burnout risk...",      │    │
│  │       "timeline": "Immediate"                    │    │
│  │     }                                            │    │
│  │   ],                                             │    │
│  │   "recommended_events": [...],                   │    │
│  │   "long_term_strategies": [...],                 │    │
│  │   "metrics_to_track": [...]                      │    │
│  │ }                                                │    │
│  └─────────────────────────────────────────────────┘    │
└───────────────────────┬───────────────────────────────────┘
                        │
                        │ 4. Structured Recommendations
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│  API Response                                             │
│                                                           │
│  {                                                        │
│    "status": "success",                                   │
│    "data": {                                              │
│      "department": "Engineering",                         │
│      "context": { ... },                                  │
│      "recommendations": { ... }                           │
│    }                                                      │
│  }                                                        │
└───────────────────────┬───────────────────────────────────┘
                        │
                        │ 5. Return to User
                        │
                        ▼
                   ┌─────────┐
                   │  User   │
                   └─────────┘
```

## Component Interaction

```
┌─────────────────────────────────────────────────────────────────┐
│                         COMPONENTS                               │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│   FastAPI App    │  • Routes HTTP requests
│   (main.py)      │  • Handles authentication (future)
└────────┬─────────┘  • Returns JSON responses
         │
         │ includes
         ▼
┌──────────────────────────────────┐
│  Recommendations Router          │  • POST /generate
│  (recommendations.py)            │  • POST /generate-multi
└────────┬─────────────────────────┘  • GET /risk-summary/{dept}
         │                             • GET /context/{dept}
         │ calls
         ▼
┌──────────────────────────────────────────────────────────┐
│  Recommendation Agent                                     │
│  (recommendation_agent.py)                                │
│                                                           │
│  Functions:                                               │
│  • get_survey_responses_by_filters()                     │
│  • get_risk_summary_by_department()                      │
│  • get_enriched_context_for_recommendations()            │
│  • generate_recommendations_with_llama()                 │
│  • generate_multi_department_recommendations()           │
└────────┬──────────────────────────────────────────────────┘
         │
         │ uses
         ▼
┌──────────────────────────────────┐
│  Risk Engine                     │  • fetch_employees_from_db()
│  (risk_engine.py)                │  • fetch_workload_from_db()
└────────┬─────────────────────────┘  • fetch_survey_from_db()
         │
         │ queries
         ▼
┌──────────────────────────────────┐
│  DynamoDB Tables                 │  • Survey_Response
│  (AWS)                           │  • Employees
└──────────────────────────────────┘  • Employee_Workload

         ┌─────────────────────────┐
         │  Ollama (Llama 3.2)     │  • localhost:11434
         │  (Local AI Service)     │  • Generates recommendations
         └─────────────────────────┘
```

## Request/Response Flow

```
HTTP POST /api/v1/recommendations/generate
{
  "department": "Engineering",
  "quarter": "Q4",
  "year": 2024,
  "focus_areas": ["burnout"]
}
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│ 1. Validate Request                                     │
│    ✓ Department exists                                  │
│    ✓ Quarter format valid                               │
│    ✓ Year is reasonable                                 │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Fetch Survey Data                                    │
│    Query: Survey_Response                               │
│    Filter: Department="Engineering", Quarter="Q4 2024"  │
│    Result: 45 responses                                 │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Analyze Responses                                    │
│    • Bad sentiment: 12 responses                        │
│    • Bad scores: 20 responses                           │
│    • Burnout risk: 35.5%                                │
│    • Turnover risk: 28.3%                               │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Enrich Context                                       │
│    • Fetch employee data: 50 employees                  │
│    • Fetch workload data: avg 48.5 hrs/week             │
│    • Extract categories: ["workload", "management"]     │
│    • Sample comments: 5 examples                        │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Generate AI Recommendations                          │
│    • Build comprehensive prompt                         │
│    • Call Llama 3.2 via Ollama                          │
│    • Parse JSON response                                │
│    • Validate structure                                 │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│ 6. Return Response                                      │
│    {                                                     │
│      "status": "success",                                │
│      "data": {                                           │
│        "department": "Engineering",                      │
│        "context": { ... },                               │
│        "recommendations": {                              │
│          "priority_actions": [...],                      │
│          "recommended_events": [...],                    │
│          "long_term_strategies": [...],                  │
│          "metrics_to_track": [...]                       │
│        }                                                 │
│      }                                                   │
│    }                                                     │
└─────────────────────────────────────────────────────────┘
```

## File Structure

```
backend/
├── main.py                          # FastAPI application
├── api/
│   └── v1/
│       └── routes/
│           ├── recommendations.py   # Recommendation API endpoints
│           └── upload.py            # Survey upload endpoint
├── utils/
│   ├── recommendation_agent.py     # Main recommendation agent
│   ├── risk_engine.py              # Risk calculation & DB queries
│   ├── nlp_engine.py               # NLP processing
│   └── process_data.py             # Data processing utilities
├── test_recommendation_agent.py    # Test suite
├── RECOMMENDATION_AGENT_README.md  # Full documentation
├── QUICK_START.md                  # Quick reference guide
└── IMPLEMENTATION_SUMMARY.md       # Implementation overview
```
