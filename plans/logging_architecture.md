# DataChat Logging Architecture

## Components and Flow

```mermaid
graph TD
    Client[Client] -->|Request| FastAPI[FastAPI App]

    subgraph "Logging Infrastructure"
        LogConfig[Centralized Logging Configuration]
        LogMiddleware[Logging Middleware]
        RequestContext[Request Context]
        LogHandlers[Log Handlers] -->|Output| LogStorage[(Log Storage)]
    end

    subgraph "Application Components"
        FastAPI -->|Routes to| Endpoint[API Endpoints]
        Endpoint -->|Calls| Validator[Query Validator]
        Validator -->|Validates| Tracer[Tracing Wrapper]
        Tracer -->|Executes| Workflow[LangGraph Workflow]
        Workflow -->|Uses| SQLAgent[SQL Agent]
        SQLAgent -->|Queries| Database[(Database)]
    end

    subgraph "Observability Integration"
        LangfuseTracing[Langfuse Tracing]
        MetricsCollection[Performance Metrics]
    end

    FastAPI -->|Intercepts| LogMiddleware
    LogMiddleware -->|Uses| LogConfig
    LogMiddleware -->|Creates/Updates| RequestContext

    Endpoint -->|Logs via| LogConfig
    Validator -->|Logs via| LogConfig
    Tracer -->|Logs via| LogConfig
    Workflow -->|Logs via| LogConfig
    SQLAgent -->|Logs via| LogConfig
    Database -->|Logs via| LogConfig

    RequestContext -->|Correlates with| LangfuseTracing
    LogConfig -->|Configures| LogHandlers
    LogConfig -->|Captures| MetricsCollection

    style LogConfig fill:#f9f,stroke:#333,stroke-width:2px
    style RequestContext fill:#bbf,stroke:#333,stroke-width:2px
    style LangfuseTracing fill:#bfb,stroke:#333,stroke-width:2px
```

## Request Flow with Logging

```mermaid
sequenceDiagram
    participant Client
    participant LogMiddleware as Logging Middleware
    participant Endpoint as API Endpoint
    participant LogSystem as Logging System
    participant Validator as Query Validator
    participant Tracer as Tracing Wrapper
    participant Workflow as LangGraph Workflow
    participant SQLAgent as SQL Agent
    participant Database

    Client->>LogMiddleware: Send request
    LogMiddleware->>LogSystem: Generate request_id
    LogMiddleware->>LogSystem: Log request details
    LogMiddleware->>Endpoint: Forward request

    Endpoint->>LogSystem: Log operation start
    Endpoint->>Validator: Validate query

    Validator->>LogSystem: Log validation attempt
    Validator->>LogSystem: Log validation result
    Validator-->>Endpoint: Return validation result

    Endpoint->>Tracer: Execute traced operation
    Tracer->>LogSystem: Pass request_id to trace
    Tracer->>Workflow: Execute workflow

    Workflow->>LogSystem: Log workflow start
    Workflow->>SQLAgent: Execute query

    SQLAgent->>LogSystem: Log agent operation
    SQLAgent->>Database: Execute SQL
    Database-->>SQLAgent: Return results
    SQLAgent->>LogSystem: Log query results
    SQLAgent-->>Workflow: Return results

    Workflow->>LogSystem: Log workflow completion
    Workflow-->>Tracer: Return workflow results

    Tracer->>LogSystem: Log trace completion
    Tracer-->>Endpoint: Return results

    Endpoint->>LogSystem: Log operation completion
    Endpoint-->>LogMiddleware: Send response

    LogMiddleware->>LogSystem: Log response details
    LogMiddleware-->>Client: Return response
```

## Log Data Structure

```mermaid
classDiagram
    class LogEntry {
        timestamp: ISO8601 datetime
        level: string
        logger: string
        message: string
        module: string
        function: string
        line: number
        request_id: string
        user_id: string
        session_id: string
        additional_context: object
    }

    class PerformanceMetric {
        operation: string
        execution_time_ms: number
        timestamp: ISO8601 datetime
        request_id: string
    }

    class RequestLog {
        method: string
        path: string
        query_params: string
        client_host: string
        status_code: number
        processing_time_ms: number
        request_id: string
    }

    class ErrorLog {
        error: string
        traceback: string
        context: object
        request_id: string
    }

    LogEntry <|-- PerformanceMetric
    LogEntry <|-- RequestLog
    LogEntry <|-- ErrorLog
```

## Implementation Dependencies

```mermaid
graph TD
    A[Centralized Logging Module] -->|Required for| B[Logging Middleware]
    A -->|Required for| C[Component-specific Logging]
    B -->|Required for| D[Request Tracking]
    A -->|Required for| E[Langfuse Integration]
    C -->|Required for| F[Performance Metrics]

    subgraph "Implementation Order"
        A
        B
        D
        C
        F
        E
    end
```

## Directory Structure

```
backend/
├── observability/
│   ├── __init__.py
│   ├── logging.py     (new)
│   └── tracing.py     (updated)
├── middleware/
│   ├── __init__.py    (new)
│   └── logging_middleware.py (new)
├── logs/              (new directory)
├── main.py            (updated)
├── agents/
│   └── sql_agent.py   (updated)
├── graph/
│   └── workflow.py    (updated)
└── guardrails_validators.py (updated)
```
