from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import graph, health, organization, person, publication, search
from app.cache.database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
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
app.include_router(graph.router, prefix="/api")
app.include_router(person.router, prefix="/api")
app.include_router(publication.router, prefix="/api")
app.include_router(organization.router, prefix="/api")
app.include_router(search.router, prefix="/api")

# Serve the compiled frontend SPA
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount(
        "/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend"
    )


@app.get("/api")
async def root():
    return {"app": "Academic Graph Explorer API", "version": "0.1.0"}
