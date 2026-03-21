"""
Unit tests for the analytics package.
These tests use small in-memory datasets and do not require a DB connection.
"""
import pytest
from typing import List, Dict, Any

# Import all implemented functions
from backend.analytics.statistics import compute_descriptive_stats, compute_correlation
from backend.analytics.trends import compute_trend, compute_forecast
from backend.analytics.outliers import detect_outliers_iqr, detect_outliers_zscore
from backend.analytics.chart_config import generate_chart_config


# Sample test data
@pytest.fixture
def sample_data() -> List[Dict[str, Any]]:
    """Return a small dataset for testing analytics functions."""
    return [
        {"id": 1, "value": 100, "date": "2025-01-01", "category": "A"},
        {"id": 2, "value": 150, "date": "2025-01-15", "category": "B"},
        {"id": 3, "value": 200, "date": "2025-02-01", "category": "A"},
        {"id": 4, "value": 120, "date": "2025-02-15", "category": "B"},
        {"id": 5, "value": 180, "date": "2025-03-01", "category": "A"},
    ]


# Placeholder tests for statistics.py
def test_compute_descriptive_stats(sample_data):
    """Test compute_descriptive_stats function."""
    # Test without grouping
    result = compute_descriptive_stats(sample_data, "value")
    
    # Check structure
    assert "column" in result
    assert "overall" in result
    assert "group_by" in result
    assert "groups" not in result  # No grouping
    
    # Check values
    assert result["column"] == "value"
    assert result["group_by"] is None
    
    # Check overall stats
    overall = result["overall"]
    assert overall["count"] == 5
    assert 140 <= overall["mean"] <= 160  # Should be around 150
    assert overall["min"] == 100
    assert overall["max"] == 200
    
    # Test with grouping
    result_grouped = compute_descriptive_stats(sample_data, "value", "category")
    
    # Check structure
    assert "groups" in result_grouped
    assert "A" in result_grouped["groups"]
    assert "B" in result_grouped["groups"]
    
    # Check group stats
    group_a = result_grouped["groups"]["A"]
    assert group_a["count"] == 3
    assert 150 <= group_a["mean"] <= 170  # Should be around 160
    
    # Test edge case: empty data
    empty_result = compute_descriptive_stats([], "value")
    assert empty_result["overall"]["count"] == 0
    assert empty_result["overall"]["mean"] is None


def test_compute_correlation(sample_data):
    """Test compute_correlation function."""
    # Add a correlated column for testing
    for i, row in enumerate(sample_data):
        row["correlated"] = row["value"] * 2 + 10  # Perfect positive correlation
        row["anti_correlated"] = 500 - row["value"]  # Perfect negative correlation
    
    # Test positive correlation
    result = compute_correlation(sample_data, "value", "correlated")
    
    # Check structure
    assert "col_x" in result
    assert "col_y" in result
    assert "r" in result
    assert "r_squared" in result
    assert "interpretation" in result
    assert "n" in result
    
    # Check values
    assert result["col_x"] == "value"
    assert result["col_y"] == "correlated"
    assert 0.95 <= result["r"] <= 1.0  # Should be close to 1
    assert 0.9 <= result["r_squared"] <= 1.0
    assert "strong positive" in result["interpretation"]
    assert result["n"] == 5
    
    # Test negative correlation
    result_neg = compute_correlation(sample_data, "value", "anti_correlated")
    assert -1.0 <= result_neg["r"] <= -0.95  # Should be close to -1
    assert "strong negative" in result_neg["interpretation"]
    
    # Test edge case: insufficient data
    empty_result = compute_correlation([], "value", "correlated")
    assert empty_result["r"] is None
    assert empty_result["interpretation"] == "insufficient data"


# Placeholder tests for trends.py
def test_compute_trend(sample_data):
    """Test compute_trend function."""
    # Test monthly trend
    result = compute_trend(sample_data, "date", "value", "month")
    
    # Check structure
    assert "date_col" in result
    assert "value_col" in result
    assert "period" in result
    assert "direction" in result
    assert "slope_per_period" in result
    assert "r_squared" in result
    assert "series" in result
    
    # Check values
    assert result["date_col"] == "date"
    assert result["value_col"] == "value"
    assert result["period"] == "month"
    assert result["direction"] in ["up", "down", "flat"]
    assert isinstance(result["slope_per_period"], float)
    assert 0 <= result["r_squared"] <= 1
    
    # Check series
    assert len(result["series"]) > 0
    assert "period" in result["series"][0]
    assert "value" in result["series"][0]
    
    # Test edge case: insufficient data
    empty_result = compute_trend([], "date", "value")
    assert empty_result["direction"] == "insufficient data"
    assert empty_result["slope_per_period"] is None


def test_compute_forecast(sample_data):
    """Test compute_forecast function."""
    # Test forecast
    result = compute_forecast(sample_data, "date", "value", 2, "month")
    
    # Check structure
    assert "historical" in result
    assert "forecast" in result
    assert "method" in result
    assert "confidence" in result
    
    # Check values
    assert result["method"] == "linear_regression"
    assert result["confidence"] in ["low", "medium", "high", "none"]
    
    # Check historical data
    assert len(result["historical"]) > 0
    assert "period" in result["historical"][0]
    assert "value" in result["historical"][0]
    
    # Check forecast data
    assert len(result["forecast"]) == 2  # We requested 2 periods ahead
    assert "period" in result["forecast"][0]
    assert "value" in result["forecast"][0]
    assert "is_forecast" in result["forecast"][0]
    assert result["forecast"][0]["is_forecast"] is True
    
    # Test edge case: insufficient data
    empty_result = compute_forecast([], "date", "value")
    assert len(empty_result["historical"]) == 0
    assert len(empty_result["forecast"]) == 0


# Placeholder tests for outliers.py
def test_detect_outliers_iqr(sample_data):
    """Test detect_outliers_iqr function."""
    # Add an outlier
    sample_data.append({"id": 6, "value": 500, "date": "2025-03-15", "category": "A"})
    
    # Test outlier detection
    result = detect_outliers_iqr(sample_data, "value")
    
    # Check structure
    assert "column" in result
    assert "method" in result
    assert "q1" in result
    assert "q3" in result
    assert "iqr" in result
    assert "lower_fence" in result
    assert "upper_fence" in result
    assert "outlier_count" in result
    assert "outlier_pct" in result
    assert "outliers" in result
    
    # Check values
    assert result["column"] == "value"
    assert result["method"] == "iqr"
    assert result["outlier_count"] >= 1  # Should detect at least the one we added
    assert 0 <= result["outlier_pct"] <= 100
    
    # Check outliers
    assert len(result["outliers"]) >= 1
    outlier = result["outliers"][0]
    assert "id" in outlier
    assert "value" in outlier
    assert "direction" in outlier
    assert outlier["direction"] in ["high", "low"]
    
    # Test edge case: empty data
    empty_result = detect_outliers_iqr([], "value")
    assert empty_result["outlier_count"] == 0
    assert len(empty_result["outliers"]) == 0


def test_detect_outliers_zscore(sample_data):
    """Test detect_outliers_zscore function."""
    # Add an extreme outlier
    sample_data.append({"id": 6, "value": 1000, "date": "2025-03-15", "category": "A"})
    
    # Test outlier detection with a lower threshold to ensure detection
    result = detect_outliers_zscore(sample_data, "value", threshold=1.5)
    
    # Check structure
    assert "column" in result
    assert "method" in result
    assert "mean" in result
    assert "std" in result
    assert "threshold" in result
    assert "outlier_count" in result
    assert "outlier_pct" in result
    assert "outliers" in result
    
    # Check values
    assert result["column"] == "value"
    assert result["method"] == "zscore"
    assert result["threshold"] == 1.5  # Updated to match the threshold we're using
    assert result["outlier_count"] >= 1  # Should detect at least the one we added
    assert 0 <= result["outlier_pct"] <= 100
    
    # Check outliers
    assert len(result["outliers"]) >= 1
    outlier = result["outliers"][0]
    assert "id" in outlier
    assert "value" in outlier
    assert "z_score" in outlier
    assert "direction" in outlier
    assert outlier["direction"] in ["high", "low"]
    
    # Test edge case: empty data
    empty_result = detect_outliers_zscore([], "value")
    assert empty_result["outlier_count"] == 0
    assert len(empty_result["outliers"]) == 0


# Placeholder tests for chart_config.py
def test_generate_chart_config(sample_data):
    """Test generate_chart_config function."""
    # Test bar chart
    result = generate_chart_config(sample_data, "bar", "category", "value")
    
    # Check structure
    assert "chart_type" in result
    assert "title" in result
    assert "plotly" in result
    assert "fallback_table" in result
    
    # Check values
    assert result["chart_type"] == "bar"
    assert "plotly" in result
    assert "data" in result["plotly"]
    assert "layout" in result["plotly"]
    assert len(result["plotly"]["data"]) > 0
    assert len(result["fallback_table"]) > 0
    
    # Test with color grouping
    result_color = generate_chart_config(sample_data, "bar", "date", "value", color_col="category")
    assert len(result_color["plotly"]["data"]) >= 2  # Should have at least 2 traces (one per category)
    
    # Test line chart
    result_line = generate_chart_config(sample_data, "line", "date", "value")
    assert result_line["chart_type"] == "line"
    assert len(result_line["plotly"]["data"]) > 0
    assert result_line["plotly"]["data"][0]["type"] == "scatter"
    assert result_line["plotly"]["data"][0]["mode"] == "lines+markers"
    
    # Test scatter plot
    result_scatter = generate_chart_config(sample_data, "scatter", "value", "id")
    assert result_scatter["chart_type"] == "scatter"
    assert result_scatter["plotly"]["data"][0]["mode"] == "markers"
    
    # Test pie chart
    result_pie = generate_chart_config(sample_data, "pie", "category", "value")
    assert result_pie["chart_type"] == "pie"
    assert "labels" in result_pie["plotly"]["data"][0]
    assert "values" in result_pie["plotly"]["data"][0]
    
    # Test edge case: empty data
    empty_result = generate_chart_config([], "bar", "category", "value")
    assert len(empty_result["plotly"]["data"]) == 0
    assert len(empty_result["fallback_table"]) == 0