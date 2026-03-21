"""
Time-series trend and forecasting functions.

MCP-READY: Each function becomes an MCP tool.
"""
from typing import List, Dict, Any

# MCP-READY
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
    from datetime import datetime
    from scipy.stats import linregress
    import numpy as np
    
    # Validate period parameter
    valid_periods = ["day", "week", "month", "quarter"]
    if period not in valid_periods:
        raise ValueError(f"Period must be one of {valid_periods}")
    
    # Extract date and value pairs, filtering out None values
    date_value_pairs = []
    for row in data:
        if date_col in row and value_col in row and row[date_col] is not None and row[value_col] is not None:
            try:
                # Parse date string to datetime object
                date_obj = datetime.fromisoformat(row[date_col].replace('Z', '+00:00'))
                date_value_pairs.append((date_obj, float(row[value_col])))
            except (ValueError, TypeError):
                # Skip rows with invalid date format or non-numeric values
                continue
    
    if not date_value_pairs:
        return {
            "date_col": date_col,
            "value_col": value_col,
            "period": period,
            "direction": "insufficient data",
            "slope_per_period": None,
            "r_squared": None,
            "series": []
        }
    
    # Sort by date
    date_value_pairs.sort(key=lambda x: x[0])
    
    # Group by period
    period_groups = {}
    for date_obj, value in date_value_pairs:
        if period == "day":
            period_key = date_obj.strftime("%Y-%m-%d")
        elif period == "week":
            # ISO week format: YYYY-Www
            period_key = f"{date_obj.isocalendar()[0]}-W{date_obj.isocalendar()[1]:02d}"
        elif period == "month":
            period_key = date_obj.strftime("%Y-%m")
        elif period == "quarter":
            quarter = (date_obj.month - 1) // 3 + 1
            period_key = f"{date_obj.year}-Q{quarter}"
        
        if period_key not in period_groups:
            period_groups[period_key] = []
        period_groups[period_key].append(value)
    
    # Calculate average value for each period
    series = [
        {"period": period_key, "value": sum(values) / len(values)}
        for period_key, values in period_groups.items()
    ]
    
    # Sort series by period
    series.sort(key=lambda x: x["period"])
    
    # Prepare data for linear regression
    x = np.arange(len(series))
    y = np.array([item["value"] for item in series])
    
    if len(x) < 2:
        # Need at least 2 points for regression
        return {
            "date_col": date_col,
            "value_col": value_col,
            "period": period,
            "direction": "insufficient data",
            "slope_per_period": None,
            "r_squared": None,
            "series": series
        }
    
    # Perform linear regression
    slope, intercept, r_value, p_value, std_err = linregress(x, y)
    r_squared = r_value ** 2
    
    # Determine direction
    if abs(slope) < 0.01 * np.mean(y):  # If slope is less than 1% of mean, consider it flat
        direction = "flat"
    else:
        direction = "up" if slope > 0 else "down"
    
    return {
        "date_col": date_col,
        "value_col": value_col,
        "period": period,
        "direction": direction,
        "slope_per_period": float(slope),
        "r_squared": float(r_squared),
        "series": series
    }

# MCP-READY
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
    import re
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta
    
    # First compute the trend to get historical data and regression parameters
    trend_result = compute_trend(data, date_col, value_col, period)
    
    if trend_result["direction"] == "insufficient data" or not trend_result["series"]:
        return {
            "historical": [],
            "forecast": [],
            "method": "linear_regression",
            "confidence": "none"
        }
    
    historical = trend_result["series"]
    slope = trend_result["slope_per_period"]
    r_squared = trend_result["r_squared"]
    
    # Determine confidence level based on r_squared
    if r_squared is None:
        confidence = "none"
    elif r_squared > 0.8:
        confidence = "high"
    elif r_squared > 0.5:
        confidence = "medium"
    else:
        confidence = "low"
    
    # Generate forecast periods
    forecast = []
    if historical:
        last_period = historical[-1]["period"]
        last_value = historical[-1]["value"]
        
        # Generate next period keys based on the period format
        for i in range(1, periods_ahead + 1):
            if period == "day":
                # Format: YYYY-MM-DD
                try:
                    last_date = datetime.strptime(last_period, "%Y-%m-%d")
                    next_date = last_date + timedelta(days=i)
                    next_period = next_date.strftime("%Y-%m-%d")
                except ValueError:
                    # If parsing fails, use a simple increment
                    next_period = f"Period {len(historical) + i}"
            
            elif period == "week":
                # Format: YYYY-Www
                match = re.match(r"(\d{4})-W(\d{2})", last_period)
                if match:
                    year, week = int(match.group(1)), int(match.group(2))
                    # Simple increment, not handling year rollover perfectly
                    next_week = week + i
                    next_year = year
                    while next_week > 52:
                        next_week -= 52
                        next_year += 1
                    next_period = f"{next_year}-W{next_week:02d}"
                else:
                    next_period = f"Period {len(historical) + i}"
            
            elif period == "month":
                # Format: YYYY-MM
                try:
                    last_date = datetime.strptime(last_period, "%Y-%m")
                    next_date = last_date + relativedelta(months=i)
                    next_period = next_date.strftime("%Y-%m")
                except ValueError:
                    next_period = f"Period {len(historical) + i}"
            
            elif period == "quarter":
                # Format: YYYY-Qq
                match = re.match(r"(\d{4})-Q(\d)", last_period)
                if match:
                    year, quarter = int(match.group(1)), int(match.group(2))
                    next_quarter = quarter + i
                    next_year = year
                    while next_quarter > 4:
                        next_quarter -= 4
                        next_year += 1
                    next_period = f"{next_year}-Q{next_quarter}"
                else:
                    next_period = f"Period {len(historical) + i}"
            
            else:
                next_period = f"Period {len(historical) + i}"
            
            # Calculate forecasted value using the linear model
            next_value = last_value + (slope * i)
            
            forecast.append({
                "period": next_period,
                "value": float(next_value),
                "is_forecast": True
            })
    
    return {
        "historical": historical,
        "forecast": forecast,
        "method": "linear_regression",
        "confidence": confidence
    }