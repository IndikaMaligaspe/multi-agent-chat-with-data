import React, { useState } from "react";
import PropTypes from "prop-types";
import "./OptionsWidget.css";

/**
 * OptionsWidget - Displays multiple choice options for user selection
 *
 * Used for presenting a set of options to the user and handling selection.
 * Supports various display styles and single/multiple selection modes.
 */
const OptionsWidget = ({ data, metadata = {}, onAction }) => {
  // Extract data properties
  const {
    question = "",
    description = "",
    options = [],
    defaultSelected = [],
    multiSelect = false,
    submitButtonText = "Submit",
    cancelButtonText = "Cancel",
    requireConfirmation = true,
  } = data;

  // Extract metadata with defaults
  const {
    displayStyle = "buttons", // 'buttons', 'cards', 'dropdown', 'radio'
    layout = "vertical", // 'horizontal', 'vertical', 'grid'
    showIcons = true,
    iconPosition = "left", // 'left', 'top', 'right'
    maxSelectionsAllowed = 0, // 0 = unlimited in multiSelect mode
    enableSearch = options.length > 10,
    searchPlaceholder = "Search options...",
    size = "medium", // 'small', 'medium', 'large'
    equalWidth = true,
    submitOnSelect = !multiSelect && !requireConfirmation,
  } = metadata;

  // Component state
  const [selected, setSelected] = useState(defaultSelected || []);
  const [searchText, setSearchText] = useState("");
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isCancelled, setIsCancelled] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  // Filter options based on search text
  const filteredOptions = options.filter((option) => {
    if (!searchText) return true;

    const searchLower = searchText.toLowerCase();
    return (
      (option.label && option.label.toLowerCase().includes(searchLower)) ||
      (option.description &&
        option.description.toLowerCase().includes(searchLower))
    );
  });

  // Handle option selection
  const handleOptionSelect = (optionId) => {
    if (isProcessing || isSubmitted || isCancelled) return;

    let newSelected;

    if (multiSelect) {
      // For multi-select, toggle the selection
      if (selected.includes(optionId)) {
        newSelected = selected.filter((id) => id !== optionId);
      } else {
        // Check max selections if applicable
        if (
          maxSelectionsAllowed > 0 &&
          selected.length >= maxSelectionsAllowed
        ) {
          return; // Don't add if max selections reached
        }
        newSelected = [...selected, optionId];
      }
    } else {
      // For single-select, replace the selection
      newSelected = [optionId];
    }

    setSelected(newSelected);

    // If submitOnSelect is true, immediately submit
    if (submitOnSelect) {
      handleSubmit(newSelected);
    }
  };

  // Handle submission
  const handleSubmit = async (selectedOptions = selected) => {
    if (isProcessing || isSubmitted || isCancelled) return;
    if (selectedOptions.length === 0) return; // Require at least one selection

    setIsProcessing(true);

    try {
      // Get the selected option objects to include in the callback
      const selectedData = options.filter((option) =>
        selectedOptions.includes(option.id),
      );

      if (onAction) {
        await onAction("select", {
          selectedIds: selectedOptions,
          selectedData,
          question,
          multiSelect,
          timestamp: new Date().toISOString(),
        });
      }

      setIsSubmitted(true);
    } catch (error) {
      console.error("Error during option submission:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle cancellation
  const handleCancel = async () => {
    if (isProcessing || isSubmitted || isCancelled) return;

    setIsProcessing(true);

    try {
      if (onAction) {
        await onAction("cancel", {
          question,
          timestamp: new Date().toISOString(),
        });
      }

      setIsCancelled(true);
    } catch (error) {
      console.error("Error during option cancellation:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  // Render icon for option
  const renderIcon = (option) => {
    if (!showIcons || !option.icon) return null;

    return (
      <span className={`option-icon icon-position-${iconPosition}`}>
        {typeof option.icon === "string" ? (
          <img src={option.icon} alt="" />
        ) : (
          option.icon
        )}
      </span>
    );
  };

  // Render options based on display style
  const renderOptions = () => {
    switch (displayStyle) {
      case "cards":
        return (
          <div className={`options-cards layout-${layout}`}>
            {filteredOptions.map((option) => (
              <div
                key={option.id}
                className={`option-card ${selected.includes(option.id) ? "selected" : ""}`}
                onClick={() => handleOptionSelect(option.id)}
                role="button"
                aria-pressed={selected.includes(option.id)}
                tabIndex={0}
                onKeyPress={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    handleOptionSelect(option.id);
                  }
                }}
              >
                {renderIcon(option)}

                <div className="option-content">
                  <div className="option-label">{option.label}</div>
                  {option.description && (
                    <div className="option-description">
                      {option.description}
                    </div>
                  )}
                </div>

                <div className="option-indicator">
                  {multiSelect ? (
                    <div className="checkbox">
                      {selected.includes(option.id) && (
                        <span className="check">✓</span>
                      )}
                    </div>
                  ) : (
                    <div className="radio">
                      {selected.includes(option.id) && (
                        <span className="dot"></span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        );

      case "dropdown":
        return (
          <div className="options-dropdown">
            <select
              value={multiSelect ? "" : selected[0] || ""}
              onChange={(e) => handleOptionSelect(e.target.value)}
              multiple={multiSelect}
              size={multiSelect ? Math.min(filteredOptions.length, 5) : 1}
            >
              <option value="" disabled>
                Select an option
              </option>
              {filteredOptions.map((option) => (
                <option
                  key={option.id}
                  value={option.id}
                  selected={multiSelect && selected.includes(option.id)}
                >
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        );

      case "radio":
        return (
          <div className={`options-radio layout-${layout}`}>
            {filteredOptions.map((option) => (
              <label
                key={option.id}
                className={`radio-option ${selected.includes(option.id) ? "selected" : ""}`}
              >
                <input
                  type={multiSelect ? "checkbox" : "radio"}
                  name="option-selection"
                  value={option.id}
                  checked={selected.includes(option.id)}
                  onChange={() => handleOptionSelect(option.id)}
                />

                <div className="option-content">
                  {renderIcon(option)}
                  <span className="option-label">{option.label}</span>
                  {option.description && (
                    <span className="option-description">
                      {option.description}
                    </span>
                  )}
                </div>
              </label>
            ))}
          </div>
        );

      case "buttons":
      default:
        return (
          <div className={`options-buttons layout-${layout}`}>
            {filteredOptions.map((option) => (
              <button
                key={option.id}
                className={`option-button ${selected.includes(option.id) ? "selected" : ""} ${equalWidth ? "equal-width" : ""}`}
                onClick={() => handleOptionSelect(option.id)}
                aria-pressed={selected.includes(option.id)}
              >
                {renderIcon(option)}
                {option.label}
              </button>
            ))}
          </div>
        );
    }
  };

  // Generate CSS classes
  const containerClasses = [
    "options-widget",
    `size-${size}`,
    `display-${displayStyle}`,
    isSubmitted ? "submitted" : "",
    isCancelled ? "cancelled" : "",
    isProcessing ? "processing" : "",
  ]
    .filter(Boolean)
    .join(" ");

  // Show result message
  const renderResult = () => {
    if (isSubmitted) {
      const selectedLabels = options
        .filter((option) => selected.includes(option.id))
        .map((option) => option.label)
        .join(", ");

      return (
        <div className="options-result success">
          <div className="result-title">Selection confirmed</div>
          <div className="result-detail">{selectedLabels}</div>
        </div>
      );
    } else if (isCancelled) {
      return (
        <div className="options-result cancelled">Selection cancelled</div>
      );
    }

    return null;
  };

  // Empty state
  if (!options.length) {
    return (
      <div className="options-widget options-empty-state">
        <div className="empty-message">No options available</div>
      </div>
    );
  }

  return (
    <div className={containerClasses}>
      {/* Question and description */}
      {question && <div className="options-question">{question}</div>}
      {description && <div className="options-description">{description}</div>}

      {/* Search input if enabled */}
      {enableSearch && !isSubmitted && !isCancelled && (
        <div className="options-search">
          <input
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder={searchPlaceholder}
          />
          {searchText && (
            <button
              className="clear-search"
              onClick={() => setSearchText("")}
              aria-label="Clear search"
            >
              ✕
            </button>
          )}
        </div>
      )}

      {/* Display options or result */}
      {!(isSubmitted || isCancelled) ? (
        <>
          {/* Options display */}
          {renderOptions()}

          {/* Confirmation buttons if required */}
          {requireConfirmation && !submitOnSelect && (
            <div className="options-actions">
              <button
                className="submit-button"
                onClick={() => handleSubmit()}
                disabled={isProcessing || selected.length === 0}
              >
                {isProcessing ? "Processing..." : submitButtonText}
              </button>

              <button
                className="cancel-button"
                onClick={handleCancel}
                disabled={isProcessing}
              >
                {cancelButtonText}
              </button>
            </div>
          )}
        </>
      ) : (
        renderResult()
      )}
    </div>
  );
};

// PropTypes for documentation and type checking
OptionsWidget.propTypes = {
  data: PropTypes.shape({
    question: PropTypes.string,
    description: PropTypes.string,
    options: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.oneOfType([PropTypes.string, PropTypes.number])
          .isRequired,
        label: PropTypes.string.isRequired,
        description: PropTypes.string,
        icon: PropTypes.oneOfType([PropTypes.string, PropTypes.element]),
      }),
    ).isRequired,
    defaultSelected: PropTypes.arrayOf(
      PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    ),
    multiSelect: PropTypes.bool,
    submitButtonText: PropTypes.string,
    cancelButtonText: PropTypes.string,
    requireConfirmation: PropTypes.bool,
  }),
  metadata: PropTypes.shape({
    displayStyle: PropTypes.oneOf(["buttons", "cards", "dropdown", "radio"]),
    layout: PropTypes.oneOf(["horizontal", "vertical", "grid"]),
    showIcons: PropTypes.bool,
    iconPosition: PropTypes.oneOf(["left", "top", "right"]),
    maxSelectionsAllowed: PropTypes.number,
    enableSearch: PropTypes.bool,
    searchPlaceholder: PropTypes.string,
    size: PropTypes.oneOf(["small", "medium", "large"]),
    equalWidth: PropTypes.bool,
    submitOnSelect: PropTypes.bool,
  }),
  onAction: PropTypes.func,
};

// Default props
OptionsWidget.defaultProps = {
  data: {
    question: "",
    description: "",
    options: [],
    defaultSelected: [],
    multiSelect: false,
    submitButtonText: "Submit",
    cancelButtonText: "Cancel",
    requireConfirmation: true,
  },
  metadata: {
    displayStyle: "buttons",
    layout: "vertical",
    showIcons: true,
    iconPosition: "left",
    maxSelectionsAllowed: 0,
    enableSearch: false,
    searchPlaceholder: "Search options...",
    size: "medium",
    equalWidth: true,
    submitOnSelect: false,
  },
};

export default OptionsWidget;
