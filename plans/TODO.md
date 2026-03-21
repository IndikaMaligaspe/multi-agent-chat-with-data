# Analysis Agent — Implementation TODO

> Reference: [`plans/analysis_agent_design.md`](./analysis_agent_design.md)
> Pattern: **Option B — plain Python class wrapper** (no Anthropic MCP SDK)
> Future cycle: a dedicated sprint will migrate Option B → proper Anthropic MCP server
> Base branch: `feature/analyzer_agent` (already created)

---

## Git Branch & Sprint Strategy

Each phase is one **sprint**. Create a branch off `feature/analyzer_agent` at the start of each sprint and merge back via PR before starting the next.

| Phase      | Sprint branch                       | Goal                                               |
| ---------- | ----------------------------------- | -------------------------------------------------- |
| 0          | `feature/phase-0-setup`             | Dependencies, tooling verified                     |
| 1          | `feature/phase-1-pure-analytics`    | All 5 pure-function files + unit tests green       |
| 2          | `feature/phase-2-analytics-wrapper` | Python class wrapper callable from agent           |
| 3          | `feature/phase-3-analysis-agent`    | ReAct agent runs 7 tools end-to-end                |
| 4          | `feature/phase-4-workflow`          | LangGraph router + analysis node wired             |
| 5          | `feature/phase-5-api`               | `/analyze` endpoint live, Langfuse traces visible  |
| 6          | `feature/phase-6-frontend-chart`    | ChartWidget renders Plotly in UI                   |
| 7          | `feature/phase-7-integration-tests` | All smoke tests pass                               |
| 8          | `feature/phase-8-docs`              | Docs, PR, cycle closed                             |
| _(future)_ | `feature/phase-mcp-migration`       | Convert Python wrapper → real Anthropic MCP server |

**Branch commands for each sprint:**

```bash
# Start sprint N
git checkout feature/analyzer_agent
git pull
git checkout -b feature/phase-N-name

# End sprint N — merge back
git checkout feature/analyzer_agent
git merge --no-ff feature/phase-N-name
```

---

## Phase 0 — Setup

- [ ] **0.1** Create sprint branch: `git checkout -b feature/phase-0-setup` from `feature/analyzer_agent`
- [ ] **0.2** Add Python dependencies to [`requirements.txt`](../requirements.txt):
  ```
  scipy>=1.12
  numpy>=1.26
  plotly>=5.20
  ```
- [ ] **0.3** Add frontend dependencies to [`frontend/package.json`](../frontend/package.json):
  ```json
  "plotly.js": "^2.30.0",
  "react-plotly.js": "^2.6.0"
  ```
- [ ] **0.4** Run `pip install -r requirements.txt` and `npm install` inside `frontend/` to verify no conflicts

---

- [ ] **0.5** Merge `feature/phase-0-setup` → `feature/analyzer_agent` via PR

---

## Phase 1 — Pure Analytics Functions

> **Sprint branch:** `feature/phase-1-pure-analytics`
> All files in `backend/analytics/`. No LangChain imports, no DB imports. Unit-testable in isolation.
> Sprint done when: `pytest backend/tests/test_analytics.py` passes with zero DB connections.

- [ ] **1.0** `git checkout -b feature/phase-1-pure-analytics`
- [ ] **1.1** Create `backend/analytics/__init__.py`
  - Export all public functions from sub-modules
  - Add module docstring explaining MCP-READY strategy

- [ ] **1.2** Create `backend/analytics/statistics.py`
  - Implement `compute_descriptive_stats(data, column, group_by=None)`
    - Compute: count, mean, median, std, min, max, p25, p75 using `statistics` stdlib + `numpy`
    - When `group_by` is given, return per-group breakdown in `"groups"` dict
    - Return schema: `{column, group_by, overall: {...}, groups: {...}}`
  - Implement `compute_correlation(data, col_x, col_y)`
    - Compute Pearson r using `scipy.stats.pearsonr`
    - Derive r_squared and map r to human `interpretation` ("strong positive", etc.)
    - Return schema: `{col_x, col_y, r, r_squared, interpretation, n}`
  - Add `# MCP-READY` comment above each function

- [ ] **1.3** Create `backend/analytics/trends.py`
  - Implement `compute_trend(data, date_col, value_col, period="month")`
    - Parse date strings to `datetime.date` objects
    - Aggregate by period (day/week/month/quarter) using dict grouping
    - Fit linear regression via `scipy.stats.linregress`
    - Return `{date_col, value_col, period, direction, slope_per_period, r_squared, series}`
  - Implement `compute_forecast(data, date_col, value_col, periods_ahead=3, period="month")`
    - Re-use `compute_trend` internally
    - Project `periods_ahead` future periods using slope + intercept
    - Return `{historical, forecast, method, confidence}`
    - Set confidence: "high" if r_squared>0.8, "medium" if >0.5, else "low"
  - Add `# MCP-READY` comment above each function

- [ ] **1.4** Create `backend/analytics/outliers.py`
  - Implement `detect_outliers_iqr(data, column, id_col="id")`
    - Compute Q1, Q3, IQR; fences = Q1-1.5×IQR, Q3+1.5×IQR
    - Return `{column, method, q1, q3, iqr, lower_fence, upper_fence, outlier_count, outlier_pct, outliers}`
    - Each outlier entry: `{id, value, direction}`
  - Implement `detect_outliers_zscore(data, column, id_col="id", threshold=3.0)`
    - Compute mean, std; flag rows where `|z| > threshold`
    - Return `{column, method, mean, std, threshold, outlier_count, outlier_pct, outliers}`
    - Each outlier entry: `{id, value, z_score, direction}`
  - Add `# MCP-READY` comment above each function

- [ ] **1.5** Create `backend/analytics/chart_config.py`
  - Implement `generate_chart_config(data, chart_type, x_col, y_col, title=None, color_col=None, orientation="v")`
  - Support chart types: `bar`, `line`, `scatter`, `pie`, `histogram`, `box`
  - Build Plotly-compatible `data` (traces) and `layout` objects as plain dicts
  - Include `fallback_table` key (raw `[{x_col: ..., y_col: ...}]` list) for graceful degradation
  - Return `{chart_type, title, plotly: {data, layout}, fallback_table}`
  - Add `# MCP-READY` comment

- [ ] **1.6** Write unit tests in `backend/tests/test_analytics.py` (one test per function):
  - Use small in-memory datasets (no DB connection required)
  - Verify output dict keys match the specified schemas
  - Test edge cases: empty list, single-row list, all-same-value column

- [ ] **1.X** Merge `feature/phase-1-pure-analytics` → `feature/analyzer_agent` via PR

---

## Phase 2 — Analytics Python Wrapper

> **Sprint branch:** `feature/phase-2-analytics-wrapper`
> **⚠️ IMPORTANT — What this is NOT:**
> This is **not** an Anthropic MCP server. It does **not** use the `mcp` package, `fastmcp`, `stdio` transport, or any MCP SDK. It is a plain Python class that wraps the analytics functions — identical in style to the existing [`mcp_server.py`](../backend/mcp_server.py) which is also a plain Python class despite its name.
>
> **What this IS:**
> A thin Python class (`AnalyticsMCPServer`) that the `AnalysisAgent` calls directly via `analytics_mcp_server.method()`. The class name and `# MCP-MIGRATION:` comments are forward-looking documentation only — they do not implement any protocol.
>
> **Future sprint `feature/phase-mcp-migration`** will convert this class to a real Anthropic MCP server using the MCP SDK. That migration will not change `analytics/` pure functions at all.
>
> Sprint done when: `AnalysisAgent` can import and call all 5 wrapper methods without errors.

- [ ] **2.0** `git checkout -b feature/phase-2-analytics-wrapper`
- [ ] **2.1** Create `backend/analytics_mcp_server.py`
  - Define class `AnalyticsMCPServer` — **plain Python class, no MCP SDK, no imports from `mcp` package**
  - Mirror the structure of [`mcp_server.py`](../backend/mcp_server.py) exactly: same logging style, same `{success, result, error}` return envelope
  - Implement 5 public methods (each wraps one or two pure analytics functions):
    - `compute_stats(data, column, group_by=None) → {success, result, error}`
    - `compute_trend(data, date_col, value_col, period="month") → {success, result, error}`
    - `compute_forecast(data, date_col, value_col, periods_ahead=3, period="month") → {success, result, error}`
    - `detect_outliers(data, column, method="iqr", id_col="id", zscore_threshold=3.0) → {success, result, error}`
    - `generate_chart(data, chart_type, x_col, y_col, title=None, color_col=None) → {success, result, error}`
  - Each method must:
    - Log entry with `log_with_props` (match style of `mcp_server.py`)
    - Wrap call in `try/except` and return `{success: False, error: str(e)}` on failure
    - Use `log_execution_time` context manager
    - Include a `# MCP-MIGRATION: future @mcp.tool("method_name") signature` comment — documentation only
  - Create module-level singleton: `analytics_mcp_server = AnalyticsMCPServer()`
  - **Do not** add `mcp` to `requirements.txt` — this phase has zero MCP dependencies
- [ ] **2.X** Merge `feature/phase-2-analytics-wrapper` → `feature/analyzer_agent` via PR

---

## Phase 3 — Analysis Agent

> **Sprint branch:** `feature/phase-3-analysis-agent`
> Sprint done when: `AnalysisAgent().run("what is the average order value?")` returns a valid dict with `success=True` in a local test script.

- [ ] **3.0** `git checkout -b feature/phase-3-analysis-agent`
- [ ] **3.1** Create `backend/agents/analysis_agent.py`
  - Define class `AnalysisAgent` (same constructor signature as `SQLAgent`)
  - `__init__`: initialise `ChatOpenAI(model="gpt-4o", temperature=0)` (GPT-4o for better reasoning)
  - `_create_tools()` → return list of 7 `Tool` objects:

    | Tool name          | Calls                                        | Input args                                        |
    | ------------------ | -------------------------------------------- | ------------------------------------------------- |
    | `get_schema`       | `mcp_server.get_schema(table)`               | `table: str`                                      |
    | `execute_sql`      | `mcp_server.execute_query(query)`            | `query: str`                                      |
    | `compute_stats`    | `analytics_mcp_server.compute_stats(...)`    | `data_json, column, group_by=""`                  |
    | `compute_trend`    | `analytics_mcp_server.compute_trend(...)`    | `data_json, date_col, value_col, period="month"`  |
    | `compute_forecast` | `analytics_mcp_server.compute_forecast(...)` | `data_json, date_col, value_col, periods_ahead=3` |
    | `detect_outliers`  | `analytics_mcp_server.detect_outliers(...)`  | `data_json, column, method="iqr"`                 |
    | `generate_chart`   | `analytics_mcp_server.generate_chart(...)`   | `data_json, chart_type, x_col, y_col, title=""`   |

  - Analytics tool functions accept `data_json: str` (JSON string), parse with `json.loads` internally
  - Each tool wrapper must log entry/exit and errors (same pattern as [`sql_agent.py`](../backend/agents/sql_agent.py))
  - `_create_agent()`: call `create_react_agent(model=self.llm, tools=self.tools, prompt=ANALYSIS_SYSTEM_PROMPT)`
  - `run(query: str) → Dict[str, Any]`:
    - Invoke agent
    - Extract `final_answer` text from last AI message
    - Extract `chart_config` from last `generate_chart` tool result (if any)
    - Extract `analysis_data` from last `compute_*` tool result (if any)
    - Return `{success, output, analysis_data, chart_config, full_trace}`

- [ ] **3.2** Define `ANALYSIS_SYSTEM_PROMPT` constant in `analysis_agent.py`
  - Include full schema descriptor and analytical workflow instructions
  - Keep it as a module-level constant so it can be tuned without touching agent logic

- [ ] **3.X** Merge `feature/phase-3-analysis-agent` → `feature/analyzer_agent` via PR

---

## Phase 4 — Extend LangGraph Workflow

> **Sprint branch:** `feature/phase-4-workflow`
> Sprint done when: `POST /query "show me revenue trend"` routes to `analysis_node` and returns a structured response (verified in logs).

- [ ] **4.0** `git checkout -b feature/phase-4-workflow`
- [ ] **4.1** Extend `AgentState` in [`backend/graph/workflow.py`](../backend/graph/workflow.py)
  - Add `intent: str` field (default `"sql"`)
  - Add `analysis_result: Annotated[List[Dict[str, Any]], operator.add]` field
  - Ensure existing fields are unchanged (backwards-compatible)

- [ ] **4.2** Implement `query_router_node(state: AgentState) → AgentState`
  - Use `ChatOpenAI(model="gpt-4o-mini", temperature=0)` for fast classification
  - Build prompt: classify query as `"sql"` or `"analytics"` (one-word response)
  - Parse response; default to `"sql"` on any parse error
  - Set `state['intent']` and return updated state
  - Log classification result and confidence

- [ ] **4.3** Implement `analysis_node(state: AgentState) → AgentState`
  - Mirror the existing `sql_node` structure exactly
  - Import `AnalysisAgent` inside the function (same lazy-import pattern)
  - Append result to `state['analysis_result']` list

- [ ] **4.4** Update `answer_node(state: AgentState)` to handle both intents
  - Check `state.get('intent', 'sql')`
  - For `"analytics"`: read from `state['analysis_result'][-1]` instead of `sql_result`
  - If `analysis_result` contains `chart_config`, call `WidgetFormatter.format_as_chart()`
  - Keep all existing SQL-path logic unchanged

- [ ] **4.5** Update `create_workflow()`:
  - Change entry point from `'sql_agent'` to `'query_router'`
  - Add `query_router` node
  - Add `analysis_agent` node
  - Add conditional edges from `query_router` → `{sql: sql_agent, analytics: analysis_agent}`
  - Add edge `analysis_agent → answer`
  - Update initial state dict in `trace_agent_run` to include `intent: ""` and `analysis_result: []`

- [ ] **4.X** Merge `feature/phase-4-workflow` → `feature/analyzer_agent` via PR

---

## Phase 5 — Extend Backend API

> **Sprint branch:** `feature/phase-5-api`
> Sprint done when: `curl -X POST /analyze -d '{"query":"..."}'` returns `200` with `chart_config` populated and Langfuse shows a separate "DataChat Analysis" trace.

- [ ] **5.0** `git checkout -b feature/phase-5-api`
- [ ] **5.1** Add `AnalyzeRequest` and `AnalyzeResponse` Pydantic models to [`backend/main.py`](../backend/main.py)
  - `AnalyzeRequest`: `query: str`, `context: Optional[Dict[str, Any]] = None`
  - `AnalyzeResponse`: `success, answer, chart_config, analysis_metadata, error, trace_id`

- [ ] **5.2** Add `POST /analyze` endpoint to `main.py`
  - Follow identical error-handling pattern as `POST /query`
  - Call `trace_analysis_run(request.query)` (to be created in step 5.3)
  - Extract `final_answer` and `chart_config` from result
  - Return `AnalyzeResponse`
  - Add `log_with_props` calls for entry, validation, execution, and response

- [ ] **5.3** Add `trace_analysis_run(query: str)` to [`backend/observability/tracing.py`](../backend/observability/tracing.py)
  - Decorate with `@observe(name="DataChat Analysis")`
  - Pre-set `intent = "analytics"` in initial workflow state
  - Add Langfuse tag `query_type: "analysis"` to differentiate traces
  - Mirror all logging from existing `trace_agent_run`

- [ ] **5.X** Merge `feature/phase-5-api` → `feature/analyzer_agent` via PR

---

## Phase 6 — Extend Widget System

> **Sprint branch:** `feature/phase-6-frontend-chart`
> Sprint done when: a chart query in the chat UI renders a Plotly chart (not just a text response).

- [ ] **6.0** `git checkout -b feature/phase-6-frontend-chart`
- [ ] **6.1** Add `format_as_chart(data, query, metadata)` static method to `WidgetFormatter` in [`backend/widget_formatter.py`](../backend/widget_formatter.py)
  - Input `data` is the dict returned by `generate_chart_config`
  - Return `{type: "chart", data: plotly_config, title, fallback_table, fallback, query}`
  - Update `detect_widget_type()` to recognise chart data and return `"chart"`

- [ ] **6.2** Create `frontend/src/components/widgets/ChartWidget.js`
  - Import `Plot` from `react-plotly.js`
  - Accept props: `data` (Plotly traces), `layout`, `title`, `fallback_table`
  - Render `<Plot data={data} layout={layout} />`
  - Fall back to a `<TableWidget>` rendering of `fallback_table` if Plotly data is empty
  - Add responsive sizing: `useResizeHandler={true}` and `style={{width: "100%"}}`

- [ ] **6.3** Create `frontend/src/components/widgets/ChartWidget.css`
  - Style chart container, title, fallback section
  - Use same spacing/border conventions as `TableWidget.css`

- [ ] **6.4** Register `ChartWidget` in [`frontend/src/components/widgets/WidgetRegistry.js`](../frontend/src/components/widgets/WidgetRegistry.js)
  - Import `ChartWidget`
  - Add `chart: ChartWidget` to the registry map

- [ ] **6.5** Update `frontend/src/services/api.js` to add `analyzeQuery(query, context)` function
  - `POST /analyze` with `{query, context}` body
  - Return full response including `chart_config`
  - Handle errors consistently with existing `sendQuery()`

- [ ] **6.X** Merge `feature/phase-6-frontend-chart` → `feature/analyzer_agent` via PR

---

## Phase 7 — Integration Testing

> **Sprint branch:** `feature/phase-7-integration-tests`
> Sprint done when: all 4 smoke test scenarios pass and Langfuse shows correct trace tags.

- [ ] **7.0** `git checkout -b feature/phase-7-integration-tests`
- [ ] **7.1** Manual smoke tests via `curl` or Postman:
  - `POST /query` with `"list all customers"` → still returns table widget (SQL path unchanged)
  - `POST /query` with `"show me the trend in monthly revenue"` → routes to analytics, returns chart
  - `POST /analyze` with `"find outlier orders by total_amount"` → returns outlier data
  - `POST /analyze` with `"what is the correlation between price and quantity sold?"` → returns correlation stats

- [ ] **7.2** Verify Langfuse traces:
  - `/query` traces tagged `query_type: analytics` vs `query_type: sql` correctly
  - `/analyze` traces tagged `query_type: analysis`
  - All 7 tool calls visible in trace tree for analysis queries

- [ ] **7.3** Frontend integration test:
  - Send an analytics query through the chat UI
  - Verify `ChartWidget` renders (Plotly chart visible)
  - Verify fallback table shows if chart data is missing

- [ ] **7.4** Edge case tests:
  - Analytics query on empty table → graceful "no data" message
  - `compute_forecast` with < 3 data points → returns error in `result`, not crash
  - `query_router` classifying ambiguous query → defaults to `"sql"`, no error

- [ ] **7.X** Merge `feature/phase-7-integration-tests` → `feature/analyzer_agent` via PR

---

## Phase 8 — Documentation & Cleanup

> **Sprint branch:** `feature/phase-8-docs`
> Sprint done when: PR from `feature/analyzer_agent` → `main` is open and reviewed.

- [ ] **8.0** `git checkout -b feature/phase-8-docs`
- [ ] **8.1** Add docstrings to every new function and class (Google-style)
- [ ] **8.2** Add `# MCP-MIGRATION:` comments to every method in `analytics_mcp_server.py` documenting the future `@mcp.tool` signature
- [ ] **8.3** Update [`docs/datachat_consolidated_documentation.md`](../docs/datachat_consolidated_documentation.md) with:
  - New architecture diagram
  - Description of analysis agent and its tools
  - Description of `POST /analyze` endpoint
  - Widget type reference (add `chart`)
- [ ] **8.4** Update top-level `README.md` (if it exists) with the new `/analyze` endpoint
- [ ] **8.5** Create `backend/tests/test_analysis_agent.py` with integration test stubs (mock DB calls)
- [ ] **8.6** Open PR from `feature/phase-8-docs` → `feature/analyzer_agent` then final PR `feature/analyzer_agent` → `main`
- [ ] **8.7** Note in PR description: Phase 2 used a **plain Python class wrapper** — future sprint `feature/phase-mcp-migration` will upgrade to proper Anthropic MCP server

---

## Dependency Map

```
Phase 0 (Setup)
  └── Phase 1 (Pure Functions)
        └── Phase 2 (MCP Server)
              └── Phase 3 (Analysis Agent)
                    ├── Phase 4 (Workflow)
                    │     └── Phase 5 (API)
                    └── Phase 6 (Frontend Widget)
                          └── Phase 7 (Integration Tests)
                                └── Phase 8 (Docs)
```

Phases 5 and 6 can be developed in parallel after Phase 4 is complete.

---

## Files Created / Modified Checklist

| File                                                | Action     | Phase |
| --------------------------------------------------- | ---------- | ----- |
| `requirements.txt`                                  | Modify     | 0     |
| `frontend/package.json`                             | Modify     | 0     |
| `backend/analytics/__init__.py`                     | **Create** | 1     |
| `backend/analytics/statistics.py`                   | **Create** | 1     |
| `backend/analytics/trends.py`                       | **Create** | 1     |
| `backend/analytics/outliers.py`                     | **Create** | 1     |
| `backend/analytics/chart_config.py`                 | **Create** | 1     |
| `backend/tests/test_analytics.py`                   | **Create** | 1     |
| `backend/analytics_mcp_server.py`                   | **Create** | 2     |
| `backend/agents/analysis_agent.py`                  | **Create** | 3     |
| `backend/graph/workflow.py`                         | Modify     | 4     |
| `backend/main.py`                                   | Modify     | 5     |
| `backend/observability/tracing.py`                  | Modify     | 5     |
| `backend/widget_formatter.py`                       | Modify     | 6     |
| `frontend/src/components/widgets/ChartWidget.js`    | **Create** | 6     |
| `frontend/src/components/widgets/ChartWidget.css`   | **Create** | 6     |
| `frontend/src/components/widgets/WidgetRegistry.js` | Modify     | 6     |
| `frontend/src/services/api.js`                      | Modify     | 6     |
| `backend/tests/test_analysis_agent.py`              | **Create** | 8     |
| `docs/datachat_consolidated_documentation.md`       | Modify     | 8     |
