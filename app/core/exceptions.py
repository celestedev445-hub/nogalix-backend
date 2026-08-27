from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.responses import fail


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_: Request, exc: StarletteHTTPException):
        detail = exc.detail
        if isinstance(detail, dict):
            payload = detail
        else:
            payload = fail(str(detail) if detail else "Une erreur est survenue.")
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError):
        errors: dict[str, list[str]] = {}
        for item in exc.errors():
            loc = item.get("loc") or ()
            field = str(loc[-1]) if loc else "body"
            errors.setdefault(field, []).append(item.get("msg", "Valeur invalide"))
        return JSONResponse(
            status_code=422,
            content=fail(
                "Les informations saisies sont invalides.",
                code="validation_error",
                errors=errors,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception):
        payload = fail("Une erreur inattendue s'est produite.")
        if settings.app_debug:
            payload["error"] = str(exc)
        return JSONResponse(status_code=500, content=payload)
