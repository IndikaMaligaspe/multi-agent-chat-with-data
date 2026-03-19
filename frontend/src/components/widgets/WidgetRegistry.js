// Import widget components
import TextWidget from "./TextWidget";
import TableWidget from "./TableWidget";
import AggregationWidget from "./AggregationWidget";
import ComparisonWidget from "./ComparisonWidget";
import ConfirmationWidget from "./ConfirmationWidget";
import OptionsWidget from "./OptionsWidget";

/**
 * Widget Registry System
 *
 * A centralized registry for all widget types that can be displayed in the chat interface.
 * Designed with multi-agent compatibility in mind, allowing widgets to be namespaced by agent.
 */

/**
 * Widget registry with multi-agent support
 *
 * - Default namespace contains common widgets
 * - Agent-specific widgets can be organized by namespace (e.g., 'sql:table')
 * - This structure supports future expansion to multi-agent system
 */
const widgetRegistry = {
  // Default widgets (non-namespaced)
  text: TextWidget,

  // SQL Agent widgets (will be accessed either directly or with namespace)
  table: TableWidget,
  aggregation: AggregationWidget,
  comparison: ComparisonWidget,

  // Interactive widgets
  confirmation: ConfirmationWidget,
  options: OptionsWidget,

  // Future agent-specific widgets can be added with namespaces
  "task:progress": null, // For future task execution agent
  "knowledge:graph": null, // For future knowledge agent
};

/**
 * Get the appropriate widget component for a type, with optional namespace
 *
 * @param {string} type - Widget type identifier (e.g., 'table', 'confirmation')
 * @param {string|null} namespace - Optional namespace for agent-specific widgets (e.g., 'sql', 'task')
 * @returns {React.Component} - The corresponding widget component or fallback
 */
export const getWidget = (type, namespace = null) => {
  if (!type) {
    console.warn("No widget type specified, falling back to text widget");
    return widgetRegistry["text"];
  }

  // Try namespace-specific lookup first (for multi-agent support)
  const fullType = namespace ? `${namespace}:${type}` : type;

  // Check for namespaced widget first, then non-namespaced, then fallback to text
  if (widgetRegistry[fullType]) {
    return widgetRegistry[fullType];
  } else if (widgetRegistry[type]) {
    return widgetRegistry[type];
  }

  // Log warning and return fallback widget
  console.warn(
    `Unknown widget type: ${type}${namespace ? ` in namespace ${namespace}` : ""}`,
  );
  return widgetRegistry["text"];
};

/**
 * Register a new widget type in the registry
 *
 * @param {string} type - Widget type identifier
 * @param {React.Component} component - Widget component to register
 * @param {string|null} namespace - Optional namespace for agent-specific widgets
 */
export const registerWidget = (type, component, namespace = null) => {
  if (!type || !component) {
    console.error("Cannot register widget: missing type or component");
    return;
  }

  const fullType = namespace ? `${namespace}:${type}` : type;

  if (widgetRegistry[fullType] && widgetRegistry[fullType] !== null) {
    console.warn(`Overriding existing widget type: ${fullType}`);
  }

  widgetRegistry[fullType] = component;
};

/**
 * Update registry with a batch of widget components once they're implemented
 *
 * @param {Object} widgets - Object mapping widget types to components
 * @param {string|null} namespace - Optional namespace for all widgets in the batch
 */
export const registerWidgets = (widgets, namespace = null) => {
  if (!widgets || typeof widgets !== "object") {
    console.error("Invalid widgets object provided to registerWidgets");
    return;
  }

  Object.entries(widgets).forEach(([type, component]) => {
    registerWidget(type, component, namespace);
  });
};

const WidgetRegistry = {
  getWidget,
  registerWidget,
  registerWidgets,
  TextWidget, // Export the fallback widget for now
};

export default WidgetRegistry;
