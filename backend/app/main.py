"""
Main FastAPI application module.

Initializes FastAPI app with middleware, routers, and configuration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import auth, users, videos, analyses


# Create FastAPI app
app = FastAPI(
    title="Hustl Analyzer API",
    description="Backend API for dance technique analysis",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(videos.router)
app.include_router(analyses.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Hustl Analyzer API",
        "version": "0.1.0",
        "docs": "/api/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
