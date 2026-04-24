import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .auth import get_current_user
from .config import settings as app_settings, STATIC_DIR, UPLOADS_DIR, EXPORTS_DIR
from .database import init_db
from .errors import classify_error
from .seed import seed_demo_project
from .routers import projects, pages, settings, generation, exports, auth, prompts, providers
from .services.ws_manager import ConnectionManager

logger = logging.getLogger(__name__)


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


# --- Global error envelope ---
# Every exception that reaches the HTTP layer becomes
# `{code, detail, title, hint, retryable}` so the frontend can show the user a
# friendly message (and decide whether to offer a retry button) without caring
# about SDK-specific exception types.

@app.exception_handler(FastAPIHTTPException)
async def _http_exception_handler(request: Request, exc: FastAPIHTTPException):
    # HTTPExceptions raised explicitly by routers keep their status, but we
    # still normalize the body shape so the frontend can branch on `code`.
    detail = exc.detail if isinstance(exc.detail, str) else "Błąd"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": "HTTP_" + str(exc.status_code),
            "detail": detail,
            "title": detail,
            "hint": "",
            "retryable": exc.status_code in (408, 409, 429, 500, 502, 503, 504),
        },
    )


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception):
    err = classify_error(exc)
    # Log the real exception — the user gets the friendly one.
    logger.error(
        "Unhandled exception on %s %s → %s: %s",
        request.method, request.url.path, err.code, exc,
        exc_info=True,
    )
    return JSONResponse(status_code=err.status, content=err.to_dict())

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(auth.router, prefix="/api")
app.include_router(projects.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(pages.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(prompts.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(providers.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(settings.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(generation.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(generation.ws_router)  # WS — no /api prefix, auth via token query param
app.include_router(exports.router, prefix="/api", dependencies=[Depends(get_current_user)])
