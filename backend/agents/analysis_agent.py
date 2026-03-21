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
        # Placeholder - will be implemented in Phase 3
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.tools = self._create_tools()
        self.agent = None  # Will be initialized in Phase 3

    def _create_tools(self) -> list:
        """
        Create all tools: 2 DB tools + 5 analytics tools.
        Each tool wrapper follows the logging pattern from sql_agent.py.
        """
        # Placeholder - will be implemented in Phase 3
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
        # Placeholder - will be implemented in Phase 3
        return {
            "success": False,
            "output": "Analysis agent not implemented yet",
            "analysis_data": None,
            "chart_config": None,
            "full_trace": None
        }