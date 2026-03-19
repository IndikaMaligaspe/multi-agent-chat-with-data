import React from "react";
import { getWidget } from "./WidgetRegistry";

/**
 * Widget Container Component
 *
 * Serves as a wrapper for all widget types with:
 * - Error boundary to catch widget rendering errors
 * - Standardized props interface
 * - Consistent styling wrapper
 * - Support for agent namespacing (multi-agent compatibility)
 */
class WidgetContainer extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      processedData: null,
    };

    // Debug widget container creation
    console.log("Creating WidgetContainer with props:", {
      type: props.widgetType,
      hasMetadata: !!props.metadata,
      hasTransition: !!props.widgetTransition,
      messageId: props.messageId,
    });
  }

  /**
   * Process widget data in a standardized way for all widget types
   * This ensures consistent handling of different data formats and structures
   *
   * @param {Object} widgetData - The raw widget data
   * @param {string} widgetType - The type of widget
   * @returns {Object} - Processed data ready for rendering
   */
  processWidgetData(widgetData, widgetType) {
    // If no data is provided, return null
    if (!widgetData) {
      console.warn("[DEBUG] No widget data provided to process");
      return null;
    }

    console.log("[DEBUG] Processing widget data:", {
      widgetType,
      hasMetadata: !!widgetData.metadata,
      freshData: widgetData.metadata?.freshData,
      refreshTimestamp: widgetData.metadata?.refreshTimestamp,
    });

    // Extract metadata for enhanced processing
    const metadata = widgetData.metadata || {};

    // Use API-determined widget type if available, fallback to passed type
    const effectiveWidgetType = metadata.widgetType || widgetType;

    if (metadata.widgetType && metadata.widgetType !== widgetType) {
      console.log(
        `[DEBUG] Widget type override from API metadata: ${widgetType} -> ${metadata.widgetType}`,
      );
    }

    // Log transition information if present
    if (metadata.widgetTransition) {
      console.log(
        "[DEBUG] Using widget transition from API metadata:",
        metadata.widgetTransition,
      );
    }

    // Log refresh information if present
    if (metadata.freshData) {
      console.log(
        "[DEBUG] Processing fresh data with timestamp:",
        metadata.refreshTimestamp,
      );
    }

    // Extract the data property, or use the whole object if no data property
    let processedData = widgetData.data || widgetData;

    // Handle stringified JSON data
    if (
      typeof processedData === "string" &&
      (processedData.startsWith("[") || processedData.startsWith("{"))
    ) {
      try {
        console.log("[DEBUG] Parsing stringified widget data");
        processedData = JSON.parse(processedData);
      } catch (error) {
        console.error("[DEBUG] Failed to parse widget data string:", error);

        // Add error information to the processed data
        if (typeof processedData === "object") {
          processedData.parseError = true;
          processedData.errorMessage = error.message;
        }
      }
    }

    // Ensure processedData is an object we can add properties to
    if (typeof processedData !== "object" || processedData === null) {
      processedData = { value: processedData };
    }

    // Add refresh metadata to the processed data for widget rendering
    if (metadata.freshData) {
      processedData.refreshTimestamp = metadata.refreshTimestamp;
      processedData.freshData = true;
    }

    // Type-specific processing using the effective widget type
    switch (effectiveWidgetType) {
      case "aggregation":
        // If data is an array with a single item, extract that item
        if (Array.isArray(processedData) && processedData.length === 1) {
          processedData = processedData[0];
          console.log(
            "Extracted single item from aggregation array:",
            processedData,
          );
        }
        break;

      case "table":
        console.log("Processing table widget data:", processedData);

        // Ensure table data is in the correct format
        if (
          Array.isArray(processedData) &&
          !processedData.headers &&
          !processedData.columns
        ) {
          // Convert array data to table format
          const headers =
            processedData.length > 0 ? Object.keys(processedData[0]) : [];

          const rows = processedData.map((item) =>
            headers.map((header) => item[header] ?? ""),
          );

          processedData = { headers, rows, columns: headers };
          console.log("Converted array data to table format:", processedData);
        }
        // Handle case where we have rows but need to ensure headers/columns are aligned
        else if (processedData.rows && Array.isArray(processedData.rows)) {
          // Make sure we have either columns or headers
          if (!processedData.headers && processedData.columns) {
            processedData.headers = processedData.columns;
            console.log("Using columns as headers for table widget");
          } else if (!processedData.columns && processedData.headers) {
            processedData.columns = processedData.headers;
            console.log("Using headers as columns for table widget");
          }

          // If neither exists but we have rows with data, try to generate headers
          if (
            !processedData.headers &&
            !processedData.columns &&
            processedData.rows.length > 0 &&
            Array.isArray(processedData.rows[0])
          ) {
            const columnCount = processedData.rows[0].length;
            const generatedHeaders = Array.from(
              { length: columnCount },
              (_, i) => `Column ${i + 1}`,
            );
            processedData.headers = generatedHeaders;
            processedData.columns = generatedHeaders;
            console.log(
              "Generated default headers for table widget:",
              generatedHeaders,
            );
          }
        }

        console.log("Final processed table data:", processedData);
        break;

      case "comparison":
        // Ensure comparison data is in the correct format
        if (Array.isArray(processedData) && !processedData.items) {
          processedData = { items: processedData };
          console.log(
            "Wrapped comparison data in items property:",
            processedData,
          );
        }
        break;

      // Add other widget type processing as needed
    }

    // Add metadata to processed data for component access
    if (metadata && Object.keys(metadata).length > 0) {
      processedData.metadata = metadata;
    }

    console.log(`Processed ${effectiveWidgetType} data:`, processedData);
    return processedData;
  }

  // Error boundary to catch widget rendering errors
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidMount() {
    // Process widget data when component mounts
    const { widgetType, widgetData } = this.props;
    const processedData = this.processWidgetData(widgetData, widgetType);
    this.setState({ processedData });
  }

  componentDidUpdate(prevProps) {
    // If widget data or type changes, reprocess the data
    const { widgetType, widgetData, widgetTransition } = this.props;

    // Detailed logging to trace widget update flow
    console.log(
      "[DEBUG] WidgetContainer componentDidUpdate checking for changes",
      {
        prevType: prevProps.widgetType,
        newType: widgetType,
        prevDataRefTimestamp: prevProps.widgetData?.metadata?.refreshTimestamp,
        newDataRefTimestamp: widgetData?.metadata?.refreshTimestamp,
        dataChanged: prevProps.widgetData !== widgetData,
        hasFreshData: widgetData?.metadata?.freshData === true,
      },
    );

    // Check if we need to reprocess the data
    if (
      prevProps.widgetType !== widgetType ||
      prevProps.widgetData !== widgetData ||
      prevProps.widgetTransition !== widgetTransition ||
      // Explicitly check for fresh data flag to force update
      widgetData?.metadata?.freshData === true ||
      // Check if refresh timestamps differ
      (widgetData?.metadata?.refreshTimestamp &&
        widgetData?.metadata?.refreshTimestamp !==
          prevProps.widgetData?.metadata?.refreshTimestamp)
    ) {
      console.log("[DEBUG] Widget needs update - reprocessing data", {
        prevType: prevProps.widgetType,
        newType: widgetType,
        transition: widgetTransition,
        freshData: widgetData?.metadata?.freshData,
      });

      const processedData = this.processWidgetData(widgetData, widgetType);

      // Debug log processed data differences
      if (this.state.processedData !== processedData) {
        console.log("[DEBUG] Widget data changed:", {
          prev: this.state.processedData,
          new: processedData,
        });
      }

      this.setState({ processedData });
    } else {
      console.log("[DEBUG] Widget data unchanged, skipping update");
    }
  }

  componentDidCatch(error, errorInfo) {
    // Log error to console or error tracking service
    console.error("Widget rendering failed:", error, errorInfo);

    // In production, you might want to send this to a monitoring service
    // errorTrackingService.captureError(error, { extra: errorInfo });

    // Report error to parent
    if (this.props.onError) {
      this.props.onError(error);
    }
  }

  render() {
    const {
      widgetType,
      widgetData,
      onAction,
      agentNamespace = null, // For multi-agent support
      className = "",
      showFallback = false, // Control whether to show fallback by default
      messageId = null, // Message ID for tracking
      widgetTransition = null, // Widget transition information
    } = this.props;

    // Handle error state - show fallback content
    if (this.state.hasError) {
      return (
        <div className="widget-error">
          <div className="widget-error-message">Widget failed to render</div>
          <div className="widget-error-fallback">
            {widgetData?.fallback || "No fallback content available"}
          </div>
          {process.env.NODE_ENV !== "production" && (
            <details className="widget-error-details">
              <summary>Error details</summary>
              <pre>{this.state.error && this.state.error.toString()}</pre>
            </details>
          )}
        </div>
      );
    }

    // Use API-defined widget type if available
    const effectiveWidgetType = widgetData?.metadata?.widgetType || widgetType;

    // Get the appropriate widget component
    const WidgetComponent = getWidget(effectiveWidgetType, agentNamespace);

    // Merge all available metadata
    const combinedMetadata = {
      ...(widgetData?.metadata || {}),
      messageId,
      widgetTransition,
    };

    // Wrap action handler to add widget context
    const handleAction = (actionType, actionData) => {
      if (onAction) {
        // Include widget metadata in callbacks to provide context
        onAction(actionType, {
          ...actionData,
          _widgetContext: {
            widgetType: effectiveWidgetType,
            agentNamespace,
            metadata: combinedMetadata,
            transitionInfo: widgetTransition,
          },
        });
      }
    };

    // Debug - Enhanced logging for widget debugging
    console.log(`--------------- WIDGET DEBUG ---------------`);
    console.log(
      `WidgetContainer for type: "${effectiveWidgetType}" (original: "${widgetType}")`,
    );

    // More detailed widget tracing
    console.log(
      `Widget component to use: ${WidgetComponent ? WidgetComponent.name : "undefined"}`,
    );
    console.log(`Is widget component defined: ${!!WidgetComponent}`);

    // Debug widget data structure
    console.log(`Widget data:`, widgetData);
    console.log(`Widget data.data:`, widgetData?.data);

    // Log the exact structure we expect for a table widget
    if (effectiveWidgetType === "table") {
      console.log(`🔍 TABLE WIDGET DETAILED DEBUG 🔍`);
      console.log(`Table data columns:`, widgetData?.data?.columns);
      console.log(`Table data rows:`, widgetData?.data?.rows);
      console.log(`Table data headers:`, widgetData?.data?.headers);

      // Check for array vs object rows
      if (widgetData?.data?.rows && widgetData.data.rows.length > 0) {
        const firstRow = widgetData.data.rows[0];
        console.log(
          `First row type: ${typeof firstRow}, is array: ${Array.isArray(firstRow)}`,
        );
        console.log(`First row:`, firstRow);
      }

      // Check for properly structured table data in processedData
      if (this.state.processedData) {
        console.log(`Processed table data:`);
        console.log(`- Has columns: ${!!this.state.processedData.columns}`);
        console.log(`- Has rows: ${!!this.state.processedData.rows}`);
        console.log(`- Has headers: ${!!this.state.processedData.headers}`);
        console.log(
          `- Rows length: ${this.state.processedData.rows ? this.state.processedData.rows.length : 0}`,
        );
      }
    }

    console.log(`Widget combined metadata:`, combinedMetadata);
    console.log(`Using processed data from state:`, this.state.processedData);

    // Log critical info for determining why widget might not be rendering
    console.log(`⚠️ Widget rendering readiness check:`);
    console.log(`- Has error state: ${this.state.hasError}`);
    console.log(
      `- Error message: ${this.state.error ? this.state.error.message : "none"}`,
    );
    console.log(`- Has processed data: ${!!this.state.processedData}`);
    console.log(`- Widget component available: ${!!WidgetComponent}`);
    console.log(`- Container CSS class: ${finalClassName}`);

    // Add transition debugging
    if (widgetTransition) {
      console.log(`Widget transition:`, widgetTransition);
    }

    // Add detailed widget component info
    console.log(
      `Using widget component:`,
      WidgetComponent?.name || "Unknown component",
    );
    console.log(`Widget namespace:`, agentNamespace);
    console.log(`--------------- END DEBUG ---------------`);

    // Combine any provided className with the widget-specific class
    const containerClassName =
      `widget-container widget-type-${effectiveWidgetType} ${className}`.trim();

    // Add a transition class if this widget is transitioning
    const transitionClass = widgetTransition
      ? `widget-transitioning widget-from-${widgetTransition.from} widget-to-${widgetTransition.to}`
      : "";

    const finalClassName = `${containerClassName} ${transitionClass}`.trim();

    // Use the processed data from state for all widget types
    // This implements a unified rendering approach for all widget types
    return (
      <div className={finalClassName} data-message-id={messageId}>
        {/* Render widget component with properly processed data */}
        <WidgetComponent
          data={this.state.processedData}
          onAction={handleAction}
          metadata={combinedMetadata}
          widgetTransition={widgetTransition}
        />

        {/* Optional fallback toggle and display */}
        {showFallback && widgetData?.fallback && (
          <div className="widget-fallback">
            <details>
              <summary>Show as text</summary>
              <div className="fallback-content">{widgetData?.fallback}</div>
            </details>
          </div>
        )}
      </div>
    );
  }
}

export default WidgetContainer;
