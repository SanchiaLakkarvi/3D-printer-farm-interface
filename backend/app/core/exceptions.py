from __future__ import annotations

from fastapi import HTTPException, status


class AppError(HTTPException):
    """Base application error with a machine-readable code."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
    ) -> None:
        super().__init__(
            status_code=status_code,
            detail={"code": code, "message": message},
        )


class NotFoundError(AppError):
    def __init__(self, entity: str, entity_id: str) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"{entity} {entity_id} not found",
        )


class ForbiddenError(AppError):
    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message=message,
        )


class ConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code="CONFLICT",
            message=message,
        )
