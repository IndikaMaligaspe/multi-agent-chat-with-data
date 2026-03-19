import React from "react";
import PropTypes from "prop-types";
import "./Message.css";

/**
 * Base Message component that provides the structure for all message types
 */
const Message = ({
  children,
  isUser,
  timestamp,
  className,
  messageId, // Add messageId prop for tracking and widget state management
  ...props
}) => {
  const messageClasses = `message ${isUser ? "message-user" : "message-ai"} ${className || ""}`;

  return (
    <div className={messageClasses} data-message-id={messageId} {...props}>
      <div className="message-content">{children}</div>
      {timestamp && (
        <div className="message-timestamp">
          {new Date(timestamp).toLocaleTimeString()}
          {messageId && (
            <span
              className="message-id"
              style={{ fontSize: "9px", marginLeft: "5px", opacity: 0.6 }}
            >
              {messageId.substring(0, 8)}
            </span>
          )}
        </div>
      )}
    </div>
  );
};

Message.propTypes = {
  children: PropTypes.node.isRequired,
  isUser: PropTypes.bool,
  timestamp: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.number,
    PropTypes.instanceOf(Date),
  ]),
  className: PropTypes.string,
  messageId: PropTypes.string, // Add prop type for messageId
};

Message.defaultProps = {
  isUser: false,
  timestamp: null,
  className: "",
  messageId: null, // Add default prop for messageId
};

export default Message;
