"""
CAVIA Backend API - Main Application
"""

import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add shared package to path
sys.path.insert(0, "/shared")

from cavia_common import setup_logging, get_logger

from routers import cv_router, jobs_router, agents_router, queues_router, workflows_router

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="CAVIA API",
    description="CV Assessment via Intelligent Agents - Backend API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(cv_router.router, prefix="/api/v1", tags=["CVs"])
app.include_router(jobs_router.router, prefix="/api/v1", tags=["Jobs"])
app.include_router(agents_router.router, prefix="/api/v1", tags=["Agents"])
app.include_router(queues_router.router, prefix="/api/v1", tags=["Queues"])
app.include_router(workflows_router.router, prefix="/api/v1", tags=["Workflows"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "cavia-api",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "CAVIA API",
        "version": "1.0.0",
        "description": "CV Assessment via Intelligent Agents",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
