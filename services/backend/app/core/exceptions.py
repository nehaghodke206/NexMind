from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(
        self,
        status_code: int,
        error: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=message)
        self.error = error
        self.message = message
        self.details = details or {}


class NotFoundException(AppException):
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error="not_found",
            message=f"{resource} '{identifier}' was not found",
            details={"resource": resource, "identifier": str(identifier)},
        )


class ConflictException(AppException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error="conflict",
            message=message,
            details=details,
        )


class BadRequestException(AppException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error="bad_request",
            message=message,
            details=details,
        )


class InvalidLifecycleTransitionException(AppException):
    def __init__(self, message: str, current_status: str, target_status: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error="invalid_lifecycle_transition",
            message=message,
            details={"current_status": current_status, "target_status": target_status},
        )
