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
    # Placeholder - will be implemented in Phase 1
    pass