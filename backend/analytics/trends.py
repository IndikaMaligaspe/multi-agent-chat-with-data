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
    # Placeholder - will be implemented in Phase 1
    pass

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
    # Placeholder - will be implemented in Phase 1
    pass