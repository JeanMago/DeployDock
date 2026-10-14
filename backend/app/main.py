import os
import shutil

# Auto-detect git executable if not in system PATH
if not shutil.which("git"):
    candidates = [
        "C:\\Program Files\\Git\\cmd\\git.exe",
        "C:\\Program Files (x86)\\Git\\cmd\\git.exe",
    ]
    gh_desktop = os.path.expanduser("~\\AppData\\Local\\GitHubDesktop")
    if os.path.exists(gh_desktop):
        for entry in sorted(os.listdir(gh_desktop), reverse=True):
            candidate = os.path.join(gh_desktop, entry, "resources", "app", "git", "cmd", "git.exe")
            if os.path.isfile(candidate):
                candidates.insert(0, candidate)

    for c in candidates:
        if os.path.isfile(c):
            os.environ["GIT_PYTHON_GIT_EXECUTABLE"] = c
            git_dir = os.path.dirname(c)
            if git_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = git_dir + os.pathsep + os.environ.get("PATH", "")
            break

os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.db.session import init_db, engine
from app.api.v1.router import api_router

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await engine.dispose()

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"app": settings.APP_NAME, "version": "1.0.0"}
