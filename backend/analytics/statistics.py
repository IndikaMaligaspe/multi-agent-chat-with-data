"""
Pure statistical analysis functions.

MCP-READY: Each function becomes an MCP tool named after the function.
"""
from typing import List, Dict, Any, Optional
import statistics as _stats
import math

# MCP-READY
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
    import numpy as np
    
    # Extract the values for the specified column
    values = [row[column] for row in data if column in row and row[column] is not None]
    
    if not values:
        return {
            "column": column,
            "group_by": group_by,
            "overall": {
                "count": 0,
                "mean": None,
                "median": None,
                "std": None,
                "min": None,
                "max": None,
                "p25": None,
                "p75": None
            }
        }
    
    # Compute overall statistics
    np_values = np.array(values)
    result = {
        "column": column,
        "group_by": group_by,
        "overall": {
            "count": len(values),
            "mean": float(_stats.mean(values)),
            "median": float(_stats.median(values)),
            "std": float(_stats.stdev(values)) if len(values) > 1 else 0.0,
            "min": float(min(values)),
            "max": float(max(values)),
            "p25": float(np.percentile(np_values, 25)),
            "p75": float(np.percentile(np_values, 75))
        }
    }
    
    # If group_by is provided, compute statistics for each group
    if group_by:
        groups = {}
        # Group data by the group_by column
        for row in data:
            if column in row and row[column] is not None and group_by in row and row[group_by] is not None:
                group_value = str(row[group_by])
                if group_value not in groups:
                    groups[group_value] = []
                groups[group_value].append(row[column])
        
        # Compute statistics for each group
        result["groups"] = {}
        for group_value, group_values in groups.items():
            if group_values:
                np_group_values = np.array(group_values)
                result["groups"][group_value] = {
                    "count": len(group_values),
                    "mean": float(_stats.mean(group_values)),
                    "median": float(_stats.median(group_values)),
                    "std": float(_stats.stdev(group_values)) if len(group_values) > 1 else 0.0,
                    "min": float(min(group_values)),
                    "max": float(max(group_values)),
                    "p25": float(np.percentile(np_group_values, 25)),
                    "p75": float(np.percentile(np_group_values, 75))
                }
    
    return result

# MCP-READY
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
    from scipy.stats import pearsonr
    
    # Extract paired values where both columns exist and are not None
    paired_values = [
        (row[col_x], row[col_y])
        for row in data
        if col_x in row and col_y in row and row[col_x] is not None and row[col_y] is not None
    ]
    
    if not paired_values or len(paired_values) < 2:
        return {
            "col_x": col_x,
            "col_y": col_y,
            "r": None,
            "r_squared": None,
            "interpretation": "insufficient data",
            "n": len(paired_values)
        }
    
    # Unzip the paired values
    x_values, y_values = zip(*paired_values)
    
    # Compute Pearson correlation
    r, p_value = pearsonr(x_values, y_values)
    r_squared = r ** 2
    
    # Interpret the correlation coefficient
    interpretation = "no correlation"
    if abs(r) >= 0.8:
        interpretation = "strong " + ("positive" if r > 0 else "negative")
    elif abs(r) >= 0.5:
        interpretation = "moderate " + ("positive" if r > 0 else "negative")
    elif abs(r) >= 0.3:
        interpretation = "weak " + ("positive" if r > 0 else "negative")
    
    return {
        "col_x": col_x,
        "col_y": col_y,
        "r": float(r),
        "r_squared": float(r_squared),
        "interpretation": interpretation,
        "n": len(paired_values)
    }