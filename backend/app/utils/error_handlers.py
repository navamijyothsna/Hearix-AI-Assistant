from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

async def global_exception_handler(request: Request, exc: Exception):
    """
    Catches any unhandled Python exceptions.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred in the Blind Voice system.",
            "detail": str(exc) if True else None # Set to False in production
        },
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Catches FastAPI/Starlette specific HTTP exceptions.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "Request Error",
            "message": exc.detail
        },
    )