import React from "react";
import PropTypes from "prop-types";
import Message from "./Message";

/**
 * UserMessage component for displaying user messages in the chat
 */
const UserMessage = ({ content, timestamp }) => {
  return (
    <Message isUser={true} timestamp={timestamp}>
      {content}
    </Message>
  );
};

UserMessage.propTypes = {
  content: PropTypes.string.isRequired,
  timestamp: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.number,
    PropTypes.instanceOf(Date),
  ]),
};

UserMessage.defaultProps = {
  timestamp: null,
};

export default UserMessage;
