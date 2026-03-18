# DataChat Logging Guidelines and Best Practices

## Overview

This document provides guidelines for using the centralized logging system in the DataChat application. The logging system is designed to provide:

- Structured JSON logs for better analysis and querying
- Request ID tracking for correlation across components
- Performance metrics for critical operations
- Integration with Langfuse tracing
- Appropriate log levels for different environments

## Logging Architecture

The DataChat logging system consists of:

1. **Centralized Configuration** (`backend/observability/logging.py`) - Core logging module
2. **Request Context Tracking** - For correlating logs across components
3. **Logging Middleware** - For automatic request/response logging
4. **Component-Specific Loggers** - Configured through the central system
5. **Integration with Tracing** - Connection to Langfuse

## How to Use Logging in Your Code

### Getting a Logger

Always get a logger through the centralized configuration:

```python
from observability.logging import get_logger

# Initialize logger with the module name
logger = get_logger(__name__)
```

### Basic Logging

Use standard Python logging methods with appropriate log levels:

```python
# Debug logs (development details, not shown in production by default)
logger.debug("Initializing component")

# Info logs (normal operation events)
logger.info("Component initialized successfully")

# Warning logs (potential issues that don't prevent operation)
logger.warning("Configuration value missing, using default")

# Error logs (issues that prevent a function from working)
logger.error("Failed to connect to external service", exc_info=True)

# Critical logs (program cannot continue)
logger.critical("Database connection failed, application cannot function")
```

### Structured Logging with Properties

For richer, queryable logs, use the `log_with_props` helper:

```python
from observability.logging import log_with_props

log_with_props(logger, "info", "Query executed successfully",
              query_type="SELECT",
              row_count=15,
              execution_time_ms=45.2)
```

### Request Context

To maintain correlation across components:

```python
from observability.logging import RequestContext

# Get the current request ID (set by middleware)
request_id = RequestContext.get_request_id()

# Add context values
RequestContext.add_context("user_id", user_id)
```

### Timing Operations

Use the timing context manager for performance metrics:

```python
from observability.logging import log_execution_time

# Time a database operation
with log_execution_time(logger, "database_query"):
    results = execute_query(...)
```

### Function Call Logging

For automatic entry/exit logging with timing:

```python
from observability.logging import log_function_call

@log_function_call(logger)
def process_data(data):
    # Function body
    return result
```

## Log Levels

Use appropriate log levels based on the information importance:

| Level    | When to Use                                               | Environment Visibility |
| -------- | --------------------------------------------------------- | ---------------------- |
| DEBUG    | Detailed information for troubleshooting                  | Development, Testing   |
| INFO     | Confirmation that things are working as expected          | All environments       |
| WARNING  | An unexpected situation occurred, but operation continues | All environments       |
| ERROR    | An issue prevented a function from working                | All environments       |
| CRITICAL | Application cannot continue functioning                   | All environments       |

## Best Practices

### DO

1. **Be Consistent** - Use consistent naming and structure for log properties
2. **Include Context** - Always include enough context to understand the log entry
3. **Use Appropriate Levels** - Match log level to the importance of the information
4. **Log Boundaries** - Log at the entry and exit of key functions
5. **Time Critical Operations** - Use timing for performance-sensitive operations
6. **Log Failures with Details** - Include error information, but avoid sensitive data
7. **Limit Log Volume** - Be selective in DEBUG level logging

### DON'T

1. **Don't Log Sensitive Information** - Never log passwords, tokens, or personal data
2. **Don't Log Huge Objects** - Summarize or truncate large data structures
3. **Don't Create Custom Logging Solutions** - Use the centralized system
4. **Don't Overuse High-Level Logging** - Reserve ERROR and CRITICAL for actual issues
5. **Don't Use String Formatting for Variables** - Pass them as properties instead

## Examples

### API Endpoint Logging

```python
@app.post("/query")
def handle_query(request: QueryRequest):
    request_id = RequestContext.get_request_id()

    log_with_props(logger, "info", "Processing query request",
                  query_length=len(request.query),
                  request_id=request_id)

    try:
        # Process the request...

        log_with_props(logger, "info", "Query processed successfully",
                      request_id=request_id)
        return result
    except Exception as e:
        log_with_props(logger, "error", "Error processing query",
                      error=str(e),
                      request_id=request_id,
                      exc_info=True)
        raise
```

### Database Operation Logging

```python
def execute_query(query: str):
    request_id = RequestContext.get_request_id()

    log_with_props(logger, "info", "Executing database query",
                  query_type=query.strip().upper().split()[0],
                  request_id=request_id)

    with log_execution_time(logger, "db_query_execution"):
        result = perform_query(query)

    log_with_props(logger, "info", "Query executed successfully",
                  row_count=len(result),
                  request_id=request_id)

    return result
```

## Searching and Analyzing Logs

The JSON structure of the logs allows for easy filtering and analysis using log management tools:

- **Filter by request_id**: Find all logs for a specific request
- **Filter by component**: Focus on a specific system area
- **Search by operation**: Find all occurrences of a specific operation
- **Analyze performance**: Look at execution_time_ms values
- **Find errors**: Filter for error level entries

## Monitoring and Alerting

Configure monitoring and alerting based on log levels:

- **ERROR and CRITICAL**: Immediate alerts
- **WARNING**: Daily summaries
- **Performance Metrics**: Alerts on thresholds exceeded

## Integration with Langfuse Tracing

Logs and traces are correlated using request_id:

1. The request_id from logs matches the trace_id in Langfuse
2. Tags in Langfuse traces include the request_id for correlation
3. OpenTelemetry spans are linked to both logs and traces

## Troubleshooting Common Issues

### Missing Context in Logs

If logs lack context like request_id:

- Ensure the code is using RequestContext.get_request_id()
- Verify the LoggingMiddleware is correctly installed
- Check that log messages use log_with_props

### Excessive Log Volume

If logs become too voluminous:

- Adjust log levels in the environment configuration
- Review DEBUG level logs and reduce frequency
- Add sampling for high-frequency events

### Missing Performance Metrics

If timing information is missing:

- Ensure log_execution_time is used for critical operations
- Check that execution_time_ms is included in log properties
