from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
import time
import uuid
from dotenv import load_dotenv

from database import init_db
from routers import auth, stories, reading, teacher, parent, admin, notifications, export, gamification, assignments, charts, messages, agenda
import migration_script
from logging_config import setup_logging, get_logger

# Load environment variables
load_dotenv()

# Setup logging first
setup_logging(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Okuma Geliştirme Uygulaması",
    description="Reading Development Web Application API",
    version="1.0.0"
)

# CORS Configuration with explicit setup
from starlette.middleware.cors import CORSMiddleware as StarletteCORS

allowed_origins = [
    "https://okuma-frontend.onrender.com",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000"
]

logger.info(f"Adding CORS for origins: {allowed_origins}")

# Use Starlette's CORS middleware correctly
app.add_middleware(
    StarletteCORS,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    # Log request
    logger.info(f"[{request_id}] {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        logger.info(f"[{request_id}] Completed {response.status_code} in {duration:.3f}s")
        return response
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[{request_id}] Error after {duration:.3f}s: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

# Mount static files
os.makedirs("static/uploads/images", exist_ok=True)
os.makedirs("static/uploads/audio", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(auth.router)
app.include_router(stories.router)
app.include_router(reading.router)
app.include_router(teacher.router)
app.include_router(parent.router)
app.include_router(admin.router)
app.include_router(notifications.router)
app.include_router(export.router)
app.include_router(gamification.router)
app.include_router(assignments.router)
app.include_router(charts.router)
app.include_router(messages.router)
app.include_router(agenda.router)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("Starting application...")
    init_db()
    try:
        migration_script.run_migration()
        logger.info("Migration executed successfully")
    except Exception as e:
        logger.warning(f"Migration failed: {e}")
        
    logger.info("Database initialized successfully")
    logger.info("Application started")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Okuma Geliştirme Uygulaması API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/ready")
async def ready_check():
    """Readiness check endpoint"""
    from database import get_db
    try:
        db = next(get_db())
        db.execute("SELECT 1")
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "disconnected"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

