import { useCallback, useState } from "react";

/**
 * Custom hook for handling widget actions and interactions
 *
 * @param {Object} options - Configuration options
 * @param {Function} options.onSubmitQuery - Function to submit a new query
 * @param {Function} options.onUpdateState - Function to update application state
 * @param {Function} options.onApiCall - Function to make API calls
 * @param {Function} options.getCurrentWidgetType - Optional function to get current widget type
 * @returns {Object} Widget action handlers
 */
const useWidgetActions = ({
  onSubmitQuery,
  onUpdateState,

  onApiCall,
  getCurrentWidgetType = null,
}) => {
  const [lastWidgetType, setLastWidgetType] = useState(null);

  /**
   * Get the current widget type for transition tracking
   *
   * @returns {string|null} The current widget type or null if unknown
   */
  const getWidgetType = useCallback(() => {
    // If an external function is provided to get the current widget type, use it
    if (getCurrentWidgetType) {
      return getCurrentWidgetType();
    }

    // Otherwise use our internal state
    return lastWidgetType;
  }, [getCurrentWidgetType, lastWidgetType]);

  /**
   * Handle confirmation widget actions (yes/no)
   */
  const handleConfirmationAction = useCallback(
    (data, namespace) => {
      // If the confirmation has a followup query, submit it
      if (data.followupQuery) {
        onSubmitQuery(data.followupQuery);
        return;
      }

      // If there's a callback action to perform
      if (data.callbackAction) {
        // Get current widget type for tracking transitions
        const currentWidgetType = getWidgetType();

        // Make any necessary API calls based on the confirmation
        if (data.apiEndpoint) {
          onApiCall(data.apiEndpoint, {
            action: data.callbackAction,
            confirmed: data.confirmed,
            metadata: data.metadata,
            previousWidgetType: currentWidgetType,
          });
        }

        // Update local state based on the action
        onUpdateState({
          type: data.callbackAction,
          confirmed: data.confirmed,
          metadata: data.metadata,
        });
      }
    },
    [onSubmitQuery, onUpdateState, onApiCall, getWidgetType],
  );

  /**
   * Handle option selection actions
   */
  const handleOptionAction = useCallback(
    (data, namespace) => {
      // If the option has a followup query, submit it
      if (data.followupQuery) {
        onSubmitQuery(data.followupQuery);
        return;
      }

      // Get current widget type for tracking transitions
      const currentWidgetType = getWidgetType();

      // If the option selection requires an API call
      if (data.apiEndpoint) {
        onApiCall(data.apiEndpoint, {
          selectedOption: data.selectedOption,
          optionId: data.optionId,
          metadata: data.metadata,
          previousWidgetType: currentWidgetType,
        });
      }

      // Update local state based on the selection
      onUpdateState({
        type: "OPTION_SELECTED",
        selectedOption: data.selectedOption,
        optionId: data.optionId,
        metadata: data.metadata,
      });
    },
    [onSubmitQuery, onUpdateState, onApiCall, getWidgetType],
  );

  /**
   * Handle table actions like sorting, filtering, etc.
   */
  const handleTableAction = useCallback(
    (data, namespace) => {
      // Update local state based on table interactions
      onUpdateState({
        type: "TABLE_ACTION",
        actionType: data.actionType, // 'sort', 'filter', 'select', etc.
        field: data.field,
        value: data.value,
        metadata: data.metadata,
      });

      // Get current widget type for tracking transitions
      const currentWidgetType = getWidgetType();

      // Make API calls if needed (for server-side sorting/filtering)
      if (data.requiresApi && data.apiEndpoint) {
        onApiCall(data.apiEndpoint, {
          actionType: data.actionType,
          field: data.field,
          value: data.value,
          metadata: data.metadata,
          previousWidgetType: currentWidgetType,
        });
      }
    },
    [onUpdateState, onApiCall, getWidgetType],
  );

  /**
   * Update the current widget type in our state
   */
  const updateWidgetType = useCallback(
    (widgetType) => {
      if (widgetType && widgetType !== lastWidgetType) {
        console.log(`Updating widget type in useWidgetActions: ${widgetType}`);
        setLastWidgetType(widgetType);
      }
    },
    [lastWidgetType],
  );

  /**
   * Generic action handler that routes to specific handlers based on action type
   */
  const handleAction = useCallback(
    (actionType, data, namespace = null) => {
      console.log(
        `Widget action: ${actionType}`,
        data,
        namespace ? `(namespace: ${namespace})` : "",
      );

      // If the action context includes widget type information, update our state
      if (data._widgetContext?.widgetType) {
        updateWidgetType(data._widgetContext.widgetType);
      }

      switch (actionType) {
        case "CONFIRM":
          handleConfirmationAction(data, namespace);
          break;
        case "SELECT_OPTION":
          handleOptionAction(data, namespace);
          break;
        case "TABLE_ACTION":
          handleTableAction(data, namespace);
          break;
        default:
          // Get current widget type for generic actions too
          const currentWidgetType = getWidgetType();

          // For any other action types, use the generic state update
          onUpdateState({
            type: actionType,
            ...data,
            namespace,
          });

          // If the action requires an API call
          if (data.apiEndpoint) {
            onApiCall(data.apiEndpoint, {
              ...data,
              actionType,
              previousWidgetType: currentWidgetType,
            });
          }
          break;
      }
    },
    [
      handleConfirmationAction,
      handleOptionAction,
      handleTableAction,
      onUpdateState,
      onApiCall,
      getWidgetType,
      updateWidgetType,
    ],
  );

  return {
    handleAction,
    getCurrentWidgetType: getWidgetType,
    updateWidgetType,
  };
};

export default useWidgetActions;
