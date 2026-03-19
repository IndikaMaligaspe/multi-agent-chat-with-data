/**
 * Utility functions for widget operations
 */

/**
 * Check if data is likely to be tabular
 *
 * @param {Array|Object} data - The data to check
 * @returns {boolean} - True if data appears to be tabular
 */
export const isTabularData = (data) => {
  if (!data || !Array.isArray(data) || data.length === 0) {
    return false;
  }

  // Check if all items are objects with similar structure
  const firstItem = data[0];
  if (typeof firstItem !== "object" || firstItem === null) {
    return false;
  }

  // For very small arrays with object items, assume they're tabular
  if (data.length <= 3 && Object.keys(firstItem).length >= 2) {
    return true;
  }

  // For larger arrays, check if structure is consistent
  const firstItemKeys = Object.keys(firstItem);
  const consistentStructure = data.every((item) => {
    if (typeof item !== "object" || item === null) return false;
    const itemKeys = Object.keys(item);
    // Allow some flexibility - at least 70% of keys should match
    const matchingKeys = itemKeys.filter((key) => firstItemKeys.includes(key));
    return matchingKeys.length >= 0.7 * firstItemKeys.length;
  });

  return consistentStructure;
};

/**
 * Check if data is likely to be aggregation data (single value or small set of metrics)
 *
 * @param {Array|Object} data - The data to check
 * @returns {boolean} - True if data appears to be an aggregation
 */
export const isAggregationData = (data) => {
  // Case 1: Single object with 1-2 properties
  if (data && typeof data === "object" && !Array.isArray(data)) {
    const keys = Object.keys(data);
    return keys.length <= 2;
  }

  // Case 2: Array with single object with 1-2 properties
  if (Array.isArray(data) && data.length === 1 && typeof data[0] === "object") {
    const keys = Object.keys(data[0]);
    return keys.length <= 2;
  }

  // Case 3: Single numeric or string value
  if (
    typeof data === "number" ||
    (typeof data === "string" && !isNaN(parseFloat(data)))
  ) {
    return true;
  }

  return false;
};

/**
 * Check if data is likely to be comparison data (pairs of values)
 *
 * @param {Array|Object} data - The data to check
 * @returns {boolean} - True if data appears to be comparison data
 */
export const isComparisonData = (data) => {
  if (!data || !Array.isArray(data)) {
    return false;
  }

  // Check for array of objects with consistent keys including a label/name and value
  const hasNameValuePattern = data.every((item) => {
    if (typeof item !== "object" || item === null) return false;
    const keys = Object.keys(item);

    // Look for common name/value patterns
    const hasNameKey = keys.some((key) =>
      ["name", "label", "category", "key", "id"].includes(key.toLowerCase()),
    );

    const hasValueKey = keys.some((key) =>
      ["value", "count", "amount", "total", "sum", "quantity"].includes(
        key.toLowerCase(),
      ),
    );

    return hasNameKey && hasValueKey && keys.length <= 4; // Comparison data typically has few columns
  });

  return hasNameValuePattern && data.length >= 2 && data.length <= 10;
};

/**
 * Normalize tabular data to expected format
 *
 * @param {Array} data - The raw data
 * @returns {Object} - Normalized data with headers and rows
 */
export const normalizeTabularData = (data) => {
  if (!Array.isArray(data) || data.length === 0) {
    return { headers: [], rows: [] };
  }

  // Extract all unique column headers
  const headers = Array.from(
    new Set(data.flatMap((item) => Object.keys(item))),
  );

  // Create rows with consistent structure
  const rows = data.map((item) => {
    return headers.map((header) => {
      const value = item[header];
      // Handle null/undefined values
      return value === undefined || value === null ? "" : value;
    });
  });

  return { headers, rows };
};

/**
 * Format a value based on its type for display
 *
 * @param {any} value - The value to format
 * @param {string} type - Optional type hint
 * @returns {string} - Formatted value
 */
export const formatValue = (value, type = null) => {
  if (value === undefined || value === null) {
    return "";
  }

  // Try to infer type if not provided
  const valueType = type || typeof value;

  switch (valueType) {
    case "number":
      return Number.isInteger(value) ? value.toString() : value.toFixed(2);

    case "boolean":
      return value ? "Yes" : "No";

    case "object":
      if (value instanceof Date) {
        return value.toLocaleString();
      }
      if (Array.isArray(value)) {
        return value.join(", ");
      }
      return JSON.stringify(value);

    case "string":
      // Check if it's a date string
      const dateTest = new Date(value);
      if (
        !isNaN(dateTest) &&
        value.includes("-") &&
        (value.includes(":") || value.length >= 10)
      ) {
        return new Date(value).toLocaleString();
      }

      // Check if it's a numeric string
      if (!isNaN(parseFloat(value)) && valueType !== "number") {
        const num = parseFloat(value);
        return Number.isInteger(num) ? num.toString() : num.toFixed(2);
      }
      return value;

    default:
      return String(value);
  }
};

/**
 * Validate widget data against expected structure
 *
 * @param {Object} data - Widget data to validate
 * @param {string} widgetType - Type of widget
 * @returns {Object} - Validation result with isValid flag and errors
 */
export const validateWidgetData = (data, widgetType) => {
  const result = {
    isValid: true,
    errors: [],
  };

  if (!data) {
    result.isValid = false;
    result.errors.push("Widget data is missing");
    return result;
  }

  // Common validation for all widgets
  if (typeof data !== "object") {
    result.isValid = false;
    result.errors.push("Widget data must be an object");
    return result;
  }

  // Widget-specific validation
  switch (widgetType) {
    case "table":
      if (!data.headers || !Array.isArray(data.headers)) {
        result.isValid = false;
        result.errors.push("Table widget requires headers array");
      }

      if (!data.rows || !Array.isArray(data.rows)) {
        result.isValid = false;
        result.errors.push("Table widget requires rows array");
      } else if (data.rows.length > 0 && data.headers) {
        // Validate row consistency
        const headerCount = data.headers.length;
        const inconsistentRows = data.rows.filter(
          (row) => !Array.isArray(row) || row.length !== headerCount,
        );

        if (inconsistentRows.length > 0) {
          result.isValid = false;
          result.errors.push(
            `${inconsistentRows.length} rows have inconsistent column count`,
          );
        }
      }
      break;

    case "aggregation":
      if (!data.value && data.value !== 0) {
        result.isValid = false;
        result.errors.push("Aggregation widget requires a value");
      }
      break;

    case "comparison":
      if (!data.items || !Array.isArray(data.items) || data.items.length < 2) {
        result.isValid = false;
        result.errors.push("Comparison widget requires at least 2 items");
      }
      break;

    case "confirmation":
      if (!data.message) {
        result.isValid = false;
        result.errors.push("Confirmation widget requires a message");
      }

      if (
        !data.options ||
        !Array.isArray(data.options) ||
        data.options.length < 2
      ) {
        result.isValid = false;
        result.errors.push("Confirmation widget requires at least 2 options");
      }
      break;

    case "options":
      if (
        !data.options ||
        !Array.isArray(data.options) ||
        data.options.length === 0
      ) {
        result.isValid = false;
        result.errors.push("Options widget requires options array");
      }
      break;

    case "text":
      if (!data.text && data.text !== "") {
        result.isValid = false;
        result.errors.push("Text widget requires text content");
      }
      break;
  }

  return result;
};

/**
 * Determine if a new widget should replace an existing widget
 * This helps resolve the issue where new widgets weren't properly replacing old ones
 *
 * @param {Object} existingWidget - The current widget being displayed
 * @param {Object} newWidget - The new widget to potentially display
 * @param {Object} options - Additional context options
 * @returns {boolean} - Whether the new widget should replace the existing one
 */
export const shouldReplaceWidget = (
  existingWidget,
  newWidget,
  options = {},
) => {
  console.log("[DEBUG] Evaluating widget replacement:", {
    existing: existingWidget ? existingWidget.type : "none",
    new: newWidget ? newWidget.type : "none",
    options,
  });

  // If no existing widget, always show the new widget
  if (!existingWidget) {
    console.log("[DEBUG] No existing widget, showing new widget");
    return true;
  }

  // If this is fresh data from a forced refresh, always replace
  if (newWidget.metadata && newWidget.metadata.freshData) {
    console.log("[DEBUG] Fresh data detected, forcing widget replacement");
    return true;
  }

  // If widgets have explicit IDs and they match, always replace
  if (
    existingWidget.widgetId &&
    newWidget.widgetId &&
    existingWidget.widgetId === newWidget.widgetId
  ) {
    console.log("[DEBUG] Matching widget IDs, replacing widget");
    return true;
  }

  // Check if this is a continuation of the same data
  if (options.isSameQuery) {
    console.log("[DEBUG] Same query detected, updating with latest data");
    // For the same query, always update with latest data
    return true;
  }

  // Check if forceRefresh flag is set
  if (options.forceRefresh) {
    console.log("[DEBUG] Force refresh flag set, replacing widget");
    return true;
  }

  // Different widget types should be evaluated based on context
  if (existingWidget.type !== newWidget.type) {
    console.log("[DEBUG] Different widget types detected", {
      existing: existingWidget.type,
      new: newWidget.type,
    });

    // If transitioning from a simpler widget type (like aggregation)
    // to a more detailed one (like table), allow the replacement
    if (
      (existingWidget.type === "aggregation" && newWidget.type === "table") ||
      (existingWidget.type === "text" &&
        ["table", "aggregation", "comparison"].includes(newWidget.type))
    ) {
      console.log("[DEBUG] Allowing transition to more detailed widget");
      return true;
    }
  }

  // Check for explicit widget refresh timestamp
  if (
    newWidget.refreshTimestamp &&
    (!existingWidget.refreshTimestamp ||
      newWidget.refreshTimestamp > existingWidget.refreshTimestamp)
  ) {
    console.log("[DEBUG] Newer refresh timestamp detected, replacing widget");
    return true;
  }

  // By default, different queries should show different widgets
  const result = options.forceReplace || false;
  console.log("[DEBUG] Widget replacement decision:", result);
  return result;
};

export default {
  isTabularData,
  isAggregationData,
  isComparisonData,
  normalizeTabularData,
  formatValue,
  validateWidgetData,
  shouldReplaceWidget,
};
