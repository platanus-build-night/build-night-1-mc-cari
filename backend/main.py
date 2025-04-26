from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import submissions, competitions
from backend.models import CodeGenerationRequest, CodeGenerationResponse
from backend.code_generator import handle_code_generation

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(submissions.router, prefix="/api")
app.include_router(competitions.router, prefix="/api")

@app.post("/api/code_generation", response_model=CodeGenerationResponse)
async def code_generation(request: CodeGenerationRequest):
    try:
        return await handle_code_generation(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))