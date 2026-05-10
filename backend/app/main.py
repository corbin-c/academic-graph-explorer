from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import create_db_and_tables
from app.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    await create_db_and_tables()
    yield


app = FastAPI(
    title="Academic Graph Explorer API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — permissive for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(health.router, prefix="/api")

# Serve the compiled frontend SPA
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount(
        "/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend"
    )


@app.get("/api")
async def root():
    return {"app": "Academic Graph Explorer API", "version": "0.1.0"}
