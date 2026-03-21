"""
Outlier detection functions.

MCP-READY: Each function becomes an MCP tool.
"""
from typing import List, Dict, Any

# MCP-READY
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
    import numpy as np
    
    # Extract values and corresponding IDs
    value_id_pairs = []
    for row in data:
        if column in row and row[column] is not None and id_col in row:
            value_id_pairs.append((row[id_col], row[column]))
    
    if not value_id_pairs:
        return {
            "column": column,
            "method": "iqr",
            "q1": None,
            "q3": None,
            "iqr": None,
            "lower_fence": None,
            "upper_fence": None,
            "outlier_count": 0,
            "outlier_pct": 0.0,
            "outliers": []
        }
    
    # Separate IDs and values
    ids, values = zip(*value_id_pairs)
    values_array = np.array(values)
    
    # Calculate quartiles and IQR
    q1 = float(np.percentile(values_array, 25))
    q3 = float(np.percentile(values_array, 75))
    iqr = q3 - q1
    
    # Calculate fences
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr
    
    # Identify outliers
    outliers = []
    for id_val, value in value_id_pairs:
        if value < lower_fence:
            outliers.append({
                "id": id_val,
                "value": float(value),
                "direction": "low"
            })
        elif value > upper_fence:
            outliers.append({
                "id": id_val,
                "value": float(value),
                "direction": "high"
            })
    
    # Calculate outlier percentage
    outlier_count = len(outliers)
    outlier_pct = (outlier_count / len(values)) * 100 if values else 0.0
    
    return {
        "column": column,
        "method": "iqr",
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "lower_fence": lower_fence,
        "upper_fence": upper_fence,
        "outlier_count": outlier_count,
        "outlier_pct": float(outlier_pct),
        "outliers": outliers
    }

# MCP-READY
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
    import numpy as np
    import statistics as stats
    
    # Extract values and corresponding IDs
    value_id_pairs = []
    for row in data:
        if column in row and row[column] is not None and id_col in row:
            value_id_pairs.append((row[id_col], row[column]))
    
    if not value_id_pairs or len(value_id_pairs) < 2:  # Need at least 2 values to calculate std
        return {
            "column": column,
            "method": "zscore",
            "mean": None,
            "std": None,
            "threshold": threshold,
            "outlier_count": 0,
            "outlier_pct": 0.0,
            "outliers": []
        }
    
    # Separate IDs and values
    ids, values = zip(*value_id_pairs)
    
    # Calculate mean and standard deviation
    mean = stats.mean(values)
    std = stats.stdev(values)
    
    if std == 0:  # Avoid division by zero
        return {
            "column": column,
            "method": "zscore",
            "mean": float(mean),
            "std": 0.0,
            "threshold": threshold,
            "outlier_count": 0,
            "outlier_pct": 0.0,
            "outliers": []
        }
    
    # Calculate z-scores and identify outliers
    outliers = []
    for id_val, value in value_id_pairs:
        z_score = (value - mean) / std
        if abs(z_score) > threshold:
            outliers.append({
                "id": id_val,
                "value": float(value),
                "z_score": float(z_score),
                "direction": "high" if z_score > 0 else "low"
            })
    
    # Calculate outlier percentage
    outlier_count = len(outliers)
    outlier_pct = (outlier_count / len(values)) * 100 if values else 0.0
    
    return {
        "column": column,
        "method": "zscore",
        "mean": float(mean),
        "std": float(std),
        "threshold": float(threshold),
        "outlier_count": outlier_count,
        "outlier_pct": float(outlier_pct),
        "outliers": outliers
    }