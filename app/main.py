from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.limiter import limiter
from app.modules.assistant.router import router as assistant_router
from app.modules.auth.router import router as auth_router
from app.modules.contact.router import router as contact_router
from app.modules.convert.router import router as convert_router
from app.modules.cv.router import router as cv_router
from app.modules.health.router import router as health_router
from app.modules.notifications.router import router as notifications_router
from app.modules.profile.router import router as profile_router
from app.modules.plans.router import router as plans_router
from app.modules.candidature.router import router as candidature_router
from app.modules.templates.router import router as templates_router


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        docs_url="/docs" if settings.app_debug else None,
        redoc_url=None,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"],
    )

    register_exception_handlers(app)

    api = APIRouter(prefix="/api")
    api.include_router(health_router)
    api.include_router(auth_router)
    api.include_router(cv_router)
    api.include_router(profile_router)
    api.include_router(notifications_router)
    api.include_router(assistant_router)
    api.include_router(contact_router)
    api.include_router(convert_router)
    api.include_router(templates_router)
    api.include_router(plans_router)
    api.include_router(candidature_router)
    app.include_router(api)

    uploads = Path(__file__).resolve().parent.parent / "storage" / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    app.mount("/storage/uploads", StaticFiles(directory=str(uploads)), name="uploads")

    @app.get("/")
    def root():
        return {
            "app": settings.app_name,
            "docs": "/docs" if settings.app_debug else None,
            "api": "/api/health",
        }

    return app


app = create_app()
