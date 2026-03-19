import React, { useState, useEffect, useRef } from "react";
import PropTypes from "prop-types";
import Message from "./Message";
import WidgetContainer from "../widgets/WidgetContainer";
import DirectTableRenderer from "../widgets/DirectTableRenderer";
import "./AIMessage.css";

/**
 * AIMessage component for displaying AI responses with widget support
 */
const AIMessage = ({
  content,
  timestamp,
  onWidgetAction,
  namespace,
  messageId,
}) => {
  const [widgetError, setWidgetError] = useState(null);
  const [widgetTypeTransition, setWidgetTypeTransition] = useState(null);
  const prevContentRef = useRef(null);
  const prevWidgetTypeRef = useRef(null);

  // Track widget type changes for better transition handling and debugging
  useEffect(() => {
    // Only track for widget content
    if (typeof content === "object" && content !== null && content.type) {
      // First check if the API already provided transition metadata
      if (content.metadata && content.metadata.widgetTransition) {
        console.log(
          `API detected widget transition: ${content.metadata.widgetTransition.from} → ${content.metadata.widgetTransition.to}`,
          {
            messageId,
            transition: content.metadata.widgetTransition,
          },
        );

        // Use the transition information from the API
        setWidgetTypeTransition(content.metadata.widgetTransition);
      }
      // Fallback to local transition detection
      else if (
        prevWidgetTypeRef.current &&
        prevWidgetTypeRef.current !== content.type
      ) {
        console.log(
          `Locally detected widget type transition: ${prevWidgetTypeRef.current} → ${content.type}`,
          {
            messageId,
            oldContent: prevContentRef.current,
            newContent: content,
          },
        );

        setWidgetTypeTransition({
          from: prevWidgetTypeRef.current,
          to: content.type,
          timestamp: new Date().toISOString(),
          detectedLocally: true, // Flag to indicate this was detected client-side
        });
      }

      // Update refs for next comparison
      prevContentRef.current = { ...content };
      prevWidgetTypeRef.current = content.type;
    }
  }, [content, messageId]);

  // Handle errors that bubble up from widgets
  const handleWidgetError = (error) => {
    console.error("Widget error:", error);
    setWidgetError(
      error.message || "An error occurred while displaying the widget",
    );
  };

  // Handle widget actions with agent namespace
  const handleWidgetAction = (actionType, data) => {
    if (onWidgetAction) {
      onWidgetAction(actionType, data, namespace);
    }
  };

  // Determine if content is a widget object or plain text
  // First set basic widget detection
  let isWidget =
    typeof content === "object" && content !== null && content.type;

  console.log("🧩 AIMessage initial content analysis:", {
    type: content?.type,
    dataPresent: !!content?.data,
    dataKeys: content?.data ? Object.keys(content.data) : [],
    metadataPresent: !!content?.metadata,
    metadataWidgetType: content?.metadata?.widgetType,
    contentKeys:
      typeof content === "object" && content !== null
        ? Object.keys(content)
        : [],
  });

  // MAJOR SIMPLIFICATION - Ensure type field is present
  // If content has no type but has metadata.widgetType, use that
  if (!isWidget && typeof content === "object" && content !== null) {
    // Fix 1: Use metadata.widgetType if available
    if (!content.type && content.metadata?.widgetType) {
      console.log(
        `🔄 Setting missing type "${content.metadata.widgetType}" from metadata`,
      );
      content.type = content.metadata.widgetType;
    }

    // Fix 2: Auto-detect table structures
    if (!content.type && content.data) {
      // Check for table structure
      if (
        content.data.rows &&
        Array.isArray(content.data.rows) &&
        ((content.data.columns && Array.isArray(content.data.columns)) ||
          (content.data.headers && Array.isArray(content.data.headers)))
      ) {
        console.log("🔄 Found table structure without type - setting to table");
        content.type = "table";

        if (!content.metadata) {
          content.metadata = {};
        }
        content.metadata.widgetType = "table";
      }
      // Check for aggregation structure - simple numeric value with title
      else if (
        (typeof content.data.value === "number" ||
          typeof content.data.count === "number") &&
        (content.data.title || content.data.label)
      ) {
        console.log(
          "🔄 Found aggregation structure without type - setting to aggregation",
        );
        content.type = "aggregation";

        if (!content.metadata) {
          content.metadata = {};
        }
        content.metadata.widgetType = "aggregation";
      }
    }

    // Reevaluate widget status
    isWidget = typeof content === "object" && content !== null && content.type;
  }

  console.log("🧩 Final widget detection status:", {
    isWidget,
    type: content?.type,
    dataFields: content?.data ? Object.keys(content.data) : [],
    hasRows: content?.data?.rows ? true : false,
    hasColumns: content?.data?.columns ? true : false,
    hasHeaders: content?.data?.headers ? true : false,
    rowsLength: content?.data?.rows?.length || 0,
    directRenderingDecision:
      content?.type === "table" || content?.type === "aggregation"
        ? "Yes"
        : "No",
  });

  // Add API response debugging
  if (typeof content === "object" && content !== null) {
    console.log("Content properties:", Object.keys(content));
    console.log("Widget type:", content.type);
    console.log("API-provided metadata:", content.metadata);
    console.log("Widget type (metadata):", content.metadata?.widgetType);
    console.log("Widget data:", content.data);
    console.log("Widget data type:", typeof content.data);

    // Log widget transition information if present
    if (content.metadata?.widgetTransition) {
      console.log(
        "🔄 API-detected widget transition:",
        content.metadata.widgetTransition,
      );
    }

    // Check if data is stringified
    if (
      typeof content.data === "string" &&
      (content.data.startsWith("[") || content.data.startsWith("{"))
    ) {
      console.log("⚠️ Data appears to be stringified JSON");
      try {
        const parsed = JSON.parse(content.data);
        console.log("Parsed data:", parsed);
      } catch (err) {
        console.error("Failed to parse data:", err);
      }
    }

    // Log processing information if present
    if (content.processedAt) {
      console.log("API processing timestamp:", content.processedAt);
    }

    // Log any processing errors
    if (content.processingError) {
      console.error("⚠️ API processing error:", content.processingError);
    }
  }
  console.log("====== END AIMessage DEBUGGING ======");

  return (
    <Message isUser={false} timestamp={timestamp} className="ai-message">
      {isWidget ? (
        <>
          {widgetError ? (
            <div className="widget-error">
              <p className="error-message">{widgetError}</p>
              {content.fallback && (
                <div className="widget-fallback">
                  <h4>Fallback Content:</h4>
                  <div className="fallback-content">{content.fallback}</div>
                </div>
              )}
            </div>
          ) : (
            <div className="widget-wrapper">
              {/* Debug information section */}
              <div
                className="debug-info"
                style={{
                  background: "#f0f0f0",
                  padding: "8px",
                  margin: "4px 0",
                  fontSize: "12px",
                  fontFamily: "monospace",
                }}
              >
                <strong>Widget Debug:</strong> type=
                {content.metadata?.widgetType || content.type}, data present:{" "}
                {content.data ? "yes" : "no"}, metadata present:{" "}
                {content.metadata ? "yes" : "no"},
                {content.type === "table" && (
                  <span style={{ color: "#0066cc", fontWeight: "bold" }}>
                    TABLE: rows={content.data?.rows?.length || 0}, cols=
                    {content.data?.columns?.length || 0}
                  </span>
                )}
                {widgetTypeTransition && (
                  <div
                    className="transition-info"
                    style={{
                      marginTop: "4px",
                      color: "#0066cc",
                      backgroundColor: widgetTypeTransition.detectedLocally
                        ? "#fff8e6"
                        : "#e6f7ff",
                      padding: "2px 4px",
                      borderRadius: "3px",
                    }}
                  >
                    Widget transition: {widgetTypeTransition.from} →{" "}
                    {widgetTypeTransition.to}
                    {widgetTypeTransition.detectedLocally && (
                      <span style={{ fontStyle: "italic", fontSize: "10px" }}>
                        {" "}
                        (client detected)
                      </span>
                    )}
                  </div>
                )}
                {content.processedAt && (
                  <div style={{ marginTop: "2px", fontSize: "10px" }}>
                    Processed:{" "}
                    {new Date(content.processedAt).toLocaleTimeString()}
                  </div>
                )}
              </div>

              {/* Direct rendering for specific widget types to bypass widget system */}
              {content.type === "table" && content.data ? (
                <>
                  <DirectTableRenderer data={content.data} />
                  {/* Log the direct rendering decision for debugging */}
                  {console.log("✅ Using DirectTableRenderer for table widget")}
                </>
              ) : content.type === "aggregation" && content.data ? (
                <>
                  {/* Simple direct rendering for aggregation widget */}
                  <div
                    className="direct-aggregation-widget"
                    style={{
                      padding: "15px",
                      background: "#e6f7ff",
                      border: "1px solid #91caff",
                      borderRadius: "4px",
                      textAlign: "center",
                      marginBottom: "15px",
                    }}
                  >
                    <div style={{ fontSize: "14px", color: "#666" }}>
                      {content.data.title || content.data.label || "Result"}
                    </div>
                    <div
                      style={{
                        fontSize: "24px",
                        fontWeight: "bold",
                        margin: "10px 0",
                      }}
                    >
                      {content.data.value || content.data.count || 0}
                    </div>
                    {content.data.subtitle && (
                      <div style={{ fontSize: "12px", color: "#999" }}>
                        {content.data.subtitle}
                      </div>
                    )}
                    {console.log(
                      "✅ Using direct rendering for aggregation widget",
                    )}
                  </div>
                </>
              ) : (
                /* All other widget types use the widget container */
                <>
                  <WidgetContainer
                    widgetType={content.metadata?.widgetType || content.type}
                    widgetData={content}
                    onAction={handleWidgetAction}
                    onError={handleWidgetError}
                    namespace={namespace}
                    messageId={messageId}
                    showFallback={true}
                    widgetTransition={widgetTypeTransition}
                    metadata={content.metadata}
                  />
                  {console.log(
                    `ℹ️ Using WidgetContainer for ${content.type} widget`,
                  )}
                </>
              )}
            </div>
          )}
        </>
      ) : (
        <div className="text-content">{content}</div>
      )}
    </Message>
  );
};

AIMessage.propTypes = {
  content: PropTypes.oneOfType([PropTypes.string, PropTypes.object]).isRequired,
  timestamp: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.number,
    PropTypes.instanceOf(Date),
  ]),
  onWidgetAction: PropTypes.func,
  namespace: PropTypes.string,
  messageId: PropTypes.string, // Added message ID for tracking widget transitions
};

AIMessage.defaultProps = {
  timestamp: null,
  onWidgetAction: null,
  namespace: null,
  messageId: null,
};

export default AIMessage;
