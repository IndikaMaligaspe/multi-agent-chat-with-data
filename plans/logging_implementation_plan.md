# DataChat Logging Implementation Plan

## Overview

This document outlines the implementation strategy for adding comprehensive logging to the DataChat project. The goal is to capture key events, errors, and performance metrics across all system components while integrating with the existing Langfuse tracing system.

## Implementation Steps

### 1. Create Centralized Logging Configuration Module

**File:** `backend/observability/logging.py`

```python
import json
import logging
import sys
import time
import uuid
from logging.handlers import RotatingFileHandler
from datetime import datetime
import os
from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator

# Configure environment-based log levels
LOG_LEVELS = {
    "development": logging.DEBUG,
    "testing": logging.DEBUG,
    "staging": logging.INFO,
    "production": logging.WARNING
}

# Get environment or default to development
ENV = os.getenv("ENVIRONMENT", "development")
DEFAULT_LOG_LEVEL = LOG_LEVELS.get(ENV, logging.INFO)

# Context for tracking request information across the application
class RequestContext:
    _request_id = None
    _user_id = None
    _session_id = None
    _additional_context = {}

    @classmethod
    def set_request_id(cls, request_id: Optional[str] = None) -> str:
        cls._request_id = request_id or str(uuid.uuid4())
        return cls._request_id

    @classmethod
    def get_request_id(cls) -> Optional[str]:
        return cls._request_id

    @classmethod
    def set_user_id(cls, user_id: str) -> None:
        cls._user_id = user_id

    @classmethod
    def get_user_id(cls) -> Optional[str]:
        return cls._user_id

    @classmethod
    def set_session_id(cls, session_id: str) -> None:
        cls._session_id = session_id

    @classmethod
    def get_session_id(cls) -> Optional[str]:
        return cls._session_id

    @classmethod
    def add_context(cls, key: str, value: Any) -> None:
        cls._additional_context[key] = value

    @classmethod
    def get_context(cls, key: str) -> Any:
        return cls._additional_context.get(key)

    @classmethod
    def get_all_context(cls) -> Dict[str, Any]:
        context = cls._additional_context.copy()
        if cls._request_id:
            context["request_id"] = cls._request_id
        if cls._user_id:
            context["user_id"] = cls._user_id
        if cls._session_id:
            context["session_id"] = cls._session_id
        return context


# Custom JSON Formatter
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request context if available
        request_context = RequestContext.get_all_context()
        if request_context:
            log_record.update(request_context)

        # Add exception info if available
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, 'props'):
            log_record.update(record.props)

        return json.dumps(log_record)


# Context manager for timing operations
@contextmanager
def log_execution_time(logger, operation_name: str) -> Generator[None, None, None]:
    start_time = time.time()
    try:
        yield
    finally:
        execution_time = time.time() - start_time
        logger.info(
            f"Operation {operation_name} completed",
            extra={"props": {"operation": operation_name, "execution_time_ms": round(execution_time * 1000, 2)}}
        )


def get_logger(name: str, log_level: Optional[int] = None) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Name for the logger, typically __name__ of the calling module
        log_level: Optional override for log level

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # If logger already has handlers, return it to avoid duplicate handlers
    if logger.handlers:
        return logger

    # Set log level from param or default
    logger.setLevel(log_level or DEFAULT_LOG_LEVEL)

    # Console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JsonFormatter())
    logger.addHandler(console_handler)

    # File handler with rotation
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(log_dir, exist_ok=True)

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "datachat.log"),
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)

    return logger


# Helper function for adding extra properties to log entries
def log_with_props(logger, level: str, message: str, **props):
    """
    Log a message with additional properties that get included in the JSON output.

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        props: Additional properties to include in the log
    """
    log_method = getattr(logger, level.lower())
    log_method(message, extra={"props": props})
```

### 2. Add FastAPI Middleware for Request/Response Logging

**File:** `backend/middleware/logging_middleware.py`

```python
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import traceback
from observability.logging import get_logger, RequestContext

logger = get_logger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # Generate a unique request ID
        request_id = RequestContext.set_request_id()

        # Log the request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "props": {
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params),
                    "client_host": request.client.host,
                    "request_id": request_id
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
                        "request_id": request_id
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
            raise  # Re-raise the exception
```

### 3. Integrate Logging with Database Operations in MCP Server

**Updates to:** `backend/mcp_server.py`

Key changes:

- Add logger initialization
- Log connection attempts and status
- Log query execution with timing
- Enhance error logging with query details
- Add performance metrics for query execution

```python
# Add at the top of the file
from observability.logging import get_logger, log_execution_time, log_with_props

# Initialize logger within the class
logger = get_logger(__name__)

# In connect() method:
logger.info("Attempting to connect to MySQL database")
# After connection:
logger.info("Connection to MySQL database established successfully",
           extra={"props": {"host": os.getenv('MYSQL_HOST'), "database": os.getenv('MYSQL_DATABASE')}})
# On error:
logger.error(f"Error connecting to MySQL database",
           extra={"props": {"error": str(e), "host": os.getenv('MYSQL_HOST')}})

# In execute_query():
logger.info(f"Executing SQL query",
           extra={"props": {"query_type": query.strip().upper().split()[0] if query else "UNKNOWN"}})

# Use the timing context manager:
with log_execution_time(logger, "sql_query_execution"):
    cursor.execute(query)

# On successful result:
logger.info(f"Query executed successfully",
           extra={"props": {"query_type": query.strip().upper().split()[0], "row_count": len(results)}})

# On error:
logger.error(f"Error executing query",
           extra={"props": {"error": str(e), "query_type": query.strip().upper().split()[0] if query else "UNKNOWN"}})
```

### 4. Add Logging to Workflow Nodes

**Updates to:** `backend/graph/workflow.py`

Key changes:

- Add logger to each node function
- Log node entry and exit with state info
- Log state transitions and routing decisions
- Add error logging for failures

```python
# Add at the top of the file
from observability.logging import get_logger, log_execution_time, RequestContext

logger = get_logger(__name__)

# Update node functions like sql_node():
def sql_node(state: AgentState) -> AgentState:
    """SQL Agent Node"""
    node_name = "sql_node"
    logger.info(f"Entering node: {node_name}",
               extra={"props": {"node": node_name, "query": state['query']}})

    try:
        with log_execution_time(logger, f"{node_name}_execution"):
            from agents.sql_agent import SQLAgent
            agent = SQLAgent()
            result = agent.run(state['query'])

        # Log successful execution
        success = result.get('success', False)
        logger.info(
            f"SQL agent execution {'succeeded' if success else 'failed'}",
            extra={"props": {
                "node": node_name,
                "success": success,
                "error": result.get('error') if not success else None
            }}
        )

        updated_state = {
            **state,
            'sql_result': state.get('sql_result', []) + [result],
        }

        logger.info(f"Exiting node: {node_name}",
                   extra={"props": {"node": node_name}})
        return updated_state

    except Exception as e:
        logger.error(f"Error in node: {node_name}",
                    extra={"props": {"node": node_name, "error": str(e)}})
        # Propagate the error or handle it as appropriate for your workflow
        raise
```

### 5. Update SQL Agent with Logging

**Updates to:** `backend/agents/sql_agent.py`

Key changes:

- Add logger initialization
- Log agent creation and tool initialization
- Log query execution start and completion
- Track LLM interactions
- Enhanced error logging

```python
# Add at the top of the file
from observability.logging import get_logger, log_execution_time, RequestContext

logger = get_logger(__name__)

# In __init__:
logger.info("Initializing SQL Agent")

# In _create_tools:
logger.debug("Creating SQL Agent tools")

# In run method:
logger.info(f"Executing natural language query",
           extra={"props": {"query": query}})

try:
    with log_execution_time(logger, "sql_agent_execution"):
        result = self.agent_executor.invoke({
            "messages": [("user", query)]
        })

    # Log successful execution
    logger.info(f"SQL Agent execution completed",
               extra={"props": {"success": True}})

    # Extract final answer
    # ...existing code...

    return {
        'success': True,
        'output': final_answer or "No answer generated",
        'full_trace': messages
    }

except Exception as e:
    logger.error(f"SQL Agent execution failed",
               extra={"props": {"error": str(e), "query": query}})
    return {
        'success': False,
        'error': str(e)
    }
```

### 6. Add Logging to Validation Process

**Updates to:** `backend/guardrails_validators.py`

Key changes:

- Add logger initialization
- Log validation attempts & results
- Detailed logging for injection prevention
- Log validation errors with context

```python
# Add at the top of the file
from observability.logging import get_logger, RequestContext

logger = get_logger(__name__)

# In validate_query:
logger.info(f"Validating query",
           extra={"props": {"query": query, "max_results": max_results}})

try:
    validated = QueryRequest(query=query, max_results=max_results)
    logger.info("Query validation successful")
    return {
        'valid': True,
        'validated_query': validated.query,
        'max_results': validated.max_results
    }
except Exception as e:
    logger.warning(f"Query validation failed",
                 extra={"props": {"error": str(e), "query": query}})
    return {
        'valid': False,
        'error': str(e)
    }

# In prevent_sql_injection validator:
for pattern, description in dangerous_patterns:
    if re.search(pattern, v, re.IGNORECASE):
        logger.warning(f"SQL injection attempt detected",
                     extra={"props": {"pattern": description, "query": v}})
        raise ValueError(
            f"Potential SQL injection detected: {description}. "
            f"Please rephrase your question."
        )
```

### 7. Update Main.py to Integrate Logging Middleware

**Updates to:** `backend/main.py`

Key changes:

- Update logger initialization to use new centralized configuration
- Add logging middleware
- Ensure request ID is propagated to Langfuse traces

```python
# Replace existing logger initialization
from observability.logging import get_logger, RequestContext
from middleware.logging_middleware import LoggingMiddleware

# Initialize logger
logger = get_logger(__name__)

# Add middleware
app.add_middleware(LoggingMiddleware)

# In handle_query endpoint, add trace ID correlation:
@app.post("/query", response_model=QueryResponse)
def handle_query(request: QueryRequest):
    """Main endpoint to handle natural language queries"""
    request_id = RequestContext.get_request_id()

    try:
        # Add correlation ID to response
        # ...existing validation and processing code...

        return QueryResponse(
            success=True,
            answer=answer.get('final_answer', 'No answer generated'),
            trace_id=request_id)
    # ...error handling...
```

### 8. Integrate Logging with Langfuse Tracing

**Updates to:** `backend/observability/tracing.py`

Key changes:

- Connect request IDs between logging & tracing
- Ensure consistent correlation between systems

```python
# Add import for RequestContext
from observability.logging import RequestContext, get_logger

logger = get_logger(__name__)

@observe(name="DataChat Query")
def trace_agent_run(query: str):
    """Wrapper for agent execution with tracing."""
    # Get the current request ID from logging context
    request_id = RequestContext.get_request_id()

    from graph.workflow import create_workflow
    graph = create_workflow()

    # Add request_id to trace for correlation
    with propagate_attributes(
        user_id=RequestContext.get_user_id() or "12345",
        tags={"query_type": "analytics", "request_id": request_id}
    ):
        # Add to OpenTelemetry as well
        trace.get_current_span().set_attribute("request_id", request_id)
        trace.get_current_span().set_attribute("query_type", "analytics")

        logger.info(f"Starting traced agent execution",
                   extra={"props": {"query": query}})

        # Execute graph
        result = graph.invoke({
            'query': query,
            'sql_result': [],
            'validation_result': [],
            'final_answer': '',
            'errors': []
        })

        logger.info(f"Completed traced agent execution")

    return result
```

## Application Structure Updates

- Create `backend/logs` directory for log files
- Create `backend/middleware` directory for the middleware module

## Execution Strategy

1. **First Phase: Core Infrastructure**
   - Create the centralized logging module and middleware
   - Update main.py to use the new logging infrastructure
   - Test basic request logging

2. **Second Phase: Database and Workflow**
   - Add logging to MCP server operations
   - Implement workflow node logging
   - Integrate with Langfuse tracing

3. **Third Phase: Agents and Validation**
   - Update SQL agent with detailed logging
   - Add logging to validation processes
   - Test the full request flow with logging

4. **Final Phase: Performance and Monitoring**
   - Add performance metric logging
   - Set up log rotation and retention policies
   - Create logging documentation

## Testing Strategy

For each component, test:

1. Normal operation logging
2. Error condition logging
3. Performance metric capture
4. Integration with other components

## Best Practices

- Keep sensitive information out of logs (credentials, PII)
- Use appropriate log levels:
  - DEBUG: Detailed information for debugging
  - INFO: Confirmation that things are working as expected
  - WARNING: Something unexpected happened but operation continues
  - ERROR: An error occurred that prevents a function from working
  - CRITICAL: Program cannot continue

- Always include request_id for correlation
- Include timing information for performance-sensitive operations
- Structure log messages consistently
