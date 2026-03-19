import { useCallback, useState } from "react";
import { sendQuery } from "../../services/api";

/**
 * Custom hook for sending messages to the API
 *
 * @param {Object} options - Configuration options
 * @param {Function} options.onMessageSent - Callback when message is sent
 * @param {Function} options.onResponseReceived - Callback when response is received
 * @param {Function} options.onError - Callback when an error occurs
 * @param {Function} options.getCurrentWidgetType - Optional function to get current widget type
 * @returns {Object} Send message functionality and state
 */
const useSendMessage = ({
  onMessageSent = null,
  onResponseReceived = null,
  onError = null,
  getCurrentWidgetType = null,
} = {}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastQuery, setLastQuery] = useState("");
  const [lastResponse, setLastResponse] = useState(null);
  const [lastWidgetType, setLastWidgetType] = useState(null);

  /**
   * Send a query to the backend API
   *
   * @param {string} query - User query to send
   * @param {Object} options - Additional options
   * @returns {Promise<Object>} Response data
   */
  const sendMessage = useCallback(
    async (query, options = {}) => {
      if (!query || query.trim() === "") {
        const emptyQueryError = new Error("Please enter a query");
        setError(emptyQueryError);
        if (onError) onError(emptyQueryError);
        return null;
      }

      setIsLoading(true);
      setError(null);
      setLastQuery(query);

      // Add debug logging to trace request flow
      console.log(`[DEBUG] Sending new query to server: "${query}"`);

      try {
        // Determine current widget type for transition tracking
        let previousWidgetType = null;
        if (getCurrentWidgetType) {
          // If a function was provided to get current widget type, use it
          previousWidgetType = getCurrentWidgetType();
        } else if (lastWidgetType) {
          // Otherwise use the stored last widget type
          previousWidgetType = lastWidgetType;
        } else if (lastResponse?.answer?.metadata?.widgetType) {
          // Or extract from the last response if available
          previousWidgetType = lastResponse.answer.metadata.widgetType;
        }

        if (previousWidgetType) {
          console.log(
            `Current widget type before query: ${previousWidgetType}`,
          );
        }

        // Call onMessageSent callback if provided
        if (onMessageSent) {
          onMessageSent(query, options);
        }

        // Add a timestamp to force new requests for similar queries
        const timestamp = new Date().getTime();

        // Send the query to the API with widget transition information and force a fresh request
        console.log(`[DEBUG] Making API request with timestamp: ${timestamp}`);
        const response = await sendQuery(query, {
          additionalData: {
            ...(options.additionalData || {}),
            _timestamp: timestamp, // Add timestamp to force cache busting
          },
          headers: {
            ...(options.headers || {}),
            "Cache-Control": "no-cache, no-store", // Prevent browser caching
          },
          previousWidgetType: previousWidgetType, // Pass current widget type for transition tracking
          forceRefresh: true, // Add flag to indicate this should be a fresh request
        });

        console.log(`[DEBUG] Received response from server:`, response);

        // Extract and store the new widget type for future transitions
        if (response?.answer?.metadata?.widgetType) {
          setLastWidgetType(response.answer.metadata.widgetType);
          console.log(
            `New widget type: ${response.answer.metadata.widgetType}`,
          );

          // Enhanced debugging after widget type detection
          console.log(
            "🔍 DETAILED RESPONSE ANALYSIS AFTER WIDGET TYPE DETECTION:",
          );
          console.log("response.answer structure:", {
            hasData: !!response.answer.data,
            dataType: typeof response.answer.data,
            dataKeys: response.answer.data
              ? Object.keys(response.answer.data)
              : [],
            metadataKeys: response.answer.metadata
              ? Object.keys(response.answer.metadata)
              : [],
            type: response.answer.type || "undefined",
            widgetType: response.answer.metadata?.widgetType || "undefined",
          });

          // If it's a table widget, log more details
          if (response.answer.metadata?.widgetType === "table") {
            console.log("📊 TABLE WIDGET DATA STRUCTURE:");
            console.log("- Has columns:", !!response.answer.data?.columns);
            console.log("- Has rows:", !!response.answer.data?.rows);
            console.log("- Has headers:", !!response.answer.data?.headers);
            console.log(
              "- Row count:",
              response.answer.data?.rows?.length || 0,
            );
            console.log(
              "- Column count:",
              response.answer.data?.columns?.length || 0,
            );
            console.log(
              "- First row:",
              response.answer.data?.rows?.[0] || "none",
            );
          }

          // Force explicitly set the type field if it's missing
          if (response.answer.metadata?.widgetType && !response.answer.type) {
            console.log(
              "⚠️ TYPE FIELD MISSING - Adding explicit type from metadata",
            );
            response.answer.type = response.answer.metadata.widgetType;
          }

          // Additional fix for table widget data structure
          if (
            response.answer.metadata?.widgetType === "table" &&
            response.answer.data
          ) {
            console.log("⚙️ APPLYING FINAL TABLE DATA STRUCTURE FIXES:");

            // Ensure both columns and headers properties exist
            if (response.answer.data.columns && !response.answer.data.headers) {
              console.log("- Adding headers field based on columns");
              response.answer.data.headers = response.answer.data.columns;
            } else if (
              !response.answer.data.columns &&
              response.answer.data.headers
            ) {
              console.log("- Adding columns field based on headers");
              response.answer.data.columns = response.answer.data.headers;
            }

            // If we have rows but missing headers/columns, generate them based on first row length
            if (
              response.answer.data.rows?.length > 0 &&
              (!response.answer.data.columns || !response.answer.data.headers)
            ) {
              const firstRowLength = Array.isArray(response.answer.data.rows[0])
                ? response.answer.data.rows[0].length
                : Object.keys(response.answer.data.rows[0]).length;

              console.log(
                `- Generating column headers for ${firstRowLength} columns`,
              );
              const generatedHeaders = Array.from(
                { length: firstRowLength },
                (_, i) => `Column ${i + 1}`,
              );

              response.answer.data.columns = generatedHeaders;
              response.answer.data.headers = generatedHeaders;
            }

            console.log("📊 FINAL TABLE DATA STRUCTURE:", {
              type: response.answer.type,
              rows: response.answer.data.rows?.length || 0,
              columns: response.answer.data.columns?.length || 0,
              headers: response.answer.data.headers?.length || 0,
            });
          }

          // Log if a transition occurred
          if (
            previousWidgetType &&
            previousWidgetType !== response.answer.metadata.widgetType
          ) {
            console.log(
              `Widget transition: ${previousWidgetType} -> ${response.answer.metadata.widgetType}`,
            );
          }
        }

        // Update state with response
        setLastResponse(response);
        setIsLoading(false);

        // Call onResponseReceived callback if provided
        if (onResponseReceived) {
          onResponseReceived(response, query, options);
        }

        return response;
      } catch (err) {
        console.error("Error sending message:", err);

        setError(err);
        setIsLoading(false);

        // Call onError callback if provided
        if (onError) {
          onError(err, query, options);
        }

        return null;
      }
    },
    [
      onMessageSent,
      onResponseReceived,
      onError,
      getCurrentWidgetType,
      lastWidgetType,
      lastResponse,
    ],
  );

  /**
   * Reset the error state
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  /**
   * Reset all state
   */
  const reset = useCallback(() => {
    setIsLoading(false);
    setError(null);
    setLastQuery("");
    setLastResponse(null);
    setLastWidgetType(null);
  }, []);

  return {
    sendMessage,
    isLoading,
    error,
    clearError,
    reset,
    lastQuery,
    lastResponse,
    lastWidgetType,
  };
};

export default useSendMessage;
