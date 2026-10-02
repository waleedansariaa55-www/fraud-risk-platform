import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.database import Base, engine
from app.routers import auth_router, admin_router, transaction_router

# Create tables (for demo/dev; use Alembic migrations in real production)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Fraud & Risk Detection Platform API",
    description="Authentication, user/role management, and transaction management "
                "for an AI-powered fraud & risk detection platform.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(admin_router.router)
app.include_router(transaction_router.router)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


@app.get("/", tags=["Health"])
def root():
    """Serves the console UI if present, otherwise a simple API status message."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "status": "ok",
        "service": "Fraud & Risk Detection Platform API",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}
