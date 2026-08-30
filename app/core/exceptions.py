from fastapi import HTTPException, status


class ERPError(HTTPException):
    """Base class for domain errors surfaced to the API."""

    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


class NotFound(ERPError):
    def __init__(self, what: str = "Resource"):
        super().__init__(f"{what} not found", status.HTTP_404_NOT_FOUND)


class PermissionDenied(ERPError):
    def __init__(self, detail: str = "You do not have permission to perform this action"):
        super().__init__(detail, status.HTTP_403_FORBIDDEN)


class BusinessRuleError(ERPError):
    """Raised when a deterministic ERP invariant would be violated (e.g. unbalanced journal)."""
