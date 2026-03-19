/**
 * API service for backend communication with widget support
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

/**
 * Simple string hashing function to generate a deterministic hash for cache control
 *
 * @param {string} str - String to hash
 * @returns {string} - Hash of the string
 */
function hashString(str) {
  let hash = 0;
  if (str.length === 0) return hash.toString();

  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash; // Convert to 32bit integer
  }

  return Math.abs(hash).toString(16);
}

/**
 * Process API response data with standardized handling for all widget types.
 *
 * @param {Object} data - Raw response data from API
 * @param {Object} options - Processing options including previous widget state
 * @returns {Object} - Processed response data
 */
export const processResponseData = (data, options = {}) => {
  if (!data) {
    console.warn("No response data to process");
    return data;
  }

  // Early return if data is not a successful response with answer
  if (!data.success || !data.answer) {
    return data;
  }

  console.log("[DEBUG] Processing API response data:", data);
  console.log("[DEBUG] Processing options:", options);

  try {
    // Extract the answer object for easier access
    const { answer } = data;

    // Add a freshness flag if this is from a forced refresh
    if (options.forceRefresh) {
      if (!answer.metadata) {
        answer.metadata = {};
      }
      answer.metadata.freshData = true;
      answer.metadata.refreshTimestamp = new Date().toISOString();
    }

    // Process widget data
    if (answer.data) {
      // Handle stringified JSON data
      if (
        typeof answer.data === "string" &&
        (answer.data.startsWith("[") || answer.data.startsWith("{"))
      ) {
        try {
          console.log("[DEBUG] Parsing stringified answer.data:", answer.data);
          answer.data = JSON.parse(answer.data);
          console.log("[DEBUG] Successfully parsed answer.data:", answer.data);
        } catch (err) {
          console.error("[DEBUG] Failed to parse answer.data:", err);

          // Add error metadata but preserve original data
          answer.metadata = {
            ...(answer.metadata || {}),
            parseError: true,
            errorMessage: err.message,
          };
        }
      }

      // Add widget type metadata if not present
      if (!answer.metadata) {
        answer.metadata = {};
      }

      // Only infer widget type when the API did not provide one
      if (!answer.metadata.widgetType) {
        let inferredWidgetType = null;

        if (Array.isArray(answer.data)) {
          if (answer.data.length > 0 && typeof answer.data[0] === "object") {
            inferredWidgetType = "table";
          } else {
            inferredWidgetType = "aggregation";
          }
        } else if (typeof answer.data === "object") {
          if (
            (answer.data.columns || answer.data.headers) &&
            answer.data.rows
          ) {
            inferredWidgetType = "table";
          } else if (answer.data.items) {
            inferredWidgetType = "comparison";
          } else {
            inferredWidgetType = "aggregation";
          }
        } else {
          inferredWidgetType = "text";
        }

        answer.metadata.widgetType = inferredWidgetType;
        console.log(
          "[DEBUG] Setting missing widget type (inferred):",
          inferredWidgetType,
        );
      } else {
        console.log(
          "[DEBUG] Using API-provided widget type:",
          answer.metadata.widgetType,
        );
      }

      // Add widget state transition metadata
      if (
        options.previousWidgetType &&
        options.previousWidgetType !== answer.metadata.widgetType
      ) {
        answer.metadata.widgetTransition = {
          from: options.previousWidgetType,
          to: answer.metadata.widgetType,
          timestamp: new Date().toISOString(),
          forced: !!options.forceRefresh, // Flag if this was a forced transition
        };

        console.log(
          "[DEBUG] Widget transition detected:",
          answer.metadata.widgetTransition,
        );
      }

      // Validate data structure for specific widget types
      switch (answer.metadata.widgetType) {
        case "table":
          console.log("[DEBUG] Processing table data:", answer.data);

          // Handle multiple table data formats
          if (Array.isArray(answer.data)) {
            // Convert array of objects to table format
            if (answer.data.length > 0 && typeof answer.data[0] === "object") {
              const headers = Object.keys(answer.data[0]);
              const rows = answer.data.map((item) =>
                headers.map((header) => item[header] ?? ""),
              );
              answer.data = { headers, rows };
              console.log(
                "[DEBUG] Converted array data to table format:",
                answer.data,
              );
            }
          } else if (answer.data && typeof answer.data === "object") {
            // Handle data with 'columns' instead of 'headers'
            if (
              answer.data.columns &&
              answer.data.rows &&
              !answer.data.headers
            ) {
              console.log("[DEBUG] Converting 'columns' to 'headers' format");
              answer.data.headers = answer.data.columns;
              // Preserve columns for compatibility but headers is the standard
            }

            // Handle rows as array of objects instead of array of arrays
            if (
              answer.data.rows &&
              Array.isArray(answer.data.rows) &&
              answer.data.rows.length > 0 &&
              typeof answer.data.rows[0] === "object" &&
              !Array.isArray(answer.data.rows[0])
            ) {
              console.log("[DEBUG] Converting rows from objects to arrays");
              const headers =
                answer.data.headers ||
                answer.data.columns ||
                Object.keys(answer.data.rows[0]);

              // Convert to array format
              answer.data.headers = headers;
              const newRows = answer.data.rows.map((row) =>
                headers.map((header) => row[header] ?? ""),
              );
              answer.data.rows = newRows;
              console.log("[DEBUG] Converted row objects to arrays");
            }
          }

          // Final validation - ensure we have both headers and rows
          if (!answer.data.headers || !answer.data.rows) {
            console.error(
              "[DEBUG] Table data incomplete after processing:",
              answer.data,
            );
          }
          break;

        case "aggregation":
          // Ensure aggregation data is not an array with a single object
          if (Array.isArray(answer.data) && answer.data.length === 1) {
            answer.data = answer.data[0];
            console.log(
              "[DEBUG] Extracted single item from aggregation array:",
              answer.data,
            );
          }

          // Ensure numeric values are treated as numbers
          if (
            answer.data &&
            answer.data.value &&
            typeof answer.data.value === "string"
          ) {
            if (!isNaN(Number(answer.data.value))) {
              answer.data.value = Number(answer.data.value);
              console.log(
                "[DEBUG] Converted string value to number:",
                answer.data.value,
              );
            }
          }
          break;

        // Add other widget type validations as needed
      }
    }

    // Add processing timestamp and query info for caching control
    data.processedAt = new Date().toISOString();

    // Add original query for comparison purposes
    if (options.query) {
      data.originalQuery = options.query;
    }

    // Add refresh metadata
    data.refreshInfo = {
      wasForced: !!options.forceRefresh,
      timestamp: new Date().getTime(),
      queryHash: options.query ? hashString(options.query) : null,
    };
  } catch (error) {
    console.error("Error processing response data:", error);
    console.error("Error processing details:", {
      message: error.message,
      stack: error.stack,
      name: error.name,
      dataType: typeof data,
      dataKeys: data ? Object.keys(data) : [],
      options: options,
    });

    // Add error metadata but don't alter the data structure
    data.processingError = {
      message: error.message,
      stack: error.stack,
      timestamp: new Date().toISOString(),
    };
  }

  return data;
};

/**
 * Send a query to the backend
 *
 * @param {string} query - The user's query
 * @param {Object} options - Additional options
 * @returns {Promise<Object>} - The response data
 */
export const sendQuery = async (query, options = {}) => {
  const url = `${API_BASE_URL}/query`;

  // Prevent request caching by appending a timestamp to the URL if forceRefresh is enabled
  const urlWithCacheBust = options.forceRefresh
    ? `${url}?_t=${new Date().getTime()}`
    : url;

  console.log(`[DEBUG] Sending API request to ${urlWithCacheBust}`);
  console.log(`[DEBUG] Request options:`, options);

  try {
    const response = await fetch(urlWithCacheBust, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // Add cache control headers to prevent caching
        "Cache-Control": "no-cache, no-store, must-revalidate",
        Pragma: "no-cache",
        Expires: "0",
        ...(options.headers || {}),
      },
      // Pass the query and additional data with cache-busting timestamp
      body: JSON.stringify({
        query,
        _timestamp: new Date().getTime(), // Add timestamp to payload to ensure unique requests
        ...options.additionalData,
      }),
    });

    console.log(`[DEBUG] Response status:`, response.status);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API error (${response.status}): ${errorText}`);
    }

    const data = await response.json();
    console.log(`[DEBUG] Raw API response data:`, data);
    console.log(
      `[DEBUG] Raw API response data structure:`,
      JSON.stringify(data, null, 2),
    );

    // Process the response data with our enhanced helper function
    const processedData = processResponseData(data, {
      previousWidgetType: options.previousWidgetType,
      query: query,
      forceRefresh: options.forceRefresh,
    });

    console.log(`[DEBUG] Processed API response:`, processedData);
    console.log(
      `[DEBUG] Processed API response structure:`,
      JSON.stringify(processedData, null, 2),
    );

    // Detailed logging of the answer structure
    if (processedData?.answer) {
      console.log(`[DEBUG] Answer object structure:`, {
        type: processedData.answer.type,
        hasData: !!processedData.answer.data,
        dataType: typeof processedData.answer.data,
        dataKeys: processedData.answer.data
          ? Object.keys(processedData.answer.data)
          : [],
        hasMetadata: !!processedData.answer.metadata,
        metadataKeys: processedData.answer.metadata
          ? Object.keys(processedData.answer.metadata)
          : [],
        widgetType: processedData.answer.metadata?.widgetType,
      });

      // Log table-specific data if it's a table
      if (
        processedData.answer.metadata?.widgetType === "table" ||
        processedData.answer.type === "table"
      ) {
        console.log(`[DEBUG] Table data structure:`, {
          hasRows: !!processedData.answer.data?.rows,
          rowCount: processedData.answer.data?.rows?.length || 0,
          hasColumns: !!processedData.answer.data?.columns,
          columnCount: processedData.answer.data?.columns?.length || 0,
          hasHeaders: !!processedData.answer.data?.headers,
          headerCount: processedData.answer.data?.headers?.length || 0,
          firstRow: processedData.answer.data?.rows?.[0] || null,
        });
      }
    }

    return processedData;
  } catch (error) {
    console.error("Query API error:", error);
    console.error("Query API error details:", {
      message: error.message,
      stack: error.stack,
      name: error.name,
      query: query,
      url: urlWithCacheBust,
      options: options,
      timestamp: new Date().toISOString(),
    });
    throw error;
  }
};

/**
 * Send widget action data to the backend
 *
 * @param {string} endpoint - API endpoint for the action
 * @param {Object} actionData - The action data
 * @param {Object} options - Additional options including previous widget state
 * @returns {Promise<Object>} - The processed response data
 */
export const sendWidgetAction = async (endpoint, actionData, options = {}) => {
  const url = `${API_BASE_URL}/${endpoint}`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      body: JSON.stringify(actionData),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API error (${response.status}): ${errorText}`);
    }

    const data = await response.json();

    // Process the response with the same helper function for consistency
    const processedData = processResponseData(data, {
      previousWidgetType: options.previousWidgetType,
      widgetAction: endpoint,
      actionData: actionData,
    });

    return processedData;
  } catch (error) {
    console.error("Widget action API error:", error);
    console.error("Widget action API error details:", {
      message: error.message,
      stack: error.stack,
      name: error.name,
      endpoint: endpoint,
      actionDataType: typeof actionData,
      actionDataKeys: actionData ? Object.keys(actionData) : [],
      options: options,
    });
    throw error;
  }
};

/**
 * Get database schema information
 *
 * @returns {Promise<Object>} - The processed schema data
 */
export const getSchema = async () => {
  const url = `${API_BASE_URL}/schema`;

  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API error (${response.status}): ${errorText}`);
    }

    const data = await response.json();

    // Process schema data for consistency
    const processedData = processResponseData(data, {
      schemaRequest: true,
    });

    return processedData;
  } catch (error) {
    console.error("Schema API error:", error);
    console.error("Schema API error details:", {
      message: error.message,
      stack: error.stack,
      name: error.name,
      url: url,
      timestamp: new Date().toISOString(),
    });
    throw error;
  }
};

/**
 * Ping the server to check health status
 *
 * @returns {Promise<Object>} - Processed health check response
 */
export const healthCheck = async () => {
  const url = `${API_BASE_URL}/health`;

  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Health check failed (${response.status}): ${errorText}`);
    }

    const data = await response.json();

    // For consistency, process health check data as well
    // This helps with tracking widget transitions even in system responses
    const processedData = processResponseData(data, {
      healthCheck: true,
    });

    return processedData;
  } catch (error) {
    console.error("Health check error:", error);
    console.error("Health check error details:", {
      message: error.message,
      stack: error.stack,
      name: error.name,
      url: url,
      timestamp: new Date().toISOString(),
    });
    throw error;
  }
};

const api = {
  sendQuery,
  sendWidgetAction,
  getSchema,
  healthCheck,
};

export default api;
