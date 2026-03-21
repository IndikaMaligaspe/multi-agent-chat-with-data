"""
analytics/
Pure analytics functions — no LangChain, no DB dependencies.
These functions operate on plain Python lists of dicts (SQL query results).

MCP-READY: Each public function in this package maps 1-to-1 to an MCP tool
definition when migrating from Option B to Option C. The tool name is the
function name; the tool input schema is derived from the function signature.
"""

# Import all implemented functions
from .statistics import compute_descriptive_stats, compute_correlation
from .trends import compute_trend, compute_forecast
from .outliers import detect_outliers_iqr, detect_outliers_zscore
from .chart_config import generate_chart_config

__all__ = [
    "compute_descriptive_stats",
    "compute_correlation",
    "compute_trend",
    "compute_forecast",
    "detect_outliers_iqr",
    "detect_outliers_zscore",
    "generate_chart_config",
]