"""
Стандартизированная обработка ошибок (Занятие 6)

Формат: {"error": {"code": "...", "message": "...", "details": {...}}}
"""

from typing import Any, Dict, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class AppException(Exception):
    """Базовое исключение"""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class NotFoundError(AppException):
    def __init__(self, resource: str, identifier: Any = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code=f"{resource.upper()}_NOT_FOUND",
            message=f"{resource} не найден",
            details={"id": identifier} if identifier else None,
        )


class ValidationError(AppException):
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message=message,
            details=details,
        )


class AuthError(AppException):
    def __init__(self, message: str = "Ошибка аутентификации"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="AUTH_ERROR",
            message=message,
        )


class ForbiddenError(AppException):
    def __init__(self, message: str = "Доступ запрещен"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message=message,
        )


# Exception Handlers


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": ".".join(str(x) for x in error["loc"]),
                "message": error["msg"],
            }
        )

    # Попытка залогировать контекст для быстрого дебага (без паролей)
    try:
        payload = await request.json()
        if isinstance(payload, dict):
            sanitized = {k: ("***" if k.lower() == "password" else v) for k, v in payload.items()}
        else:
            sanitized = str(payload)
    except Exception:
        sanitized = "<unable to read body>"

    import logging

    logging.warning(
        f"Validation error on {request.method} {request.url.path}: "
        f"errors={errors} payload={sanitized}"
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Ошибка валидации",
                "details": {"errors": errors},
            }
        },
    )


def register_exception_handlers(app):
    """Регистрация обработчиков"""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
