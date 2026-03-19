import React from "react";
import PropTypes from "prop-types";
import "./AggregationWidget.css";

/**
 * AggregationWidget - Displays a single aggregated value with styling and context
 *
 * Used for displaying metrics like counts, sums, averages, etc. with
 * appropriate visual emphasis and contextual information.
 */
const AggregationWidget = ({ data, metadata = {} }) => {
  // Log the raw data for debugging
  console.log("AggregationWidget received data:", data);
  console.log("AggregationWidget received metadata:", metadata);

  // Handle string data (parse if possible)
  let processedData = data;
  if (typeof data === "string") {
    try {
      console.log("Trying to parse string data in AggregationWidget:", data);
      processedData = JSON.parse(data);
      console.log("Successfully parsed data:", processedData);
    } catch (e) {
      console.error("Failed to parse data in AggregationWidget:", e);
    }
  }

  // Extract data properties with fallbacks
  const {
    value = 0,
    label = "",
    unit = "",
    previousValue = null,
    description = "",
  } = typeof processedData === "object" && processedData !== null
    ? processedData
    : { value: processedData }; // Handle case where data is just the value

  // Log the extracted properties
  console.log("AggregationWidget using properties:", {
    value,
    label,
    unit,
    previousValue,
    description,
  });

  // Extract metadata with defaults
  const {
    format = "number", // 'number', 'currency', 'percentage', 'decimal'
    colorCode = false, // Whether to color positive/negative values
    showTrend = previousValue !== null,
    trendUpIsGood = true, // Whether up trend is positive or negative
    size = "medium", // 'small', 'medium', 'large'
    precision = 2, // Decimal precision
    currencySymbol = "$",
  } = metadata;

  // Format value based on specified format
  const formatValue = (val) => {
    if (val === null || val === undefined) return "N/A";

    switch (format) {
      case "currency":
        return `${currencySymbol}${Number(val).toLocaleString(undefined, {
          minimumFractionDigits: precision,
          maximumFractionDigits: precision,
        })}`;

      case "percentage":
        return `${Number(val).toLocaleString(undefined, {
          minimumFractionDigits: precision,
          maximumFractionDigits: precision,
        })}%`;

      case "decimal":
        return Number(val).toLocaleString(undefined, {
          minimumFractionDigits: precision,
          maximumFractionDigits: precision,
        });

      case "number":
      default:
        return Number(val).toLocaleString();
    }
  };

  // Calculate trend
  const calculateTrend = () => {
    if (previousValue === null || value === null) return null;

    // Calculate percentage change
    const change = value - previousValue;
    const percentChange =
      previousValue !== 0
        ? ((change / Math.abs(previousValue)) * 100).toFixed(1)
        : 0;

    // Determine direction
    const direction = change > 0 ? "up" : change < 0 ? "down" : "neutral";

    // Determine if this is good or bad
    const isPositive =
      (direction === "up" && trendUpIsGood) ||
      (direction === "down" && !trendUpIsGood);

    return {
      direction,
      percentChange,
      isPositive,
    };
  };

  const trend = showTrend ? calculateTrend() : null;

  // Generate CSS classes
  const containerClasses = [
    "aggregation-widget",
    `size-${size}`,
    colorCode && trend?.direction !== "neutral"
      ? trend?.isPositive
        ? "positive"
        : "negative"
      : "",
  ]
    .filter(Boolean)
    .join(" ");

  // Add extra styling for better visual appearance
  const valueStyle = {
    fontSize: "2.8rem",
    fontWeight: "bold",
    color: "#4a6cf7",
    marginBottom: "0.5rem",
    textShadow: "0 1px 2px rgba(0,0,0,0.05)",
  };

  const labelStyle = {
    fontSize: "1.2rem",
    fontWeight: "500",
    color: "#555",
    marginBottom: "0.75rem",
  };

  const widgetStyle = {
    padding: "1.5rem",
    borderRadius: "12px",
    boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
    background: "linear-gradient(to bottom, #ffffff, #f9fafc)",
    border: "1px solid #eaedf7",
    minWidth: "200px",
    transition: "all 0.3s ease",
  };

  // Generate trend arrow and color
  const getTrendIndicator = () => {
    if (!trend) return null;

    const { direction, percentChange, isPositive } = trend;
    const trendClass = `trend-${direction} ${isPositive ? "positive" : "negative"}`;

    return (
      <div className={`trend-indicator ${trendClass}`}>
        {direction === "up" && <span className="trend-arrow">↑</span>}
        {direction === "down" && <span className="trend-arrow">↓</span>}
        <span className="trend-value">{Math.abs(percentChange)}%</span>
      </div>
    );
  };

  return (
    <div className={containerClasses} style={widgetStyle}>
      {label && (
        <div className="aggregation-label" style={labelStyle}>
          {label}
        </div>
      )}

      <div className="aggregation-value-container">
        <div className="aggregation-value">
          <span className="value" style={valueStyle}>
            {formatValue(value)}
          </span>
          {unit && (
            <span className="unit" style={{ fontSize: "1rem", color: "#777" }}>
              {unit}
            </span>
          )}
        </div>

        {getTrendIndicator()}
      </div>

      {description && (
        <div
          className="aggregation-description"
          style={{ marginTop: "0.75rem", color: "#666" }}
        >
          {description}
        </div>
      )}

      {previousValue !== null && (
        <div
          className="aggregation-previous"
          style={{ marginTop: "0.5rem", fontSize: "0.9rem", color: "#888" }}
        >
          Previous: {formatValue(previousValue)} {unit}
        </div>
      )}
    </div>
  );
};

// PropTypes for documentation and type checking
AggregationWidget.propTypes = {
  data: PropTypes.shape({
    value: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
    label: PropTypes.string,
    unit: PropTypes.string,
    previousValue: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    description: PropTypes.string,
  }),
  metadata: PropTypes.shape({
    format: PropTypes.oneOf(["number", "currency", "percentage", "decimal"]),
    colorCode: PropTypes.bool,
    showTrend: PropTypes.bool,
    trendUpIsGood: PropTypes.bool,
    size: PropTypes.oneOf(["small", "medium", "large"]),
    precision: PropTypes.number,
    currencySymbol: PropTypes.string,
  }),
  onAction: PropTypes.func, // Not used in AggregationWidget but included for consistency
};

// Default props
AggregationWidget.defaultProps = {
  data: {
    value: 0,
    label: "",
    unit: "",
    previousValue: null,
    description: "",
  },
  metadata: {
    format: "number",
    colorCode: false,
    showTrend: false,
    trendUpIsGood: true,
    size: "medium",
    precision: 2,
    currencySymbol: "$",
  },
};

export default AggregationWidget;
