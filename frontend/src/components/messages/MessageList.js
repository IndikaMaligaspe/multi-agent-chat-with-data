import React, { useRef, useEffect } from "react";
import PropTypes from "prop-types";
import UserMessage from "./UserMessage";
import AIMessage from "./AIMessage";
import "./MessageList.css";

/**
 * MessageList component for displaying the conversation history
 * with support for widgets and automatic scrolling
 */
const MessageList = ({
  messages,
  onWidgetAction,
  agentNamespace = null,
  isLoading = false,
}) => {
  const messagesEndRef = useRef(null);

  // Auto-scroll to the bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  return (
    <div className="message-list">
      {messages.map((message, index) => {
        if (message.isUser) {
          return (
            <UserMessage
              key={`user-${index}`}
              content={message.content}
              timestamp={message.timestamp}
              messageId={message.id} // Pass the message ID for tracking
            />
          );
        } else {
          return (
            <AIMessage
              key={`ai-${index}`}
              content={message.content}
              timestamp={message.timestamp}
              onWidgetAction={onWidgetAction}
              namespace={message.namespace || agentNamespace}
              messageId={message.id} // Pass the message ID for tracking and widget transitions
            />
          );
        }
      })}

      {isLoading && (
        <div className="loading-indicator">
          <div className="loading-dots">
            <div className="loading-dot"></div>
            <div className="loading-dot"></div>
            <div className="loading-dot"></div>
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
};

MessageList.propTypes = {
  messages: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired, // Add message ID to PropTypes
      content: PropTypes.oneOfType([PropTypes.string, PropTypes.object])
        .isRequired,
      isUser: PropTypes.bool.isRequired,
      timestamp: PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.number,
        PropTypes.instanceOf(Date),
      ]),
      namespace: PropTypes.string,
    }),
  ).isRequired,
  onWidgetAction: PropTypes.func,
  agentNamespace: PropTypes.string,
  isLoading: PropTypes.bool,
};

MessageList.defaultProps = {
  onWidgetAction: () => {},
  agentNamespace: null,
  isLoading: false,
};

export default MessageList;
