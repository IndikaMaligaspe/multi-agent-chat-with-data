"""
Chart configuration generator.
Produces Plotly-compatible JSON that the frontend can render directly.

MCP-READY: becomes an MCP tool named generate_chart_config.
"""
from typing import List, Dict, Any, Optional

SUPPORTED_CHART_TYPES = ("bar", "line", "scatter", "pie", "histogram", "box")

# MCP-READY
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
    # Validate chart type
    if chart_type not in SUPPORTED_CHART_TYPES:
        raise ValueError(f"Chart type must be one of {SUPPORTED_CHART_TYPES}")
    
    # Validate orientation
    if orientation not in ("v", "h"):
        raise ValueError("Orientation must be 'v' (vertical) or 'h' (horizontal)")
    
    # Extract data for the specified columns
    filtered_data = []
    for row in data:
        if x_col in row and y_col in row and row[x_col] is not None and row[y_col] is not None:
            new_row = {
                x_col: row[x_col],
                y_col: row[y_col]
            }
            if color_col and color_col in row and row[color_col] is not None:
                new_row[color_col] = row[color_col]
            filtered_data.append(new_row)
    
    if not filtered_data:
        # Return empty chart config if no valid data
        return {
            "chart_type": chart_type,
            "title": title or f"{y_col} by {x_col}",
            "plotly": {
                "data": [],
                "layout": {
                    "title": title or f"{y_col} by {x_col}",
                    "xaxis": {"title": x_col},
                    "yaxis": {"title": y_col}
                }
            },
            "fallback_table": []
        }
    
    # Prepare fallback table (raw data)
    fallback_table = filtered_data
    
    # Initialize plotly config
    plotly_config = {
        "data": [],
        "layout": {
            "title": title or f"{y_col} by {x_col}",
            "xaxis": {"title": x_col},
            "yaxis": {"title": y_col},
            "margin": {"l": 50, "r": 50, "b": 50, "t": 80, "pad": 4},
            "hovermode": "closest"
        }
    }
    
    # Handle different chart types
    if chart_type == "bar":
        if color_col:
            # Group by color column
            color_groups = {}
            for row in filtered_data:
                color_value = str(row.get(color_col, "Unknown"))
                if color_value not in color_groups:
                    color_groups[color_value] = []
                color_groups[color_value].append(row)
            
            # Create a trace for each color group
            for color_value, group_data in color_groups.items():
                x_values = [row[x_col] for row in group_data]
                y_values = [row[y_col] for row in group_data]
                
                trace = {
                    "type": "bar",
                    "name": color_value,
                    "orientation": orientation
                }
                
                if orientation == "v":
                    trace["x"] = x_values
                    trace["y"] = y_values
                else:  # orientation == "h"
                    trace["x"] = y_values
                    trace["y"] = x_values
                
                plotly_config["data"].append(trace)
        else:
            # Simple bar chart
            x_values = [row[x_col] for row in filtered_data]
            y_values = [row[y_col] for row in filtered_data]
            
            trace = {
                "type": "bar",
                "orientation": orientation
            }
            
            if orientation == "v":
                trace["x"] = x_values
                trace["y"] = y_values
            else:  # orientation == "h"
                trace["x"] = y_values
                trace["y"] = x_values
            
            plotly_config["data"].append(trace)
    
    elif chart_type == "line":
        if color_col:
            # Group by color column
            color_groups = {}
            for row in filtered_data:
                color_value = str(row.get(color_col, "Unknown"))
                if color_value not in color_groups:
                    color_groups[color_value] = []
                color_groups[color_value].append(row)
            
            # Create a trace for each color group
            for color_value, group_data in color_groups.items():
                # Sort by x values for proper line connection
                group_data.sort(key=lambda row: row[x_col])
                
                trace = {
                    "type": "scatter",
                    "mode": "lines+markers",
                    "name": color_value,
                    "x": [row[x_col] for row in group_data],
                    "y": [row[y_col] for row in group_data]
                }
                
                plotly_config["data"].append(trace)
        else:
            # Sort by x values for proper line connection
            filtered_data.sort(key=lambda row: row[x_col])
            
            trace = {
                "type": "scatter",
                "mode": "lines+markers",
                "x": [row[x_col] for row in filtered_data],
                "y": [row[y_col] for row in filtered_data]
            }
            
            plotly_config["data"].append(trace)
    
    elif chart_type == "scatter":
        if color_col:
            # Group by color column
            color_groups = {}
            for row in filtered_data:
                color_value = str(row.get(color_col, "Unknown"))
                if color_value not in color_groups:
                    color_groups[color_value] = []
                color_groups[color_value].append(row)
            
            # Create a trace for each color group
            for color_value, group_data in color_groups.items():
                trace = {
                    "type": "scatter",
                    "mode": "markers",
                    "name": color_value,
                    "x": [row[x_col] for row in group_data],
                    "y": [row[y_col] for row in group_data],
                    "marker": {"size": 10}
                }
                
                plotly_config["data"].append(trace)
        else:
            trace = {
                "type": "scatter",
                "mode": "markers",
                "x": [row[x_col] for row in filtered_data],
                "y": [row[y_col] for row in filtered_data],
                "marker": {"size": 10}
            }
            
            plotly_config["data"].append(trace)
    
    elif chart_type == "pie":
        labels = [str(row[x_col]) for row in filtered_data]
        values = [row[y_col] for row in filtered_data]
        
        trace = {
            "type": "pie",
            "labels": labels,
            "values": values,
            "textinfo": "label+percent",
            "hoverinfo": "label+value+percent"
        }
        
        plotly_config["data"].append(trace)
        # Adjust layout for pie chart
        plotly_config["layout"]["showlegend"] = True
    
    elif chart_type == "histogram":
        trace = {
            "type": "histogram",
            "x": [row[x_col] for row in filtered_data],
            "opacity": 0.7,
            "histnorm": "probability"
        }
        
        plotly_config["data"].append(trace)
        # Adjust layout for histogram
        plotly_config["layout"]["bargap"] = 0.05
    
    elif chart_type == "box":
        if color_col:
            # Group by color column
            color_groups = {}
            for row in filtered_data:
                color_value = str(row.get(color_col, "Unknown"))
                if color_value not in color_groups:
                    color_groups[color_value] = []
                color_groups[color_value].append(row)
            
            # Create a trace for each color group
            for color_value, group_data in color_groups.items():
                trace = {
                    "type": "box",
                    "name": color_value,
                    "y": [row[y_col] for row in group_data],
                    "boxpoints": "outliers"
                }
                
                plotly_config["data"].append(trace)
        else:
            trace = {
                "type": "box",
                "y": [row[y_col] for row in filtered_data],
                "boxpoints": "outliers"
            }
            
            plotly_config["data"].append(trace)
    
    return {
        "chart_type": chart_type,
        "title": title or f"{y_col} by {x_col}",
        "plotly": plotly_config,
        "fallback_table": fallback_table
    }