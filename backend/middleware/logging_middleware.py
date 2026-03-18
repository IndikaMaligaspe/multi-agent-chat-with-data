"""
Logging middleware for FastAPI applications.

This middleware:
- Generates a unique request ID for each request
- Logs request details (method, path, query params, etc.)
- Logs response details (status code, processing time)
- Captures and logs any unhandled exceptions
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
import time
import traceback
from observability.logging import get_logger, RequestContext

# Initialize logger
logger = get_logger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that logs all incoming requests and responses.
    Also provides request ID generation and tracking.
    """
    
    def __init__(self, app: ASGIApp):
        """
        Initialize the middleware.
        
        Args:
            app (ASGIApp): The ASGI application
        """
        super().__init__(app)
        
    async def dispatch(self, request: Request, call_next):
        """
        Process the request, log details, and track timing.
        
        Args:
            request (Request): The incoming request
            call_next (Callable): The next middleware or route handler
            
        Returns:
            Response: The response from the next middleware or route handler
        """
        # Generate a unique request ID
        request_id = RequestContext.set_request_id()
        
        # Extract client IP - handle forwarded requests
        client_host = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_host = forwarded_for.split(",")[0].strip()
            
        # Log the request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "props": {
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params),
                    "client_host": client_host,
                    "request_id": request_id,
                    "user_agent": request.headers.get("User-Agent", "unknown")
                }
            }
        )
        
        # Time the request processing
        start_time = time.time()
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log the response
            logger.info(
                f"Request completed: {request.method} {request.url.path}",
                extra={
                    "props": {
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "processing_time_ms": round(process_time * 1000, 2),
                        "request_id": request_id,
                        "content_type": response.headers.get("Content-Type", "unknown")
                    }
                }
            )
            
            return response
            
        except Exception as e:
            # Log any unhandled exceptions
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "props": {
                        "method": request.method,
                        "path": request.url.path,
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                        "processing_time_ms": round(process_time * 1000, 2),
                        "request_id": request_id
                    }
                }
            )
            raise  # Re-raise the exception for FastAPI's exception handlers