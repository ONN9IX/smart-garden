"""Fixed public API errors; never echo raw exception messages or input values."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

MESSAGES = {
    "INVALID_CREDENTIALS": "Неверный логин или пароль",
    "USER_BLOCKED": "Доступ к аккаунту заблокирован. Обратитесь к администратору сада.",
    "ORGANIZATION_BLOCKED": "Доступ к детскому саду заблокирован. Обратитесь к администратору.",
    "PASSWORD_CHANGE_REQUIRED": "Сначала измените временный пароль.",
    "INVALID_PASSWORD": "Пароль не соответствует требованиям. Выберите другой пароль.",
    "USERNAME_ALREADY_EXISTS": "Логин уже занят.",
    "UNAUTHORIZED": "Необходим вход в систему.",
    "FORBIDDEN": "Доступ запрещён.",
    "VALIDATION_ERROR": "Проверьте введённые данные.",
    "INTERNAL_ERROR": "Не удалось выполнить запрос. Попробуйте ещё раз.",
}


class AppError(Exception):
    def __init__(self, status: int, code: str, field: str | None = None):
        self.status = status
        self.code = code
        self.field = field


def error_response(status: int, code: str, field: str | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": MESSAGES[code], "field": field}})


async def app_error_handler(_request: Request, error: AppError) -> JSONResponse:
    return error_response(error.status, error.code, error.field)


async def validation_error_handler(_request: Request, _error: RequestValidationError) -> JSONResponse:
    # Pydantic's raw validation details can include the submitted password.
    return error_response(400, "VALIDATION_ERROR")
