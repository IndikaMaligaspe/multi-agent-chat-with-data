import React, { useState } from "react";
import PropTypes from "prop-types";
import "./ComparisonWidget.css";

/**
 * ComparisonWidget - Displays comparative data with bar/chart visualization
 *
 * Used for visualizing comparisons between items, like:
 * - Grouped data (e.g., customers by country)
 * - Time series comparisons
 * - Side-by-side metrics
 */
const ComparisonWidget = ({ data, metadata = {} }) => {
  // Extract data properties
  const {
    title = "",
    items = [],
    maxItems = 10, // Default limit to prevent overflow
  } = data;

  // Extract metadata with defaults
  const {
    chartType = "bar", // 'bar', 'pie', 'horizontal'
    showValues = true,
    showPercentages = false,
    sortBy = "value", // 'value', 'label', 'none'
    sortDirection = "desc", // 'asc', 'desc'
    valueFormat = "number", // 'number', 'currency', 'percentage', 'decimal'
    precision = 0,
    currencySymbol = "$",
    barColor = "#1890ff",
    colorScheme = [
      "#1890ff",
      "#52c41a",
      "#faad14",
      "#f5222d",
      "#722ed1",
      "#13c2c2",
    ],
    enableToggle = items.length > maxItems,
  } = metadata;

  // State for managing expanded view
  const [showAll, setShowAll] = useState(false);

  // Format values based on specified format
  const formatValue = (val) => {
    if (val === null || val === undefined) return "N/A";

    switch (valueFormat) {
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

  // Sort the items
  const sortedItems = [...items].sort((a, b) => {
    if (sortBy === "none") return 0;

    const aValue = sortBy === "label" ? a.label : a.value;
    const bValue = sortBy === "label" ? b.label : b.value;

    if (typeof aValue === "string" && typeof bValue === "string") {
      return sortDirection === "asc"
        ? aValue.localeCompare(bValue)
        : bValue.localeCompare(aValue);
    } else {
      return sortDirection === "asc" ? aValue - bValue : bValue - aValue;
    }
  });

  // Limit the number of items shown based on maxItems and showAll
  const displayItems = showAll ? sortedItems : sortedItems.slice(0, maxItems);

  // Calculate the maximum value for scaling
  const maxValue = Math.max(...sortedItems.map((item) => item.value));
  const totalValue = sortedItems.reduce((sum, item) => sum + item.value, 0);

  // Generate chart bars
  const renderChart = () => {
    switch (chartType) {
      case "horizontal":
        return (
          <div className="comparison-chart horizontal">
            {displayItems.map((item, index) => {
              const percentage = (item.value / maxValue) * 100;
              const barStyle = {
                width: `${percentage}%`,
                backgroundColor:
                  colorScheme[index % colorScheme.length] || barColor,
              };

              return (
                <div className="comparison-item" key={index}>
                  <div className="comparison-label">{item.label}</div>
                  <div className="comparison-bar-container">
                    <div className="comparison-bar" style={barStyle}>
                      {showValues && (
                        <span className="comparison-value">
                          {formatValue(item.value)}
                          {showPercentages &&
                            ` (${Math.round((item.value / totalValue) * 100)}%)`}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        );

      case "pie":
        // Simple CSS pie chart implementation
        let cumulativePercentage = 0;

        return (
          <div className="comparison-pie-container">
            <div className="comparison-pie">
              <div
                className="comparison-pie-chart"
                style={{
                  // Create a conic gradient from the color slices
                  background: `conic-gradient(${displayItems
                    .map((item, index) => {
                      const percentage = (item.value / totalValue) * 100;
                      const color =
                        colorScheme[index % colorScheme.length] || barColor;
                      const start = cumulativePercentage;
                      cumulativePercentage += percentage;
                      return `${color} ${start}% ${cumulativePercentage}%`;
                    })
                    .join(", ")})`,
                }}
              />
            </div>

            <div className="comparison-pie-legend">
              {displayItems.map((item, index) => {
                const percentage = (item.value / totalValue) * 100;
                const color =
                  colorScheme[index % colorScheme.length] || barColor;

                return (
                  <div className="legend-item" key={index}>
                    <div
                      className="legend-color"
                      style={{ backgroundColor: color }}
                    />
                    <div className="legend-label">{item.label}</div>
                    <div className="legend-value">
                      {formatValue(item.value)}
                      {showPercentages && ` (${Math.round(percentage)}%)`}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );

      case "bar":
      default:
        return (
          <div className="comparison-chart vertical">
            {displayItems.map((item, index) => {
              const percentage = (item.value / maxValue) * 100;
              const barStyle = {
                height: `${percentage}%`,
                backgroundColor:
                  colorScheme[index % colorScheme.length] || barColor,
              };

              return (
                <div className="comparison-item" key={index}>
                  <div className="comparison-bar-container">
                    <div className="comparison-bar" style={barStyle}>
                      {showValues && (
                        <span className="comparison-value">
                          {formatValue(item.value)}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="comparison-label">{item.label}</div>
                  {showPercentages && (
                    <div className="comparison-percentage">
                      {Math.round((item.value / totalValue) * 100)}%
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        );
    }
  };

  // Empty state
  if (!items.length) {
    return (
      <div className="comparison-widget comparison-empty-state">
        <div className="empty-message">No comparative data available</div>
      </div>
    );
  }

  return (
    <div className="comparison-widget">
      {title && <h3 className="comparison-title">{title}</h3>}

      {renderChart()}

      {enableToggle && (
        <button
          className="comparison-toggle"
          onClick={() => setShowAll(!showAll)}
        >
          {showAll ? "Show Less" : `Show All (${items.length})`}
        </button>
      )}
    </div>
  );
};

// PropTypes for documentation and type checking
ComparisonWidget.propTypes = {
  data: PropTypes.shape({
    title: PropTypes.string,
    items: PropTypes.arrayOf(
      PropTypes.shape({
        label: PropTypes.string.isRequired,
        value: PropTypes.number.isRequired,
      }),
    ),
    maxItems: PropTypes.number,
  }),
  metadata: PropTypes.shape({
    chartType: PropTypes.oneOf(["bar", "pie", "horizontal"]),
    showValues: PropTypes.bool,
    showPercentages: PropTypes.bool,
    sortBy: PropTypes.oneOf(["value", "label", "none"]),
    sortDirection: PropTypes.oneOf(["asc", "desc"]),
    valueFormat: PropTypes.oneOf([
      "number",
      "currency",
      "percentage",
      "decimal",
    ]),
    precision: PropTypes.number,
    currencySymbol: PropTypes.string,
    barColor: PropTypes.string,
    colorScheme: PropTypes.arrayOf(PropTypes.string),
    enableToggle: PropTypes.bool,
  }),
  onAction: PropTypes.func,
};

// Default props
ComparisonWidget.defaultProps = {
  data: {
    title: "",
    items: [],
    maxItems: 10,
  },
  metadata: {
    chartType: "bar",
    showValues: true,
    showPercentages: false,
    sortBy: "value",
    sortDirection: "desc",
    valueFormat: "number",
    precision: 0,
    currencySymbol: "$",
    barColor: "#1890ff",
    colorScheme: [
      "#1890ff",
      "#52c41a",
      "#faad14",
      "#f5222d",
      "#722ed1",
      "#13c2c2",
    ],
  },
};

export default ComparisonWidget;
