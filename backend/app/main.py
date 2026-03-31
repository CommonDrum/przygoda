from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .auth import get_current_user
from .config import settings as app_settings, STATIC_DIR, UPLOADS_DIR, EXPORTS_DIR
from .database import init_db
from .seed import seed_demo_project
from .routers import projects, pages, settings, generation, exports, auth
from .services.ws_manager import ConnectionManager


UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_demo_project()
    manager = ConnectionManager()
    generation.set_ws_manager(manager)
    yield


app = FastAPI(title="Przygoda", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in app_settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(auth.router, prefix="/api")
app.include_router(projects.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(pages.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(settings.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(generation.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(generation.ws_router)  # WS — no /api prefix, auth via token query param
app.include_router(exports.router, prefix="/api", dependencies=[Depends(get_current_user)])
