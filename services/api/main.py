from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os
import sys
from pathlib import Path

# Add project root to Python path to allow imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load environment variables from .env file in project root
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# Also try loading from services/api/.env if it exists (for convenience)
api_env_path = Path(__file__).parent / ".env"
if api_env_path.exists():
    load_dotenv(dotenv_path=api_env_path, override=False)  # Don't override project root .env

from services.api.database import get_db, close_pool
from services.api.routers import listings, extraction, documents, images, enrichment, automation


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle events.
    Handles startup and shutdown tasks.
    """
    # Startup: Any initialization code can go here
    yield
    # Shutdown: Clean up resources
    close_pool()


app = FastAPI(title="MLS Automation API", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://localhost",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (frontend)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Root endpoint - serve frontend
@app.get("/")
async def root():
    """Serve the frontend interface."""
    static_file = Path(__file__).parent / "static" / "index.html"
    if static_file.exists():
        return FileResponse(str(static_file))
    return {"message": "Frontend not found. Please ensure static/index.html exists."}

# Include API routers with /api prefix to match frontend
app.include_router(listings.router, prefix="/api")
app.include_router(extraction.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(images.router, prefix="/api")
app.include_router(enrichment.router, prefix="/api")
app.include_router(automation.router, prefix="/api")


@app.get("/health/ready")
def readiness_check():
    """Health check endpoint that verifies database connectivity."""
    try:
        with get_db() as (conn, cur):
            cur.execute("SELECT 1")
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")
