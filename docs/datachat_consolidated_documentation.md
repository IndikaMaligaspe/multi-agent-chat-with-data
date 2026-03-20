# DataChat — Consolidated Project Documentation

> **Purpose:** This document serves as a single authoritative reference for the DataChat project — its architecture, components, features, bug fixes, and design decisions. It is intended to provide sufficient context for developers, LLMs, and AI agents to understand, maintain, and extend the project.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Backend Components](#3-backend-components)
4. [Frontend Components](#4-frontend-components)
5. [API Design](#5-api-design)
6. [Widget Framework](#6-widget-framework)
7. [Observability & Logging](#7-observability--logging)
8. [Features Implemented](#8-features-implemented)
9. [Issues Fixed](#9-issues-fixed)
10. [Architectural Decisions](#10-architectural-decisions)
11. [Open Gaps & Future Work](#11-open-gaps--future-work)
12. [Configuration & Environment](#12-configuration--environment)
13. [How to Run](#13-how-to-run)
14. [How to Add a New Widget Type](#14-how-to-add-a-new-widget-type)

---

## 1. Project Overview

**DataChat** is a natural language → SQL → UI widget application. Users type plain-English questions in a chat interface; a GPT-4-powered SQL agent translates them into SQL, executes the query against a MySQL database, and displays the result as a typed, rich UI widget inside a React chat interface.

### Core Flow

```
User types question
       │
       ▼
React Chat UI (frontend)
       │  POST /query
       ▼
FastAPI Backend
       │
       ▼
LangGraph Workflow
  ├── sql_node      → LangChain SQL Agent (GPT-4) → executes SQL via MCP
  ├── validation_node → validates SQL result
  └── answer_node   → detects widget type, formats response
       │
       ▼
Widget Formatter → JSON response
       │
       ▼
React Widget Renderer → TableWidget / AggregationWidget / etc.
```

### Technology Stack

| Layer            | Technology                            |
| ---------------- | ------------------------------------- |
| Frontend         | React (functional + class components) |
| Backend API      | FastAPI (Python)                      |
| AI Orchestration | LangGraph StateGraph                  |
| SQL Agent        | LangChain + GPT-4 (temperature=0)     |
| Database         | MySQL                                 |
| Observability    | Langfuse + OpenTelemetry              |
| Logging          | Python `logging` with JSON formatter  |

---

## 2. System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                      │
│                                                              │
│  App.js                                                      │
│   ├── useSendMessage (hook) ──────────────── POST /query    │
│   ├── useChatMessages (hook)                                 │
│   └── useWidgetActions (hook)                                │
│                                                              │
│  AIMessage.js                                                │
│   ├── Direct rendering: TableWidget / AggregationWidget     │
│   └── WidgetContainer → WidgetRegistry → Widget Component   │
└─────────────────────────────────────────────────────────────┘
                          │ HTTP
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                     │
│                                                              │
│  main.py  (POST /query, GET /schema, GET /health)           │
│   └── LoggingMiddleware (request_id, timing)                │
│                                                              │
│  LangGraph Workflow                                          │
│   ├── sql_node ──► sql_agent.py ──► mcp_server.py (MySQL)  │
│   ├── validation_node                                        │
│   └── answer_node ──► widget_formatter.py                   │
│                                                              │
│  Observability                                               │
│   ├── observability/logging.py (JsonFormatter, request_id)  │
│   └── observability/tracing.py (Langfuse, OpenTelemetry)    │
└─────────────────────────────────────────────────────────────┘
                          │ SQL
┌─────────────────────────────────────────────────────────────┐
│                         MySQL Database                       │
└─────────────────────────────────────────────────────────────┘
```

### LangGraph Workflow

```
[Entry]
   │
   ▼
sql_node
   │  Invokes LangChain SQL Agent (get_schema + execute_sql tools)
   │  Stores result in AgentState.sql_result
   ▼
validation_node
   │  Validates SQL result, checks for errors
   ▼
answer_node
   │  Checks sql_result.output first (reuses agent answer)
   │  Falls back to GPT-4 for formatting if needed
   │  Detects widget type from data shape + query keywords
   │  Calls WidgetFormatter to produce typed JSON
   ▼
[Response → FastAPI → Frontend]
```

---

## 3. Backend Components

### 3.1 `backend/main.py`

The FastAPI application entry point. Defines three endpoints:

| Endpoint  | Method | Description                                             |
| --------- | ------ | ------------------------------------------------------- |
| `/query`  | POST   | Accepts natural language query, returns widget response |
| `/schema` | GET    | Returns the MySQL database schema                       |
| `/health` | GET    | Health check endpoint                                   |

Applies `LoggingMiddleware` globally. Uses `guardrails_validators.QueryRequest` for input validation. Handles JSON serialisation via `CustomJsonEncoder`.

### 3.2 `backend/agents/sql_agent.py`

Implements a LangChain ReAct agent with two tools:

- **`get_schema`** — retrieves the MySQL schema via `mcp_server.get_schema()`
- **`execute_sql`** — runs a SQL query via `mcp_server.execute_query()`

Configured with GPT-4 at `temperature=0` for deterministic SQL generation.

### 3.3 `backend/graph/workflow.py`

Defines the LangGraph `StateGraph` with three nodes:

```python
# Node definitions
sql_node       → runs sql_agent, populates AgentState.sql_result
validation_node → validates sql_result, flags errors
answer_node    → determines widget type, formats final response
```

**`validation_node` logic:**

1. Receives `AgentState.sql_result` from `sql_node`
2. Applies validation rules:
   - Checks for empty results (`[]` or `None`)
   - Validates data structure integrity (expected fields present)
   - Verifies data types match expected schema
   - Checks for SQL error messages in response
3. On validation failure:
   - Logs detailed error with `request_id`
   - Sets `AgentState.validation_error = True`
   - Adds error context to `AgentState.validation_message`
   - Flow continues to `answer_node` for graceful error handling
4. On validation success:
   - Sets `AgentState.validation_error = False`
   - Flow continues to `answer_node` with validated data

**`answer_node` logic:**

1. Checks `sql_result.output` — if agent already produced a final answer, reuses it (avoids redundant GPT-4 call)
2. Auto-detects widget type based on data shape and query keywords (e.g., `COUNT`, `SUM` → aggregation)
3. Calls `WidgetFormatter` to produce structured JSON response
4. If `AgentState.validation_error = True`, formats an error message as a `text` widget with the validation error details

**Known issue:** `AgentState.sql_result` type is inconsistently typed as `dict | list` — this is an open gap.

### 3.4 `backend/mcp_server.py`

MySQL abstraction layer providing two public functions:

- **`execute_query(sql: str) → list[dict]`** — runs SQL, converts `datetime` objects to ISO strings
- **`get_schema() → str`** — returns schema description for the SQL agent

Handles datetime serialisation to prevent `Object of type datetime is not JSON serializable` errors.

### 3.5 `backend/widget_formatter.py`

`WidgetFormatter` class with type-specific formatting methods:

| Method                            | Widget Type    | Output Structure              |
| --------------------------------- | -------------- | ----------------------------- |
| `format_as_table_widget()`        | `table`        | `{columns, rows, headers}`    |
| `format_as_aggregation_widget()`  | `aggregation`  | `{label, value, count, unit}` |
| `format_as_comparison_widget()`   | `comparison`   | `{items: [{label, value}]}`   |
| `format_as_confirmation_widget()` | `confirmation` | `{message, options}`          |
| `format_as_options_widget()`      | `options`      | `{prompt, choices}`           |
| `format_as_text_widget()`         | `text`         | `{content}`                   |

Uses **relative imports** (`from .json_encoder import`) to avoid `No module named 'backend'` errors.

### 3.6 `backend/json_encoder.py`

Provides two JSON encoder classes:

- **`CustomJsonEncoder`** — extends `json.JSONEncoder`; handles `datetime`, `date`, `Decimal`, and unknown types
- **`DateTimeEncoder`** — specialised encoder for datetime → ISO 8601 string conversion

Used in `mcp_server.py` and `main.py` to ensure all responses are JSON-serialisable.

### 3.7 `backend/guardrails_validators.py`

Pydantic model for request validation:

```python
class QueryRequest(BaseModel):
    query: str  # validated against SQL injection regex patterns
```

Applies regex-based SQL injection prevention on incoming queries.

---

## 4. Frontend Components

### 4.1 `frontend/src/App.js`

Root component. Wires together the two primary hooks:

```
useSendMessage ──onResponseReceived──► useChatMessages
```

This callback wiring was a critical bug fix (Issue #6) — without it, API responses never appeared in the chat.

### 4.2 `frontend/src/components/messages/AIMessage.js`

Responsible for widget type detection and rendering. Implements a **two-path rendering strategy**:

- **Direct rendering (fast path):** `table` and `aggregation` types rendered inline, bypassing `WidgetContainer`/`WidgetRegistry`
- **Standard path:** All other widget types go through `WidgetContainer → WidgetRegistry → Widget Component`

Contains multi-layer type propagation: reads `message.type`, `message.metadata.widgetType`, and data shape to determine the correct widget.

**Aggregation value fix:** Uses `value ?? count ?? 0` (nullish coalescing) instead of `value || count || 0` to correctly display `0` values.

### 4.3 `frontend/src/components/widgets/WidgetContainer.js`

A **class component** (required for React Error Boundaries). Key responsibilities:

- `processWidgetData()` — normalises and validates widget data before rendering
- `getDerivedStateFromError()` — catches render errors, displays fallback
- `componentDidUpdate` with `refreshTimestamp` guard — triggers re-processing without infinite loops
- Prop immutability: uses `{ ...processedData, metadata }` spread instead of mutating props directly

### 4.4 `frontend/src/components/widgets/WidgetRegistry.js`

Simple dictionary-based widget registry:

```javascript
getWidget(type); // returns component for type
registerWidget(type, component); // registers a new widget type
```

### 4.5 Widget Components

| Component             | File                     | Purpose                                                                     |
| --------------------- | ------------------------ | --------------------------------------------------------------------------- |
| `TableWidget`         | `TableWidget.js`         | Renders tabular SQL results; supports both array-row and object-row formats |
| `AggregationWidget`   | `AggregationWidget.js`   | Renders single-value aggregations (COUNT, SUM, AVG)                         |
| `ComparisonWidget`    | `ComparisonWidget.js`    | Side-by-side comparison of multiple values                                  |
| `ConfirmationWidget`  | `ConfirmationWidget.js`  | Yes/No confirmation prompt with action round-trip                           |
| `OptionsWidget`       | `OptionsWidget.js`       | Multi-choice option selector                                                |
| `TextWidget`          | `TextWidget.js`          | Plain-text fallback renderer                                                |
| `DirectTableRenderer` | `DirectTableRenderer.js` | Resilient direct table renderer, bypasses full widget pipeline              |

### 4.6 React Hooks

#### `useSendMessage.js`

- Makes `POST /query` API call
- Tracks `lastWidgetType` for widget transition logic
- Calls `onResponseReceived` callback with processed response
- Propagates `metadata.widgetType` → `type` as one of four type-safety checkpoints

#### `useChatMessages.js`

- Manages chat message state array
- Exposes: `addUserMessage`, `addResponseMessage`, `updateMessage`

#### `useWidgetActions.js`

- Handles interactive widget callbacks: confirm, select, cancel
- Makes action round-trip to backend `/query` endpoint

### 4.7 `frontend/src/services/api.js`

HTTP client layer. Contains `processResponseData()` which applies **trust-API-first** type resolution:

```javascript
// Trust-API-first logic:
if (widgetType is present in API response metadata) {
  use API-provided widgetType
} else {
  infer widgetType from data shape
}
```

This prevents the bug where `processResponseData()` always overrode the API-provided type (Issue #13).

### 4.8 `frontend/src/utils/messageFormatter.js`

Parses raw API response into internal message object format. Performs:

- Table structure auto-detection
- `metadata.widgetType` → `type` propagation
- Stringified JSON handling (parses string responses that are actually JSON)

### 4.9 `frontend/src/utils/widgetUtils.js`

Contains `shouldReplaceWidget()` — determines whether a new widget response should replace the previous widget in the chat (e.g., aggregation → table transitions).

### 4.10 `frontend/src/components/layout/`

This directory is currently empty and reserved for future layout components. It is intended to house components that will control the overall application layout, including:

- Page layouts
- Navigation components
- Responsive grid systems
- Layout containers
- Sidebar components
- Header/footer components

As the application grows beyond the current chat interface, these layout components will provide structure and consistency across different views and features.

---

## 5. API Design

### Standard Request

```http
POST /query
Content-Type: application/json

{
  "query": "How many customers do we have?"
}
```

### Standard Response Shape

```json
{
  "success": true,
  "answer": {
    "type": "aggregation",
    "data": {
      "label": "Total Customers",
      "value": 1247,
      "unit": null
    },
    "metadata": {
      "widgetType": "aggregation",
      "sortable": false
    },
    "fallback": "There are 1,247 customers in total."
  },
  "trace_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Response Shape by Widget Type

**Table:**

```json
{
  "type": "table",
  "data": {
    "columns": ["id", "name", "email"],
    "rows": [["1", "Alice", "alice@example.com"]],
    "headers": ["ID", "Name", "Email"]
  },
  "metadata": { "widgetType": "table", "sortable": true }
}
```

**Aggregation:**

```json
{
  "type": "aggregation",
  "data": {
    "label": "Total Revenue",
    "value": 98532.5,
    "count": null,
    "unit": "USD"
  },
  "metadata": { "widgetType": "aggregation" }
}
```

**Comparison:**

```json
{
  "type": "comparison",
  "data": {
    "items": [
      { "label": "Q1 Revenue", "value": 45000 },
      { "label": "Q2 Revenue", "value": 53532 }
    ]
  },
  "metadata": { "widgetType": "comparison" }
}
```

**Confirmation:**

```json
{
  "type": "confirmation",
  "data": {
    "message": "Are you sure you want to delete this record?",
    "options": ["Yes, delete", "Cancel"]
  },
  "metadata": { "widgetType": "confirmation" }
}
```

**Options:**

```json
{
  "type": "options",
  "data": {
    "prompt": "Which department would you like to view?",
    "choices": ["Engineering", "Sales", "Marketing"]
  },
  "metadata": { "widgetType": "options" }
}
```

---

## 6. Widget Framework

### Widget Type Detection (Backend)

`answer_node` in `workflow.py` auto-detects widget type using:

1. **Data shape analysis** — single-value results → aggregation; multi-row → table; two-column comparison → comparison
2. **Query keyword matching** — `COUNT`, `SUM`, `AVG`, `TOTAL`, `HOW MANY` → aggregation; `COMPARE`, `VS` → comparison
3. **Default fallback** — unrecognised shapes → text widget

### Widget Rendering Pipeline (Frontend)

```
API Response
     │
     ▼
api.js → processResponseData()        [Checkpoint 1: type resolution]
     │
     ▼
useSendMessage.js                     [Checkpoint 2: widgetType propagation]
     │
     ▼
messageFormatter.js                   [Checkpoint 3: message object assembly]
     │
     ▼
AIMessage.js → widget type detection  [Checkpoint 4: render decision]
     │
     ├── table / aggregation ──────► DirectTableRenderer / inline render
     │
     └── other types ──────────────► WidgetContainer
                                           │
                                           ▼
                                      WidgetRegistry.getWidget(type)
                                           │
                                           ▼
                                      Widget Component (render)
```

### Widget State Management

- `shouldReplaceWidget()` in `widgetUtils.js` handles transitions between widget types
- `useSendMessage` tracks `lastWidgetType` to detect transitions (e.g., aggregation → table)
- `WidgetContainer.componentDidUpdate` uses `refreshTimestamp` (timestamp comparison) not boolean flags to trigger re-rendering

### Error Boundary

`WidgetContainer` is a class component implementing React's Error Boundary pattern:

```javascript
static getDerivedStateFromError(error) {
  return { hasError: true, error };
}
```

On error, renders the `fallback` plain-text string from the response. Every widget response includes a `fallback` field as a safety net.

---

## 7. Observability & Logging

### `backend/observability/logging.py`

Provides structured JSON logging infrastructure:

| Export                                        | Purpose                                                                  |
| --------------------------------------------- | ------------------------------------------------------------------------ |
| `JsonFormatter`                               | Formats log records as JSON with timestamp, level, message, extra fields |
| `RequestContext`                              | Thread-local storage for `request_id` propagation                        |
| `get_logger(name)`                            | Returns a module-level logger with JSON formatting                       |
| `log_with_props(logger, level, msg, **props)` | Logs with additional structured properties                               |
| `log_execution_time(logger, operation)`       | Context manager for timing code blocks                                   |

Log output goes to both console and rotating file handler at `backend/logs/datachat.log`.

### `backend/observability/tracing.py`

Integrates Langfuse and OpenTelemetry:

- **`@observe` decorator** — wraps functions to create Langfuse traces
- **`propagate_attributes()`** — propagates trace attributes across LangGraph nodes

### `backend/middleware/logging_middleware.py`

FastAPI middleware that:

1. Generates a `request_id` UUID for each incoming HTTP request
2. Stores it in `RequestContext` for propagation to all log entries
3. Times the full request lifecycle
4. Logs request/response metadata (method, path, status, duration)

### Log Correlation

Every log entry produced during a single HTTP request shares the same `request_id`, enabling end-to-end tracing from HTTP layer → LangGraph workflow → SQL agent → database query.

### Frontend Debug Logging

Emoji-prefixed `console.log` statements trace the full client-side rendering pipeline:

```
🚀 API call initiated
📡 Raw API response
🔄 processResponseData output
📨 onResponseReceived called
🧩 AIMessage rendering
🏗️ WidgetContainer processWidgetData
✅ Widget rendered
```

---

## 8. Features Implemented

### Feature 1: Widget Framework

Six widget types with a complete framework:

- **Registry** (`WidgetRegistry.js`) — pluggable component lookup
- **Container** (`WidgetContainer.js`) — error boundary + data normalisation
- **Direct renderers** — fast path for tables and aggregations
- **Fallback** — every response includes plain-text fallback string

### Feature 2: Backend Widget Type Detection

`answer_node` auto-detects the appropriate widget type from SQL result shape and query semantics. `WidgetFormatter` applies type-specific data transformation.

### Feature 3: Centralized Structured Logging

JSON-formatted logs with `request_id` correlation propagated across:

- HTTP middleware layer
- LangGraph workflow nodes
- SQL agent invocations
- Database queries

Integrated with Langfuse for LLM call tracing and OpenTelemetry for distributed tracing.

### Feature 4: API Response Normalisation

`processResponseData()` in `api.js` applies trust-API-first type resolution:

- Uses API-provided `widgetType` when present
- Falls back to data-shape inference only when `widgetType` is absent
- Handles stringified JSON in response fields

### Feature 5: Widget State Management

- `shouldReplaceWidget()` — controls widget replacement during transitions
- `lastWidgetType` tracking in `useSendMessage`
- `refreshTimestamp` signal in `WidgetContainer.componentDidUpdate`

### Feature 6: Direct Table Rendering Bypass

`DirectTableRenderer` and inline aggregation rendering in `AIMessage.js` provide a resilient fast path that works even when the full `WidgetContainer`/`WidgetRegistry` pipeline has issues.

### Feature 7: Interactive Widget Actions

`useWidgetActions` hook provides callbacks for:

- **Confirm** — sends confirmation action to backend
- **Select** — sends selected option to backend
- **Cancel** — dismisses interactive widget

### Feature 8: SQL Agent Answer Reuse

`answer_node` checks `sql_result.output` first. If the SQL agent already produced a final answer, it is reused directly — avoiding a redundant GPT-4 call and improving latency.

### Feature 9: Comprehensive Debug Logging

Emoji-prefixed `console.log` statements at every stage of the frontend rendering pipeline enable rapid visual debugging without external tools.

---

## 9. Issues Fixed

The following table documents all issues discovered and resolved during development, in order of discovery:

| #   | Problem                                                                | Root Cause                                                                                                                  | Fix Location                                                                                                              |
| --- | ---------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| 1   | SQL results not displayed                                              | Entire result object (including metadata) sent to GPT-4 instead of just the data                                            | `backend/graph/workflow.py` → `answer_node`                                                                               |
| 2   | `final_answer` empty despite agent output                              | Agent answer stored in `output` field not transferred to `final_answer`                                                     | `backend/graph/workflow.py` → `answer_node`                                                                               |
| 3   | `Object of type datetime is not JSON serializable`                     | MySQL datetime objects passed directly to `json.dumps()` without serialisation                                              | `backend/mcp_server.py` + `backend/json_encoder.py`                                                                       |
| 4   | `No module named 'backend'`                                            | Absolute import `from json_encoder import` used inside same-package file                                                    | `backend/widget_formatter.py` → changed to `from .json_encoder import`                                                    |
| 5   | `cannot access local variable 'WidgetFormatter'`                       | Import inside function body failed; variable still referenced after failed import                                           | `backend/graph/workflow.py` → moved to top-level `try/except` import block                                                |
| 6   | API responses never reached message list                               | `useSendMessage` and `useChatMessages` hooks disconnected; no callback wiring in `App.js`                                   | `frontend/src/App.js` → added `onResponseReceived` callback wiring                                                        |
| 7   | Widget type not recognised                                             | Backend set `metadata.widgetType` but left top-level `type` field empty                                                     | `AIMessage.js`, `messageFormatter.js`, `useSendMessage.js` — multi-layer type propagation added                           |
| 8   | `TableWidget` shows blank                                              | Array-row format (`row[0]`) vs. object-row format (`row["col"]`) mismatch; `headers` vs. `columns` field name inconsistency | `frontend/src/components/widgets/TableWidget.js` — dual-format cell rendering                                             |
| 9   | `ReferenceError: Cannot access 'finalClassName' before initialization` | `const` declaration used in `console.log` debug statement before declaration (Temporal Dead Zone)                           | `frontend/src/components/widgets/WidgetContainer.js` — hoisted declarations above debug block                             |
| 10  | Infinite `setState` re-render loop                                     | `freshData === true` condition in `componentDidUpdate` — boolean flag never reset, causing perpetual re-renders             | `frontend/src/components/widgets/WidgetContainer.js` — removed boolean flag; rely solely on `refreshTimestamp` diff       |
| 11  | Prop mutation broke React equality checks                              | `processedData.metadata = metadata` mutated the prop object in-place                                                        | `frontend/src/components/widgets/WidgetContainer.js` → changed to `processedData = { ...processedData, metadata }` spread |
| 12  | Aggregation value `0` not displayed                                    | `value \|\| count \|\| 0` — JavaScript `\|\|` operator treats `0` as falsy, always returning fallback                       | `frontend/src/components/messages/AIMessage.js` → changed to `value ?? count ?? 0` (nullish coalescing)                   |
| 13  | Aggregation rendered as table                                          | `processResponseData()` always inferred widget type from data shape, overriding the API-provided `widgetType`               | `frontend/src/services/api.js` → trust-API-first: infer only when `widgetType` is absent from response                    |

---

## 10. Architectural Decisions

### Decision 1: Trust-API-First Widget Type Resolution

**Decision:** Frontend infers widget type only when the backend omits it; never overrides an explicitly set type.

**Rationale:** Backend has full context (query semantics + data shape); frontend should defer to it. Inverting this caused aggregations to render as tables (Issue #13).

### Decision 2: Multi-Layer Type Safety

**Decision:** Four independent checkpoints each propagate `metadata.widgetType` → `type`:

1. `api.js` → `processResponseData()`
2. `useSendMessage.js` → response handler
3. `messageFormatter.js` → message assembly
4. `AIMessage.js` → render decision

**Rationale:** Defence-in-depth. If any single layer fails to propagate type, the next layer catches it. Eliminates single points of failure in widget type resolution.

### Decision 3: Direct Rendering Bypass for Core Widgets

**Decision:** Tables and aggregations have a fast path in `AIMessage.js`; `WidgetContainer`/`WidgetRegistry` handles everything else.

**Rationale:** Reduces pipeline failure surface for the two most common widget types. `DirectTableRenderer` is a resilient fallback that works even when the full registry pipeline has issues.

### Decision 4: Class Component for Error Boundary

**Decision:** `WidgetContainer` is implemented as a class component.

**Rationale:** React Error Boundaries (`getDerivedStateFromError` / `componentDidCatch`) require class components. This is a React architectural constraint, not a preference.

### Decision 5: Centralized `request_id` Correlation

**Decision:** A single UUID per HTTP request is generated in middleware and propagated to all log entries, LangGraph nodes, SQL agent logs, and Langfuse trace tags.

**Rationale:** Enables end-to-end request tracing in production. Without correlation IDs, diagnosing multi-hop failures (HTTP → workflow → agent → database) is impractical.

### Decision 6: Fallback-First Widget Design

**Decision:** Every widget response includes a `fallback` plain-text string.

**Rationale:** Guarantees the frontend always has something to render, even when widget parsing fails. Works in tandem with the Error Boundary to ensure users see a meaningful response regardless of widget render errors.

### Decision 7: Relative Python Imports with `try/except` Fallbacks

**Decision:** All intra-package imports use relative notation (`from .module import`); critical imports wrapped with `try/except` fallback class definitions.

**Rationale:** Prevents `No module named 'backend'` import errors (Issue #4). `try/except` fallbacks prevent cascading failures when imports fail — the workflow can still run with degraded widget formatting rather than crashing entirely.

### Decision 8: SQL Agent Answer Reuse

**Decision:** `answer_node` checks `sql_result.output` first; only invokes GPT-4 when the agent didn't already produce a final answer.

**Rationale:** Reduces latency and API cost. The SQL agent often produces a complete answer; calling GPT-4 again to reformat it is redundant.

### Decision 9: `refreshTimestamp` as Update Signal

**Decision:** `WidgetContainer.componentDidUpdate` uses timestamp comparison, not a boolean flag, to trigger re-processing.

**Rationale:** Boolean flags (`freshData === true`) don't reset between renders, causing infinite `setState` loops (Issue #10). A timestamp is unique per update and naturally prevents re-triggers.

### Decision 10: Phased Widget Framework Delivery

**Decision:** Widget framework delivered in phases: Foundation → Core Data Widgets → Interactive Widgets → Special Formats.

**Rationale:** Each phase delivers independently testable value. Avoids blocking on the full framework before any widgets are usable.

---

## 11. Open Gaps & Future Work

The following items are known gaps that have not yet been addressed:

| Gap                                        | Description                                                    | Impact                                          |
| ------------------------------------------ | -------------------------------------------------------------- | ----------------------------------------------- |
| No automated tests                         | No unit, integration, or E2E tests for backend or frontend     | High — regressions go undetected                |
| No authentication                          | API endpoints have no auth/authorization                       | High — unsuitable for production                |
| `AgentState.sql_result` type inconsistency | Type annotation says `dict` but sometimes receives `list`      | Medium — could cause runtime errors             |
| No MySQL connection pooling                | New connection created per query                               | Medium — performance and reliability under load |
| Incomplete widget test plan                | `docs/widget_test_plan.md` test cases blocked by import errors | Medium — coverage gaps unknown                  |
| No widget transition animations            | CSS classes prepared for transitions but unused                | Low — UX enhancement only                       |
| No JSON schema validation                  | Widget `data` payloads not validated against a schema          | Medium — malformed data silently breaks widgets |

---

## 12. Configuration & Environment

The DataChat application requires several environment variables to be properly configured for both development and production environments.

### Backend Environment Variables

| Variable Name                 | Description                                | Required | Default                      | Example                             |
| ----------------------------- | ------------------------------------------ | -------- | ---------------------------- | ----------------------------------- |
| `MYSQL_HOST`                  | MySQL database hostname                    | Yes      | -                            | `localhost` or `db.example.com`     |
| `MYSQL_PORT`                  | MySQL database port                        | Yes      | `3306`                       | `3306`                              |
| `MYSQL_USER`                  | MySQL database username                    | Yes      | -                            | `datachat_user`                     |
| `MYSQL_PASSWORD`              | MySQL database password                    | Yes      | -                            | `secure_password123`                |
| `MYSQL_DATABASE`              | MySQL database name                        | Yes      | -                            | `datachat_db`                       |
| `OPENAI_API_KEY`              | OpenAI API key for GPT-4 access            | Yes      | -                            | `sk-...`                            |
| `LOG_LEVEL`                   | Logging verbosity level                    | No       | `INFO`                       | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FILE_PATH`               | Path to log file                           | No       | `backend/logs/datachat.log`  | `/var/log/datachat.log`             |
| `LANGFUSE_API_KEY`            | Langfuse API key for tracing               | No       | -                            | `lfk_...`                           |
| `LANGFUSE_HOST`               | Langfuse host URL                          | No       | `https://cloud.langfuse.com` | `https://langfuse.yourdomain.com`   |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry collector endpoint           | No       | -                            | `http://localhost:4317`             |
| `MAX_QUERY_TIMEOUT`           | Maximum SQL query execution time (seconds) | No       | `30`                         | `60`                                |
| `ENABLE_SQL_VALIDATION`       | Enable SQL validation checks               | No       | `True`                       | `True`, `False`                     |

### Frontend Environment Variables

| Variable Name                         | Description                             | Required | Default | Example                                              |
| ------------------------------------- | --------------------------------------- | -------- | ------- | ---------------------------------------------------- |
| `REACT_APP_API_URL`                   | Backend API URL                         | Yes      | -       | `http://localhost:8000` or `https://api.example.com` |
| `REACT_APP_LOG_LEVEL`                 | Frontend console logging level          | No       | `info`  | `debug`, `info`, `warn`, `error`                     |
| `REACT_APP_ENABLE_WIDGET_TRANSITIONS` | Enable widget transition animations     | No       | `false` | `true`, `false`                                      |
| `REACT_APP_DEFAULT_WIDGET_TYPE`       | Fallback widget type if detection fails | No       | `text`  | `text`, `table`                                      |

### Configuration Files

| File              | Purpose                           | Location           |
| ----------------- | --------------------------------- | ------------------ |
| `.env`            | Development environment variables | Project root       |
| `.env.production` | Production environment variables  | Project root       |
| `frontend/.env`   | Frontend-specific variables       | Frontend directory |

---

## 13. How to Run

### Backend Setup and Startup

```bash
# Install backend dependencies
pip install -r requirements.txt

# Set required environment variables (see Section 12)
export MYSQL_HOST=localhost
export MYSQL_USER=root
export MYSQL_PASSWORD=password
export MYSQL_DATABASE=datachat_db
export OPENAI_API_KEY=your_openai_api_key

# Start the FastAPI server
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup and Startup

```bash
# Install frontend dependencies
cd frontend
npm install

# Set API URL environment variable
echo "REACT_APP_API_URL=http://localhost:8000" > .env

# Start the React development server
npm start
```

---

## 14. How to Add a New Widget Type

Follow this step-by-step checklist to add a new widget type to the DataChat application:

### Backend Changes

1. **Update `widget_formatter.py`**:
   - Add a new format method (e.g., `format_as_new_widget_type()`)
   - Define the expected data structure and validation logic
   - Implement the formatting logic to transform SQL results into the widget format

2. **Update `workflow.py`**:
   - Add detection logic in `answer_node` to identify when to use the new widget type
   - Add keywords or data shape patterns that should trigger this widget type

3. **Update API response schema**:
   - Document the new widget type's response format in API documentation
   - Ensure the response includes the required `type`, `data`, `metadata`, and `fallback` fields

### Frontend Changes

1. **Create the widget component**:
   - Create a new file in `frontend/src/components/widgets/` (e.g., `NewWidget.js`)
   - Implement the React component with appropriate props validation
   - Add CSS styling (either inline or in a separate `.css` file)

2. **Register the widget**:
   - Update `WidgetRegistry.js` to include the new widget type:
     ```javascript
     import NewWidget from "./NewWidget";
     // ...
     registerWidget("new_widget_type", NewWidget);
     ```

3. **Update widget detection**:
   - If using direct rendering, update `AIMessage.js` to handle the new widget type
   - Otherwise, the standard `WidgetContainer` → `WidgetRegistry` path will work automatically

4. **Add fallback handling**:
   - Ensure `messageFormatter.js` can handle the new widget type's data structure
   - Update any type inference logic in `api.js` if needed

### Testing

1. Create a test query that should trigger the new widget type
2. Verify the backend correctly detects and formats the response
3. Verify the frontend correctly renders the widget
4. Test error cases and fallback behavior

### Documentation

1. Update this documentation with:
   - The new widget type's purpose and use cases
   - The expected data structure
   - Example API response format
   - Any special considerations or limitations

---

## Appendix: File Reference Index

### Backend Files

| File                                       | Role                                                                  |
| ------------------------------------------ | --------------------------------------------------------------------- |
| `backend/main.py`                          | FastAPI app, endpoint definitions                                     |
| `backend/agents/sql_agent.py`              | LangChain SQL agent with `get_schema` + `execute_sql` tools           |
| `backend/graph/workflow.py`                | LangGraph StateGraph: `sql_node → validation_node → answer_node`      |
| `backend/mcp_server.py`                    | MySQL abstraction: `execute_query()` + `get_schema()`                 |
| `backend/widget_formatter.py`              | `WidgetFormatter` class with per-type format methods                  |
| `backend/json_encoder.py`                  | `CustomJsonEncoder` / `DateTimeEncoder` for datetime serialisation    |
| `backend/guardrails_validators.py`         | Pydantic `QueryRequest` with SQL injection prevention                 |
| `backend/observability/logging.py`         | `JsonFormatter`, `RequestContext`, `get_logger()`, `log_with_props()` |
| `backend/observability/tracing.py`         | Langfuse + OpenTelemetry integration                                  |
| `backend/middleware/logging_middleware.py` | FastAPI middleware for `request_id` generation and request timing     |

### Frontend Files

| File                                                     | Role                                                          |
| -------------------------------------------------------- | ------------------------------------------------------------- |
| `frontend/src/App.js`                                    | Root component; hook wiring via `onResponseReceived` callback |
| `frontend/src/components/messages/AIMessage.js`          | Widget type detection and rendering (direct + standard paths) |
| `frontend/src/components/widgets/WidgetContainer.js`     | Class component; Error Boundary + data normalisation          |
| `frontend/src/components/widgets/WidgetRegistry.js`      | Widget type → component registry                              |
| `frontend/src/components/widgets/TableWidget.js`         | Table renderer (dual array/object row format support)         |
| `frontend/src/components/widgets/AggregationWidget.js`   | Single-value aggregation renderer                             |
| `frontend/src/components/widgets/ComparisonWidget.js`    | Side-by-side value comparison renderer                        |
| `frontend/src/components/widgets/ConfirmationWidget.js`  | Yes/No confirmation prompt                                    |
| `frontend/src/components/widgets/OptionsWidget.js`       | Multi-choice option selector                                  |
| `frontend/src/components/widgets/TextWidget.js`          | Plain-text fallback renderer                                  |
| `frontend/src/components/widgets/DirectTableRenderer.js` | Resilient direct table renderer bypassing full pipeline       |
| `frontend/src/components/hooks/useSendMessage.js`        | API call hook with `lastWidgetType` tracking                  |
| `frontend/src/components/hooks/useChatMessages.js`       | Chat message state management                                 |
| `frontend/src/components/hooks/useWidgetActions.js`      | Interactive widget action callbacks                           |
| `frontend/src/services/api.js`                           | HTTP client with trust-API-first `processResponseData()`      |
| `frontend/src/utils/messageFormatter.js`                 | API response → message object parser                          |
| `frontend/src/utils/widgetUtils.js`                      | `shouldReplaceWidget()` transition logic                      |

---

_Document generated from Phase 1 comprehensive project analysis and Phase 3 Boomerang Pipeline. Last updated: 2026-03-20._
