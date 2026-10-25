from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import logging
import os

from .config import DEV_SECRET, settings
from .database import Base, SessionLocal, engine
from .routers import agents, auth, favorites, misc, mortgage, neighborhoods, properties
from .seed import seed

# Optional: set FRONTEND_DIST to the frontend's built `dist` folder to serve the site from this API too.
_dist_env = os.getenv("FRONTEND_DIST", "").strip()
DIST = Path(_dist_env).expanduser().resolve() if _dist_env else None


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.secret_key == DEV_SECRET:
        logging.getLogger("uvicorn.error").warning("Using the insecure development SECRET_KEY. Set SECRET_KEY in production.")
    Base.metadata.create_all(engine)
    if settings.seed_on_startup:
        with SessionLocal() as db:
            seed(db)
    yield


app = FastAPI(title="HomeFind API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,          # JWT travels in the Authorization header, not cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (misc.router, auth.router, properties.router, favorites.router,
          agents.router, neighborhoods.router, mortgage.router):
    app.include_router(r, prefix="/api")


# Serve the built React app from the same process (only when FRONTEND_DIST is set).
if DIST and DIST.is_dir():
    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not found")
        target = (DIST / path).resolve()
        if path and target.is_file() and DIST.resolve() in target.parents:
            return FileResponse(target)
        return FileResponse(DIST / "index.html")
