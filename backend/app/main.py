import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router
from app.core.config import get_settings
from app.core.database import get_engine
from app.core.exceptions import register_handlers
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logging.getLogger("studyspot").info(
        "application_started environment=%s", get_settings().app_env
    )
    yield
    get_engine().dispose()


def create_app():
    settings = get_settings()
    app = FastAPI(
        title="StudySpot API",
        version="0.3.0",
        description="Persistent campus data foundation with Supabase-verified sign-in. Seed forecasts are NOT ML output.",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )
    register_handlers(app)
    app.include_router(router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
