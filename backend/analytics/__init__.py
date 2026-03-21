"""
analytics/
Pure analytics functions — no LangChain, no DB dependencies.
These functions operate on plain Python lists of dicts (SQL query results).

MCP-READY: Each public function in this package maps 1-to-1 to an MCP tool
definition when migrating from Option B to Option C. The tool name is the
function name; the tool input schema is derived from the function signature.
"""

# These imports will be uncommented as the actual modules are implemented
# from analytics.statistics import compute_descriptive_stats, compute_correlation
# from analytics.trends import compute_trend, compute_forecast
# from analytics.outliers import detect_outliers_iqr, detect_outliers_zscore
# from analytics.chart_config import generate_chart_config

__all__ = [
    # "compute_descriptive_stats",
    # "compute_correlation",
    # "compute_trend",
    # "compute_forecast",
    # "detect_outliers_iqr",
    # "detect_outliers_zscore",
    # "generate_chart_config",
]