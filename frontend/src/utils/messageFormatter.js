/**
 * Utilities for formatting messages and widget responses
 */

/**
 * Format a user message for display
 *
 * @param {string} content - The message content
 * @param {number} timestamp - Optional timestamp
 * @returns {Object} - Formatted user message
 */
export const formatUserMessage = (content, timestamp = Date.now()) => {
  return {
    content,
    isUser: true,
    timestamp,
  };
};

/**
 * Format an AI message for display
 *
 * @param {Object|string} response - The API response or content
 * @param {number} timestamp - Optional timestamp
 * @param {string} namespace - Optional agent namespace
 * @returns {Object} - Formatted AI message
 */
export const formatAIMessage = (
  response,
  timestamp = Date.now(),
  namespace = null,
) => {
  // Add extra debugging for formatAIMessage
  console.log("🔰 FORMAT AI MESSAGE CALLED with:", {
    responseType: typeof response,
    hasType: response && typeof response === "object" && !!response.type,
    hasWidgetType:
      response && typeof response === "object" && response.metadata?.widgetType,
  });

  // Handle string responses (legacy or fallback content)
  if (typeof response === "string") {
    return {
      content: response,
      isUser: false,
      timestamp,
      namespace,
    };
  }

  // Handle widget-formatted responses
  if (response && typeof response === "object") {
    // If it's already in our widget format, ensure type is set
    if (response.type || (response.metadata && response.metadata.widgetType)) {
      // Ensure type field is populated from metadata if missing
      if (!response.type && response.metadata?.widgetType) {
        console.log(
          "🔄 Setting type from metadata.widgetType in formatAIMessage",
        );
        response.type = response.metadata.widgetType;
      }

      console.log("📦 Returning widget with type:", response.type);
      return {
        content: response,
        isUser: false,
        timestamp,
        namespace,
      };
    }

    // If it's an API response object with final_answer field
    if (response.final_answer) {
      // The final_answer might itself be a widget object or a string
      return formatAIMessage(response.final_answer, timestamp, namespace);
    }
  }

  // Fallback for unexpected formats
  console.warn("Unexpected message format:", response);
  return {
    content:
      typeof response === "object"
        ? JSON.stringify(response, null, 2)
        : String(response),
    isUser: false,
    timestamp,
    namespace,
  };
};

/**
 * Parse a backend response into appropriately formatted messages
 *
 * @param {Object} response - The API response
 * @returns {Object} - The formatted message object
 */
export const parseResponse = (response) => {
  // Enhanced debugging
  console.log("======== PARSE RESPONSE DEBUGGING ========");
  console.log("Original API response:", response);
  console.log("Response type:", typeof response);

  // Handle stringified JSON responses
  if (
    typeof response === "string" &&
    (response.startsWith("{") || response.startsWith("["))
  ) {
    try {
      console.log("Response appears to be a JSON string, attempting to parse");
      response = JSON.parse(response);
      console.log("Successfully parsed response:", response);
    } catch (err) {
      console.error("Failed to parse response string:", err);
    }
  }

  // Detailed response structure analysis
  if (response && typeof response === "object") {
    console.log("Response keys:", Object.keys(response));

    if (response.success !== undefined) {
      console.log("Response includes success field:", response.success);
    }

    if (response.answer) {
      console.log("Answer field found:", response.answer);
      console.log("Answer type:", typeof response.answer);
      console.log("Answer keys:", Object.keys(response.answer || {}));

      // Check if answer.data is stringified
      if (
        typeof response.answer?.data === "string" &&
        (response.answer.data.startsWith("[") ||
          response.answer.data.startsWith("{"))
      ) {
        console.log("Answer data appears to be stringified JSON");
        try {
          const parsedData = JSON.parse(response.answer.data);
          console.log("Parsed answer data:", parsedData);

          // Automatically fix stringified data
          response.answer = {
            ...response.answer,
            data: parsedData,
          };
          console.log("Fixed answer with parsed data:", response.answer);
        } catch (err) {
          console.error("Failed to parse answer data:", err);
        }
      }
    }
  }
  console.log("======== END PARSE RESPONSE DEBUGGING ========");

  // Handle response with answer field (current API structure)
  if (response && response.answer) {
    console.log("Found answer field:", response.answer);

    // CRITICAL FIX: Check for already properly typed table widget first
    if (
      response.answer.type === "table" ||
      response.answer.metadata?.widgetType === "table"
    ) {
      console.log(
        "🔍 FOUND PROPERLY TYPED TABLE WIDGET, ensuring structure is complete",
      );

      // Ensure type is set explicitly
      if (!response.answer.type) {
        response.answer.type = "table";
      }

      // Ensure metadata contains the widgetType
      if (!response.answer.metadata) {
        response.answer.metadata = {};
      }

      response.answer.metadata.widgetType = "table";
      response.answer.metadata.forceRefresh = true;
      response.answer.metadata.freshData = true;
      response.answer.metadata.refreshTimestamp = new Date().toISOString();

      // Create a completely new object to ensure it's not referencing the old one
      const fixedTableWidget = {
        type: "table",
        data: response.answer.data,
        metadata: response.answer.metadata,
        fallback: response.answer.fallback || "Table data cannot be displayed",
      };

      console.log("⚡ RETURNING FIXED TABLE WIDGET:", fixedTableWidget);
      return formatAIMessage(fixedTableWidget);
    }

    // Check if this is a table structure without explicit type
    if (response.answer.data && !response.answer.type) {
      console.log(
        "Analyzing answer.data structure for potential table detection:",
        response.answer.data,
      );

      // Check for table structure indicators: has both rows and either columns or headers
      const hasRows = Array.isArray(response.answer.data.rows);
      const hasColumns = Array.isArray(response.answer.data.columns);
      const hasHeaders = Array.isArray(response.answer.data.headers);

      console.log("Table structure detection:", {
        hasRows,
        hasColumns,
        hasHeaders,
        rowsLength: hasRows ? response.answer.data.rows.length : 0,
        columnsLength: hasColumns ? response.answer.data.columns.length : 0,
        headersLength: hasHeaders ? response.answer.data.headers.length : 0,
      });

      // If it has table-like structure, transform it to a proper table widget
      if (hasRows && (hasColumns || hasHeaders)) {
        console.log(
          "📊 DETECTED TABLE STRUCTURE! Creating table widget from data",
        );

        // Create a proper table widget structure
        const tableWidget = {
          type: "table", // Explicitly set the type to table
          data: response.answer.data,
          metadata: response.answer.metadata || {
            sortable: true,
            freshData: true,
            refreshTimestamp: new Date().toISOString(),
            widgetType: "table", // Ensure widgetType is set in metadata
            title: "Table Data",
          },
          fallback:
            response.answer.fallback || "Table data cannot be displayed",
        };

        console.log("Created explicit table widget:", tableWidget);
        return formatAIMessage(tableWidget);
      }
      // Check if the answer.data itself IS the table structure (not nested)
      else if (hasRows || hasColumns || hasHeaders) {
        console.log("📊 DETECTED FLAT TABLE STRUCTURE! Creating table widget");

        const tableWidget = {
          type: "table",
          data: response.answer.data,
          metadata: response.answer.metadata || {
            sortable: true,
            freshData: true,
            refreshTimestamp: new Date().toISOString(),
            widgetType: "table",
            title: "Table Data",
          },
          fallback:
            response.answer.fallback || "Table data cannot be displayed",
        };

        console.log(
          "Created explicit table widget from flat structure:",
          tableWidget,
        );
        return formatAIMessage(tableWidget);
      }
    }

    // Check if answer IS the data (not nested in .data)
    if (!response.answer.data && !response.answer.type) {
      console.log("Checking if answer itself is table data without nesting");

      // Check for table structure indicators directly on the answer
      const hasRows = Array.isArray(response.answer.rows);
      const hasColumns = Array.isArray(response.answer.columns);
      const hasHeaders = Array.isArray(response.answer.headers);

      console.log("Direct table structure detection:", {
        hasRows,
        hasColumns,
        hasHeaders,
      });

      if (hasRows && (hasColumns || hasHeaders)) {
        console.log(
          "📊 DETECTED DIRECT TABLE STRUCTURE! Creating table widget from answer",
        );

        // Create a proper table widget structure
        const tableWidget = {
          type: "table",
          data: response.answer,
          metadata: {
            sortable: true,
            freshData: true,
            refreshTimestamp: new Date().toISOString(),
            widgetType: "table",
            title: "Table Data",
          },
          fallback: "Table data cannot be displayed",
        };

        console.log(
          "Created explicit table widget from direct answer:",
          tableWidget,
        );
        return formatAIMessage(tableWidget);
      }
    }

    console.log(
      "No table structure detected, proceeding with standard processing",
    );
    return formatAIMessage(response.answer);
  }

  // Handle standard widget-formatted responses
  if (response && response.final_answer) {
    return formatAIMessage(response.final_answer);
  }

  // Handle direct widget responses
  if (response && response.type) {
    return formatAIMessage(response);
  }

  // Legacy format handling - plain text
  if (response && typeof response === "string") {
    return formatAIMessage(response);
  }

  // Fallback for unknown formats
  console.warn("Unknown response format:", response);
  return formatAIMessage({
    type: "text",
    data: "I received a response in an unexpected format. Please see the developer console for details.",
    fallback: JSON.stringify(response, null, 2),
  });
};

/**
 * Check if a message contains a widget
 *
 * @param {Object} message - The message object
 * @returns {boolean} - True if the message contains a widget
 */
export const hasWidget = (message) => {
  if (!message || typeof message !== "object") return false;

  if (
    message.content &&
    typeof message.content === "object" &&
    message.content.type
  ) {
    return true;
  }

  return false;
};

/**
 * Extract widget type from a message
 *
 * @param {Object} message - The message object
 * @returns {string|null} - The widget type or null
 */
export const getWidgetType = (message) => {
  if (hasWidget(message)) {
    return message.content.type;
  }
  return null;
};

const messageFormatter = {
  formatUserMessage,
  formatAIMessage,
  parseResponse,
  hasWidget,
  getWidgetType,
};

export default messageFormatter;
