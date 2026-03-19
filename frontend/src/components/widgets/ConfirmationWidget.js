import React, { useState } from "react";
import PropTypes from "prop-types";
import "./ConfirmationWidget.css";

/**
 * ConfirmationWidget - Displays a yes/no prompt for user decisions
 *
 * Used for getting explicit confirmation from users before taking actions,
 * showing warnings, or requesting permission.
 */
const ConfirmationWidget = ({ data, metadata = {}, onAction }) => {
  // Extract data properties
  const {
    message = "",
    details = "",
    confirmText = "Confirm",
    cancelText = "Cancel",
    action = "default_action",
    target = null,
    danger = false,
  } = data;

  // Extract metadata with defaults
  const {
    size = "medium", // 'small', 'medium', 'large'
    showIcon = true,
    iconType = danger ? "warning" : "question", // 'question', 'warning', 'info'
    autoFocus = "confirm", // 'confirm', 'cancel', 'none'
    buttonAlignment = "right", // 'left', 'center', 'right', 'spread'
    buttonOrder = "confirmFirst", // 'confirmFirst', 'cancelFirst'
  } = metadata;

  // Track confirmation state
  const [isConfirmed, setIsConfirmed] = useState(false);
  const [isCancelled, setIsCancelled] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  // Handle confirmation
  const handleConfirm = async () => {
    if (isProcessing || isConfirmed || isCancelled) return;

    setIsProcessing(true);

    try {
      if (onAction) {
        await onAction("confirm", {
          action,
          target,
          timestamp: new Date().toISOString(),
        });
      }

      setIsConfirmed(true);
    } catch (error) {
      console.error("Error during confirmation:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle cancellation
  const handleCancel = async () => {
    if (isProcessing || isConfirmed || isCancelled) return;

    setIsProcessing(true);

    try {
      if (onAction) {
        await onAction("cancel", {
          action,
          target,
          timestamp: new Date().toISOString(),
        });
      }

      setIsCancelled(true);
    } catch (error) {
      console.error("Error during cancellation:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  // Get appropriate icon
  const getIcon = () => {
    if (!showIcon) return null;

    switch (iconType) {
      case "warning":
        return <span className="confirmation-icon warning">⚠️</span>;
      case "info":
        return <span className="confirmation-icon info">ℹ️</span>;
      case "question":
      default:
        return <span className="confirmation-icon question">❓</span>;
    }
  };

  // Generate CSS classes
  const containerClasses = [
    "confirmation-widget",
    `size-${size}`,
    danger ? "danger" : "",
    isConfirmed ? "confirmed" : "",
    isCancelled ? "cancelled" : "",
    isProcessing ? "processing" : "",
  ]
    .filter(Boolean)
    .join(" ");

  // Handle button order
  const renderButtons = () => {
    const confirmButton = (
      <button
        className={`confirmation-button confirm ${danger ? "danger" : "primary"}`}
        onClick={handleConfirm}
        disabled={isProcessing || isConfirmed || isCancelled}
        autoFocus={autoFocus === "confirm"}
        aria-busy={isProcessing}
      >
        {isProcessing ? "Processing..." : confirmText}
      </button>
    );

    const cancelButton = (
      <button
        className="confirmation-button cancel"
        onClick={handleCancel}
        disabled={isProcessing || isConfirmed || isCancelled}
        autoFocus={autoFocus === "cancel"}
      >
        {cancelText}
      </button>
    );

    return (
      <div className={`confirmation-buttons button-align-${buttonAlignment}`}>
        {buttonOrder === "cancelFirst"
          ? [cancelButton, confirmButton]
          : [confirmButton, cancelButton]}
      </div>
    );
  };

  // Show result message after action
  const getResultMessage = () => {
    if (isConfirmed) {
      return <div className="confirmation-result success">Confirmed</div>;
    } else if (isCancelled) {
      return <div className="confirmation-result cancelled">Cancelled</div>;
    }
    return null;
  };

  return (
    <div className={containerClasses}>
      <div className="confirmation-content">
        {getIcon()}

        <div className="confirmation-text">
          <div className="confirmation-message">{message}</div>

          {details && <div className="confirmation-details">{details}</div>}
        </div>
      </div>

      {!(isConfirmed || isCancelled) ? renderButtons() : getResultMessage()}
    </div>
  );
};

// PropTypes for documentation and type checking
ConfirmationWidget.propTypes = {
  data: PropTypes.shape({
    message: PropTypes.string.isRequired,
    details: PropTypes.string,
    confirmText: PropTypes.string,
    cancelText: PropTypes.string,
    action: PropTypes.string,
    target: PropTypes.any,
    danger: PropTypes.bool,
  }),
  metadata: PropTypes.shape({
    size: PropTypes.oneOf(["small", "medium", "large"]),
    showIcon: PropTypes.bool,
    iconType: PropTypes.oneOf(["question", "warning", "info"]),
    autoFocus: PropTypes.oneOf(["confirm", "cancel", "none"]),
    buttonAlignment: PropTypes.oneOf(["left", "center", "right", "spread"]),
    buttonOrder: PropTypes.oneOf(["confirmFirst", "cancelFirst"]),
  }),
  onAction: PropTypes.func,
};

// Default props
ConfirmationWidget.defaultProps = {
  data: {
    message: "Are you sure?",
    details: "",
    confirmText: "Confirm",
    cancelText: "Cancel",
    action: "default_action",
    target: null,
    danger: false,
  },
  metadata: {
    size: "medium",
    showIcon: true,
    iconType: "question",
    autoFocus: "confirm",
    buttonAlignment: "right",
    buttonOrder: "confirmFirst",
  },
};

export default ConfirmationWidget;
