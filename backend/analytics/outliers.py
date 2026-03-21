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
    # Placeholder - will be implemented in Phase 1
    pass

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
    # Placeholder - will be implemented in Phase 1
    pass