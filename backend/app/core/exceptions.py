import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

logger = logging.getLogger("studyspot")


class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 404):
        self.code, self.message, self.status = code, message, status


def error_response(code: str, message: str, status: int):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def register_handlers(app: FastAPI):
    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError):
        return error_response(exc.code, exc.message, exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Do not echo submitted values, which might contain credentials in future phases.
        return error_response("VALIDATION_ERROR", "Request parameters or body are invalid.", 422)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return error_response("HTTP_ERROR", "The request could not be completed.", exc.status_code)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        logger.error("database_request_failure type=%s", type(exc).__name__)
        return error_response(
            "DATABASE_UNAVAILABLE", "Data is temporarily unavailable. Please retry.", 503
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logger.error("unexpected_request_failure type=%s", type(exc).__name__)
        return error_response("INTERNAL_ERROR", "An unexpected error occurred. Please retry.", 500)
