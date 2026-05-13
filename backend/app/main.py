from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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

# API routes
app.include_router(health.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(person.router, prefix="/api")
app.include_router(publication.router, prefix="/api")
app.include_router(organization.router, prefix="/api")
app.include_router(search.router, prefix="/api")


@app.get("/api")
async def root():
    return {"app": "Academic Graph Explorer API", "version": "0.1.0"}


# Serve the compiled frontend SPA
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if frontend_dist.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=frontend_dist / "assets"),
        name="assets",
    )

    @app.get("/{path:path}")
    async def frontend(path: str):
        requested_file = frontend_dist / path

        if requested_file.is_file():
            return FileResponse(requested_file)

        return FileResponse(frontend_dist / "index.html")
