# Analysis Agent — Technical Design

> **Status:** Draft · March 2026  
> **Pattern:** Option B (Python class wrapper) — structured for easy migration to Option C (true MCP protocol)

---

## 1. Architecture Overview

The analysis agent is a second ReAct agent that lives alongside the existing [`SQLAgent`](../backend/agents/sql_agent.py). A new `query_router` node at the front of the LangGraph workflow classifies each incoming user query as either **"sql"** (retrieval / counting) or **"analytics"** (statistics, trends, outliers, charts) and routes it accordingly.

```mermaid
flowchart TD
    UI[React Frontend] -->|POST /query| QE[/query endpoint]
    UI -->|POST /analyze| AE[/analyze endpoint]

    QE --> TR[trace_agent_run]
    AE --> TAR[trace_analysis_run]

    TR --> WF[LangGraph Workflow]
    TAR --> WF

    subgraph WF[LangGraph Workflow — graph/workflow.py]
        EP([ENTRY]) --> QR[query_router node]
        QR -- intent = sql --> SN[sql_node]
        QR -- intent = analytics --> AN[analysis_node]
        SN --> VN[validation_node]
        AN --> AnswN[answer_node]
        VN --> AnswN
        AnswN --> FBN[feedback_node]
        FBN -- accept --> END2([END])
        FBN -- improve --> IAN[improve_answer_node]
        FBN -- fail --> EEN[error_end_node]
        IAN --> FBN
        EEN --> END3([END])
    end

    subgraph SQL_Stack[SQL Stack - unchanged]
        SN --> SQLA[SQLAgent]
        SQLA --> MCP[mcp_server.py]
        MCP --> DB[(MySQL)]
    end

    subgraph Analytics_Stack[Analytics Stack - NEW]
        AN --> ANLA[AnalysisAgent]
        ANLA --> AMCP[analytics_mcp_server.py]
        AMCP --> AF[analytics/ pure functions]
        ANLA --> MCP
    end

    subgraph Analytics_Funcs[analytics/ - pure functions]
        AF --> STAT[statistics.py]
        AF --> TR2[trends.py]
        AF --> OUT[outliers.py]
        AF --> CC[chart_config.py]
    end
```

### Key design decisions

| Decision                                                   | Rationale                                        |
| ---------------------------------------------------------- | ------------------------------------------------ |
| `query_router` as new LangGraph entry point                | Single clean door; SQL path is unchanged         |
| `AnalysisAgent` also has access to `mcp_server` tools      | Analysis requires querying raw data first        |
| Pure functions in `analytics/` contain zero LangChain code | Future MCP server exposes them directly as tools |
| `analytics_mcp_server.py` mirrors `mcp_server.py` exactly  | Drop-in swap when migrating to Option C          |
| New `AgentState` fields: `intent`, `analysis_result`       | Clean state separation; backwards-compatible     |

---

## 2. Database Schema (Reference)

The MySQL database has five tables used throughout the design:

```
categories(id, name, description, created_at)
products(id, name, category_id, price, cost, stock_quantity, is_active, created_at)
customers(id, name, email, country, state, city, registration_date, customer_segment, lifetime_value, created_at)
orders(id, customer_id, order_date, status, total_amount, shipping_cost, tax_amount, discount_amount, payment_method, created_at, completed_at)
order_items(id, order_id, product_id, quantity, unit_price, discount_percent, subtotal, created_at)
```

### Enhanced Schema Descriptor (for LLM context)

The `AnalysisAgent` system prompt uses a richer schema descriptor that goes beyond `DESCRIBE table`. The descriptor captures:

```python
SCHEMA_DESCRIPTOR = {
    "customers": {
        "numeric_cols": ["lifetime_value"],
        "categorical_cols": ["country", "state", "city", "customer_segment"],
        "temporal_cols": ["registration_date", "created_at"],
        "pk": "id",
        "description": "One row per customer. customer_segment: Premium|Regular|Budget.",
    },
    "orders": {
        "numeric_cols": ["total_amount", "shipping_cost", "tax_amount", "discount_amount"],
        "categorical_cols": ["status", "payment_method"],
        "temporal_cols": ["order_date", "created_at", "completed_at"],
        "pk": "id",
        "fk": {"customer_id": "customers.id"},
        "description": "One row per order. status: pending|completed|cancelled|refunded.",
    },
    "order_items": {
        "numeric_cols": ["quantity", "unit_price", "discount_percent", "subtotal"],
        "categorical_cols": [],
        "temporal_cols": ["created_at"],
        "pk": "id",
        "fk": {"order_id": "orders.id", "product_id": "products.id"},
        "description": "Line-item detail. Use JOIN with orders for date-based analysis.",
    },
    "products": {
        "numeric_cols": ["price", "cost", "stock_quantity"],
        "categorical_cols": ["is_active"],
        "temporal_cols": ["created_at"],
        "pk": "id",
        "fk": {"category_id": "categories.id"},
        "description": "Margin = price - cost. Filter is_active=1 for live catalog.",
    },
    "categories": {
        "numeric_cols": [],
        "categorical_cols": ["name"],
        "temporal_cols": ["created_at"],
        "pk": "id",
        "description": "Top-level grouping for products.",
    },
}
```

---

## 3. New Component Specifications

### 3.1 `backend/analytics/__init__.py`

Packages all pure analytics functions as a clean public API. No LangChain imports.

```python
"""
analytics/
Pure analytics functions — no LangChain, no DB dependencies.
These functions operate on plain Python lists of dicts (SQL query results).

MCP-READY: Each public function in this package maps 1-to-1 to an MCP tool
definition when migrating from Option B to Option C. The tool name is the
function name; the tool input schema is derived from the function signature.
"""

from analytics.statistics import compute_descriptive_stats, compute_correlation
from analytics.trends import compute_trend, compute_forecast
from analytics.outliers import detect_outliers_iqr, detect_outliers_zscore
from analytics.chart_config import generate_chart_config

__all__ = [
    "compute_descriptive_stats",
    "compute_correlation",
    "compute_trend",
    "compute_forecast",
    "detect_outliers_iqr",
    "detect_outliers_zscore",
    "generate_chart_config",
]
```

---

### 3.2 `backend/analytics/statistics.py`

```python
"""
Pure statistical analysis functions.

MCP-READY: Each function becomes an MCP tool named after the function.
"""
from typing import List, Dict, Any, Optional
import statistics as _stats
import math

def compute_descriptive_stats(
    data: List[Dict[str, Any]],
    column: str,
    group_by: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compute descriptive statistics for a numeric column.

    Args:
        data:     List of dicts — raw SQL result rows.
        column:   Name of the numeric column to analyse.
        group_by: Optional categorical column to stratify results.

    Returns:
        {
          "column": "total_amount",
          "group_by": null | "customer_segment",
          "overall": {
            "count": 120, "mean": 145.3, "median": 132.0,
            "std": 42.1, "min": 12.5, "max": 899.0,
            "p25": 98.0, "p75": 188.5
          },
          "groups": {           # only when group_by is provided
            "Premium": {...},
            "Regular": {...}
          }
        }
    """
    ...

def compute_correlation(
    data: List[Dict[str, Any]],
    col_x: str,
    col_y: str,
) -> Dict[str, Any]:
    """
    Compute Pearson correlation between two numeric columns.

    Returns:
        {
          "col_x": "price",
          "col_y": "subtotal",
          "r": 0.87,
          "r_squared": 0.76,
          "interpretation": "strong positive",
          "n": 340
        }
    """
    ...
```

---

### 3.3 `backend/analytics/trends.py`

```python
"""
Time-series trend and forecasting functions.

MCP-READY: Each function becomes an MCP tool.
"""
from typing import List, Dict, Any

def compute_trend(
    data: List[Dict[str, Any]],
    date_col: str,
    value_col: str,
    period: str = "month",          # "day" | "week" | "month" | "quarter"
) -> Dict[str, Any]:
    """
    Fit a linear trend to time-series data using least-squares regression.

    Args:
        data:       Raw SQL result rows that include a date column and value column.
        date_col:   Column name carrying date/datetime strings.
        value_col:  Numeric column to trend.
        period:     Aggregation granularity.

    Returns:
        {
          "date_col": "order_date",
          "value_col": "total_amount",
          "period": "month",
          "direction": "up" | "down" | "flat",
          "slope_per_period": 1234.5,
          "r_squared": 0.91,
          "series": [                      # aggregated, sorted
            {"period": "2025-01", "value": 12300.0},
            ...
          ]
        }
    """
    ...

def compute_forecast(
    data: List[Dict[str, Any]],
    date_col: str,
    value_col: str,
    periods_ahead: int = 3,
    period: str = "month",
) -> Dict[str, Any]:
    """
    Extend a linear trend `periods_ahead` steps into the future.

    Returns:
        {
          "historical": [...],            # same format as compute_trend series
          "forecast": [
            {"period": "2026-04", "value": 15800.0, "is_forecast": true},
            ...
          ],
          "method": "linear_regression",
          "confidence": "low" | "medium" | "high"
        }
    """
    ...
```

---

### 3.4 `backend/analytics/outliers.py`

```python
"""
Outlier detection functions.

MCP-READY: Each function becomes an MCP tool.
"""
from typing import List, Dict, Any

def detect_outliers_iqr(
    data: List[Dict[str, Any]],
    column: str,
    id_col: str = "id",
) -> Dict[str, Any]:
    """
    Detect outliers using the IQR (interquartile range) method.
    Outlier threshold: value < Q1 - 1.5*IQR  OR  value > Q3 + 1.5*IQR

    Returns:
        {
          "column": "total_amount",
          "method": "iqr",
          "q1": 98.0, "q3": 188.5, "iqr": 90.5,
          "lower_fence": -37.75, "upper_fence": 324.25,
          "outlier_count": 5,
          "outlier_pct": 4.2,
          "outliers": [
            {"id": 42, "value": 899.0, "direction": "high"},
            ...
          ]
        }
    """
    ...

def detect_outliers_zscore(
    data: List[Dict[str, Any]],
    column: str,
    id_col: str = "id",
    threshold: float = 3.0,
) -> Dict[str, Any]:
    """
    Detect outliers using z-score (number of standard deviations from mean).

    Returns:
        {
          "column": "total_amount",
          "method": "zscore",
          "mean": 145.3, "std": 42.1, "threshold": 3.0,
          "outlier_count": 3,
          "outlier_pct": 2.5,
          "outliers": [
            {"id": 87, "value": 271.6, "z_score": 3.05, "direction": "high"},
            ...
          ]
        }
    """
    ...
```

---

### 3.5 `backend/analytics/chart_config.py`

```python
"""
Chart configuration generator.
Produces Plotly-compatible JSON that the frontend can render directly.

MCP-READY: becomes an MCP tool named generate_chart_config.
"""
from typing import List, Dict, Any, Optional

SUPPORTED_CHART_TYPES = ("bar", "line", "scatter", "pie", "histogram", "box")

def generate_chart_config(
    data: List[Dict[str, Any]],
    chart_type: str,                    # one of SUPPORTED_CHART_TYPES
    x_col: str,
    y_col: str,
    title: Optional[str] = None,
    color_col: Optional[str] = None,    # column to use for series color grouping
    orientation: str = "v",             # "v" | "h" for bar charts
) -> Dict[str, Any]:
    """
    Generate a Plotly chart configuration dict.

    Returns a structure compatible with Plotly React component:
        {
          "chart_type": "bar",
          "title": "Monthly Revenue",
          "plotly": {
            "data": [...],        # Plotly traces
            "layout": {...}       # Plotly layout object
          },
          "fallback_table": [     # raw data for graceful degradation
            {"x_col": "2025-01", "y_col": 12300.0},
            ...
          ]
        }
    """
    ...
```

---

### 3.6 `backend/analytics_mcp_server.py`

Mirrors the shape and conventions of the existing [`mcp_server.py`](../backend/mcp_server.py). Contains **no business logic** — purely delegates to `analytics/` functions and wraps results with error handling.

```python
"""
AnalyticsMCPServer
==================
Thin wrapper around the analytics/ pure-function package.
Mirrors the ChatWithDataMCPServer pattern in mcp_server.py.

Option B now: Python class consumed by analysis_agent.py
Option C later: Replace this file with a proper MCP server that registers
                the same method signatures as @tool definitions.

MCP-MIGRATION GUIDE:
  Each public method below maps to one MCP tool:
    self.compute_stats(...)    → @mcp.tool("compute_stats")
    self.compute_trend(...)    → @mcp.tool("compute_trend")
    self.compute_forecast(...) → @mcp.tool("compute_forecast")
    self.detect_outliers(...)  → @mcp.tool("detect_outliers")
    self.generate_chart(...)   → @mcp.tool("generate_chart")
"""

from typing import List, Dict, Any, Optional
from analytics import (
    compute_descriptive_stats,
    compute_correlation,
    compute_trend,
    compute_forecast,
    detect_outliers_iqr,
    detect_outliers_zscore,
    generate_chart_config,
)
from observability.logging import get_logger, log_with_props, log_execution_time, RequestContext
import time

logger = get_logger(__name__)


class AnalyticsMCPServer:
    """
    Tool gateway for analytics operations.
    Instantiate once (singleton at module level) and reuse across requests.
    All methods are thread-safe because they operate on caller-supplied data
    (no mutable shared state).
    """

    # ------------------------------------------------------------------
    # Public MCP tools
    # ------------------------------------------------------------------

    def compute_stats(
        self,
        data: List[Dict[str, Any]],
        column: str,
        group_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        MCP Tool: Compute descriptive statistics for a numeric column.
        Returns: {success, result, error}
        """
        ...

    def compute_trend(
        self,
        data: List[Dict[str, Any]],
        date_col: str,
        value_col: str,
        period: str = "month",
    ) -> Dict[str, Any]:
        """
        MCP Tool: Fit a linear trend to time-series data.
        Returns: {success, result, error}
        """
        ...

    def compute_forecast(
        self,
        data: List[Dict[str, Any]],
        date_col: str,
        value_col: str,
        periods_ahead: int = 3,
        period: str = "month",
    ) -> Dict[str, Any]:
        """
        MCP Tool: Forecast future values by extending a linear trend.
        Returns: {success, result, error}
        """
        ...

    def detect_outliers(
        self,
        data: List[Dict[str, Any]],
        column: str,
        method: str = "iqr",        # "iqr" | "zscore"
        id_col: str = "id",
        zscore_threshold: float = 3.0,
    ) -> Dict[str, Any]:
        """
        MCP Tool: Detect outlier rows using IQR or z-score method.
        Returns: {success, result, error}
        """
        ...

    def generate_chart(
        self,
        data: List[Dict[str, Any]],
        chart_type: str,
        x_col: str,
        y_col: str,
        title: Optional[str] = None,
        color_col: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        MCP Tool: Generate a Plotly chart configuration from data.
        Returns: {success, result, error}
        """
        ...


# Singleton — same pattern as mcp_server.py
analytics_mcp_server = AnalyticsMCPServer()
```

---

### 3.7 `backend/agents/analysis_agent.py`

A ReAct agent that mirrors [`sql_agent.py`](../backend/agents/sql_agent.py) but with a richer tool belt: it can **query the DB** (via `mcp_server`) **and run analytics** (via `analytics_mcp_server`).

```python
"""
AnalysisAgent
=============
ReAct agent for statistical analysis, trend detection, outlier identification,
and chart generation. Uses both database MCP tools and analytics MCP tools.

Tool execution order (typical):
  1. get_schema        → understand columns + types
  2. execute_sql       → fetch raw data (always a SELECT with useful columns)
  3. compute_stats     → compute statistics on fetched data
  4. compute_trend     → detect time-series trends
  5. detect_outliers   → flag anomalies
  6. generate_chart    → produce Plotly config for frontend rendering
"""

from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from langgraph.prebuilt import create_react_agent
from mcp_server import mcp_server
from analytics_mcp_server import analytics_mcp_server
from typing import Dict, Any
import json
import time
from observability.logging import get_logger, log_with_props, log_execution_time, RequestContext

logger = get_logger(__name__)


ANALYSIS_SYSTEM_PROMPT = """You are a data analysis expert. Your job is to answer analytical
questions about an e-commerce database by querying data and computing statistics.

DATABASE SCHEMA:
  categories(id, name, description, created_at)
  products(id, name, category_id, price, cost, stock_quantity, is_active, created_at)
    - numeric: price, cost, stock_quantity
    - profit_margin = price - cost
  customers(id, name, email, country, state, city, registration_date,
            customer_segment, lifetime_value, created_at)
    - numeric: lifetime_value
    - categorical: customer_segment (Premium|Regular|Budget), country
  orders(id, customer_id, order_date, status, total_amount, shipping_cost,
         tax_amount, discount_amount, payment_method, created_at, completed_at)
    - numeric: total_amount, shipping_cost, tax_amount, discount_amount
    - categorical: status (pending|completed|cancelled|refunded), payment_method
  order_items(id, order_id, product_id, quantity, unit_price, discount_percent, subtotal)
    - numeric: quantity, unit_price, discount_percent, subtotal

ANALYTICAL WORKFLOW:
  1. Call get_schema to confirm columns when uncertain.
  2. Call execute_sql with a SELECT that retrieves the data you need — always include
     an id column and filter to relevant rows (use WHERE status='completed' for revenue).
  3. Call one or more analytics tools on the returned rows:
     - compute_stats   → descriptive statistics for a numeric column
     - compute_trend   → time-series trend + direction
     - compute_forecast → future projections
     - detect_outliers → anomaly rows
     - generate_chart  → Plotly chart config
  4. Synthesise all tool results into a clear natural-language answer that includes
     key numbers, trends, and any chart config.

RULES:
  - Never invent numbers; always call execute_sql first.
  - Always pass the full list of SQL result rows to analytics tools — do not truncate.
  - Include the chart configuration JSON in your final answer so the frontend can render it.
  - If a query returns 0 rows, say so clearly and suggest an alternative."""


class AnalysisAgent:
    """
    ReAct agent for analytical queries.
    Exposes the same .run(query) interface as SQLAgent.
    """

    def __init__(self):
        ...

    def _create_tools(self) -> list:
        """
        Create all tools: 2 DB tools + 5 analytics tools.
        Each tool wrapper follows the logging pattern from sql_agent.py.
        """
        tools = []

        # --- DB tools (shared with SQLAgent) ---
        # get_schema(table: str) → JSON
        # execute_sql(query: str) → JSON

        # --- Analytics tools ---
        # compute_stats(data_json: str, column: str, group_by: str) → JSON
        # compute_trend(data_json: str, date_col: str, value_col: str, period: str) → JSON
        # compute_forecast(data_json: str, date_col: str, value_col: str, periods_ahead: int) → JSON
        # detect_outliers(data_json: str, column: str, method: str) → JSON
        # generate_chart(data_json: str, chart_type: str, x_col: str, y_col: str, title: str) → JSON

        return tools

    def run(self, query: str) -> Dict[str, Any]:
        """
        Execute an analytical natural language query.
        Returns: {success, output, analysis_data, chart_config, full_trace}
        """
        ...
```

**Tool argument strategy:** Because LangGraph's `create_react_agent` passes tool inputs as strings, analytics tools accept `data_json: str` (a JSON-serialised list of dicts from `execute_sql`) and parse it internally. This avoids complex multi-argument parsing.

---

### 3.8 Extensions to `backend/graph/workflow.py`

#### 3.8.1 Extended `AgentState`

```python
class AgentState(TypedDict):
    """State shared between all nodes — backwards-compatible extension"""
    query: str
    intent: str                                                      # NEW: "sql" | "analytics"
    sql_result: Annotated[List[Dict[str, Any]], operator.add]
    analysis_result: Annotated[List[Dict[str, Any]], operator.add]  # NEW
    validation_result: Annotated[List[Dict[str, Any]], operator.add]
    final_answer: str
    errors: Annotated[List[Dict[str, Any]], operator.add]
    feedback_score: int
    feedback_message: str
    feedback_attempt: int
    feedback_exceeded: bool
```

#### 3.8.2 `query_router` node (intent classification)

```python
def query_router_node(state: AgentState) -> AgentState:
    """
    Classify the user query as 'sql' (retrieval) or 'analytics' (analysis).
    Uses a fast gpt-4o-mini LLM call with a structured prompt.
    Falls back to 'sql' on any error.
    """
    ROUTER_PROMPT = """Classify the user's question as either "sql" or "analytics".

"sql"       → simple data retrieval, counting, listing, looking up records
"analytics" → statistics, trends, forecasts, outliers, correlations, charts,
              comparisons over time, averages across segments

Return ONLY one word: sql  OR  analytics

Question: {query}"""
    ...
```

#### 3.8.3 `analysis_node`

```python
def analysis_node(state: AgentState) -> AgentState:
    """Analysis Agent Node — mirrors sql_node"""
    from agents.analysis_agent import AnalysisAgent
    agent = AnalysisAgent()
    result = agent.run(state['query'])
    return {
        **state,
        'analysis_result': state.get('analysis_result', []) + [result],
    }
```

#### 3.8.4 Updated `answer_node`

`answer_node` must be updated to pull from **either** `sql_result` or `analysis_result` (whichever is populated) based on `state['intent']`. Analysis results may also carry a `chart_config` key that maps to a new `"chart"` widget type.

#### 3.8.5 Updated `create_workflow()`

```python
def create_workflow():
    graph = StateGraph(AgentState)

    # Nodes
    graph.add_node('query_router', query_router_node)  # NEW — entry point
    graph.add_node('sql_agent', sql_node)
    graph.add_node('analysis_agent', analysis_node)    # NEW
    graph.add_node('validator', validation_node)
    graph.add_node('answer', answer_node)
    graph.add_node('feedback', feedback_node)
    graph.add_node('improve_answer', improve_answer_node)
    graph.add_node('error_end', error_end_node)

    # Entry
    graph.set_entry_point('query_router')

    # Intent routing
    graph.add_conditional_edges(
        'query_router',
        lambda state: state.get('intent', 'sql'),
        {
            'sql':       'sql_agent',
            'analytics': 'analysis_agent',
        }
    )

    # SQL branch
    graph.add_edge('sql_agent', 'validator')
    graph.add_edge('validator', 'answer')

    # Analytics branch
    graph.add_edge('analysis_agent', 'answer')          # skips validation node

    # Shared tail
    graph.add_edge('answer', 'feedback')
    graph.add_conditional_edges('feedback', feedback_router,
        {'accept': END, 'improve': 'improve_answer', 'fail': 'error_end'})
    graph.add_edge('improve_answer', 'feedback')
    graph.add_edge('error_end', END)

    return graph.compile().with_config({"callbacks": [langfuse_handler]})
```

---

### 3.9 Extensions to `backend/main.py`

#### New Pydantic models

```python
class AnalyzeRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None  # optional UI context (table, field filters)

class AnalyzeResponse(BaseModel):
    success: bool
    answer: Union[str, Dict[str, Any]] = None
    chart_config: Optional[Dict[str, Any]] = None
    analysis_metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    trace_id: Optional[str] = None
```

#### New `/analyze` endpoint

```python
@app.post("/analyze", response_model=AnalyzeResponse)
def handle_analyze(request: AnalyzeRequest):
    """
    Dedicated endpoint for analytical queries — bypasses general query guardrails.
    Routes directly into the LangGraph workflow with intent pre-set to 'analytics'.
    Used by internal UI screens (dashboards, report builders).
    """
    request_id = RequestContext.get_request_id()
    try:
        answer = trace_analysis_run(request.query)          # new tracer wrapper
        final = answer.get('final_answer', {})
        return AnalyzeResponse(
            success=True,
            answer=final,
            chart_config=answer.get('chart_config'),
            analysis_metadata=answer.get('analysis_metadata'),
            trace_id=request_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**`trace_analysis_run`** lives in [`observability/tracing.py`](../backend/observability/tracing.py) — same `@observe` pattern as `trace_agent_run` but pre-sets `intent = "analytics"` in the initial state and tags the Langfuse trace accordingly.

---

## 4. Widget Extension: `"chart"` type

The frontend `WidgetRegistry` will need a new `ChartWidget` component. The backend `WidgetFormatter` will need a `format_as_chart()` method:

```python
# widget_formatter.py addition
@staticmethod
def format_as_chart(data: Any, query: str = "", metadata: Optional[Dict] = None) -> Dict:
    """
    Format a Plotly chart configuration as a chart widget.
    data must be the dict returned by generate_chart_config().
    """
    return {
        "type": "chart",
        "data": data.get("plotly", {}),
        "title": data.get("title", ""),
        "fallback_table": data.get("fallback_table", []),
        "fallback": f"Chart: {data.get('title', query)}",
        "query": query,
    }
```

---

## 5. MCP Migration Path (Option B → Option C)

The design is structured so that migration requires **only two steps**:

### Step 1 — Replace `analytics_mcp_server.py`

Convert the class to a proper MCP server by replacing method decorators:

```python
# BEFORE (Option B)
class AnalyticsMCPServer:
    def compute_stats(self, data, column, group_by=None):
        ...

# AFTER (Option C)
from mcp.server import Server
from mcp.types import Tool

server = Server("analytics")

@server.tool("compute_stats")
async def compute_stats(data: list, column: str, group_by: str = None):
    return compute_descriptive_stats(data, column, group_by)
    # Pure function in analytics/ unchanged!
```

### Step 2 — Update `analysis_agent.py` tool binding

```python
# BEFORE (Option B) — direct method call
Tool(name="compute_stats", func=analytics_mcp_server.compute_stats, ...)

# AFTER (Option C) — MCP client call
from langchain_mcp_adapters.client import MultiServerMCPClient
mcp_tools = await client.get_tools()  # replaces _create_tools()
```

The `analytics/` pure functions are **never changed** in either step.

---

## 6. Pydantic Schema Definitions for Enhanced SQL Querying

These Pydantic models are used for structured output from the `query_router` and for validating `AnalysisAgent` tool call arguments:

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal, List

class QueryIntent(BaseModel):
    intent: Literal["sql", "analytics"]
    confidence: float = Field(ge=0.0, le=1.0)
    analysis_types: List[Literal[
        "descriptive_stats", "correlation", "trend",
        "forecast", "outlier", "chart"
    ]] = []
    primary_table: Optional[str] = None
    required_columns: List[str] = []

class SQLQueryPlan(BaseModel):
    """Structured SQL query plan produced by the router/planner"""
    sql: str
    purpose: str
    expected_columns: List[str]
    date_col: Optional[str] = None
    value_col: Optional[str] = None
    group_col: Optional[str] = None

class AnalyticsToolCall(BaseModel):
    """Validated arguments for an analytics tool call"""
    tool_name: Literal[
        "compute_stats", "compute_trend", "compute_forecast",
        "detect_outliers", "generate_chart"
    ]
    column: Optional[str] = None
    group_by: Optional[str] = None
    date_col: Optional[str] = None
    value_col: Optional[str] = None
    method: Optional[Literal["iqr", "zscore"]] = None
    chart_type: Optional[Literal["bar", "line", "scatter", "pie", "histogram", "box"]] = None
    periods_ahead: int = 3
    period: Literal["day", "week", "month", "quarter"] = "month"
```

---

## 7. File-by-file Summary

| File                                                                                                        | Status        | Role                                                |
| ----------------------------------------------------------------------------------------------------------- | ------------- | --------------------------------------------------- |
| [`backend/mcp_server.py`](../backend/mcp_server.py)                                                         | **Unchanged** | DB operations                                       |
| [`backend/analytics/__init__.py`](../backend/analytics/__init__.py)                                         | **New**       | Public API export                                   |
| [`backend/analytics/statistics.py`](../backend/analytics/statistics.py)                                     | **New**       | `compute_descriptive_stats`, `compute_correlation`  |
| [`backend/analytics/trends.py`](../backend/analytics/trends.py)                                             | **New**       | `compute_trend`, `compute_forecast`                 |
| [`backend/analytics/outliers.py`](../backend/analytics/outliers.py)                                         | **New**       | `detect_outliers_iqr`, `detect_outliers_zscore`     |
| [`backend/analytics/chart_config.py`](../backend/analytics/chart_config.py)                                 | **New**       | `generate_chart_config`                             |
| [`backend/analytics_mcp_server.py`](../backend/analytics_mcp_server.py)                                     | **New**       | Thin wrapper; Option B→C migration point            |
| [`backend/agents/analysis_agent.py`](../backend/agents/analysis_agent.py)                                   | **New**       | ReAct agent with 7 tools                            |
| [`backend/graph/workflow.py`](../backend/graph/workflow.py)                                                 | **Extended**  | `query_router_node`, `analysis_node`, updated state |
| [`backend/main.py`](../backend/main.py)                                                                     | **Extended**  | `POST /analyze` endpoint                            |
| [`backend/widget_formatter.py`](../backend/widget_formatter.py)                                             | **Extended**  | `format_as_chart()` method                          |
| [`backend/observability/tracing.py`](../backend/observability/tracing.py)                                   | **Extended**  | `trace_analysis_run()`                              |
| [`frontend/src/components/widgets/ChartWidget.js`](../frontend/src/components/widgets/ChartWidget.js)       | **New**       | Plotly React chart renderer                         |
| [`frontend/src/components/widgets/WidgetRegistry.js`](../frontend/src/components/widgets/WidgetRegistry.js) | **Extended**  | Register `ChartWidget`                              |

---

## 8. Dependencies to Add to `requirements.txt`

```
scipy>=1.12          # statistics / linear regression
numpy>=1.26
plotly>=5.20         # chart_config serialisation (server-side)
```

Frontend:

```
plotly.js            # chart rendering (already in package.json if not present)
react-plotly.js      # React wrapper
```
