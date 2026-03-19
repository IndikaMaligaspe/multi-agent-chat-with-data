import { useState, useCallback } from "react";
import {
  formatUserMessage,
  formatAIMessage,
  parseResponse,
} from "../../utils/messageFormatter";

/**
 * Custom hook for managing chat messages state
 *
 * @param {Object} options - Configuration options
 * @param {Array} options.initialMessages - Optional initial messages
 * @param {Function} options.onMessageAdded - Optional callback when message is added
 * @returns {Object} Chat message state and operations
 */
const useChatMessages = ({
  initialMessages = [],
  onMessageAdded = null,
} = {}) => {
  const [messages, setMessages] = useState(initialMessages);
  const [isLoading, setIsLoading] = useState(false);
  const [responseToQuery, setResponseToQuery] = useState({});

  /**
   * Add a user message to the chat
   *
   * @param {string} content - Message content
   * @param {Object} options - Additional message options
   */
  const addUserMessage = useCallback(
    (content, options = {}) => {
      const userMessage = formatUserMessage(content, options.timestamp);

      // Store the query text for reference
      userMessage.queryText = content;

      setMessages((prevMessages) => [...prevMessages, userMessage]);

      if (onMessageAdded) {
        onMessageAdded(userMessage);
      }

      return userMessage;
    },
    [onMessageAdded],
  );

  /**
   * Add an AI message to the chat
   *
   * @param {string|Object} content - Message content or widget data
   * @param {Object} options - Additional message options
   */
  const addAIMessage = useCallback(
    (content, options = {}) => {
      const aiMessage = formatAIMessage(
        content,
        options.timestamp,
        options.namespace,
      );

      // Associate this response with a query if provided
      if (options.inResponseTo) {
        aiMessage.inResponseTo = options.inResponseTo.id;

        setResponseToQuery((prevMapping) => ({
          ...prevMapping,
          [aiMessage.id]: options.inResponseTo.id,
        }));
      }

      setMessages((prevMessages) => [...prevMessages, aiMessage]);

      if (onMessageAdded) {
        onMessageAdded(aiMessage);
      }

      return aiMessage;
    },
    [onMessageAdded],
  );

  /**
   * Add an AI message from an API response
   *
   * @param {Object} response - API response object
   * @param {Object} options - Additional message options
   */
  const addResponseMessage = useCallback(
    (response, options = {}) => {
      const parsedMessage = parseResponse(response);

      // If namespace is provided in options, override the parsed message namespace
      if (options.namespace) {
        parsedMessage.namespace = options.namespace;
      }

      // Associate this response with a query if provided
      if (options.inResponseTo) {
        parsedMessage.inResponseTo = options.inResponseTo.id;

        setResponseToQuery((prevMapping) => ({
          ...prevMapping,
          [parsedMessage.id]: options.inResponseTo.id,
        }));
      }

      setMessages((prevMessages) => [...prevMessages, parsedMessage]);

      if (onMessageAdded) {
        onMessageAdded(parsedMessage);
      }

      return parsedMessage;
    },
    [onMessageAdded],
  );

  /**
   * Set the loading state
   */
  const setLoading = useCallback((loading) => {
    setIsLoading(loading);
  }, []);

  /**
   * Update a specific message by its index
   *
   * @param {number} index - Message index to update
   * @param {Object} updatedMessage - Updated message data
   */
  const updateMessage = useCallback((index, updatedMessage) => {
    setMessages((prevMessages) => {
      if (index < 0 || index >= prevMessages.length) {
        console.warn(`Cannot update message at index ${index}: out of bounds`);
        return prevMessages;
      }

      const newMessages = [...prevMessages];
      newMessages[index] = {
        ...newMessages[index],
        ...updatedMessage,
      };

      return newMessages;
    });
  }, []);

  /**
   * Find a message by ID in the messages array
   *
   * @param {string} id - The ID of the message to find
   * @returns {Object|null} The message object and its index, or null if not found
   */
  const findMessageById = useCallback(
    (id) => {
      for (let i = 0; i < messages.length; i++) {
        if (messages[i].id === id) {
          return { message: messages[i], index: i };
        }
      }
      return null;
    },
    [messages],
  );

  /**
   * Update or replace an existing message based on query relationship
   *
   * @param {Object} newMessage - The new message data to add or replace with
   * @param {Object} options - Additional options for replacement
   * @returns {Object} The updated or new message
   */
  const updateOrReplaceMessage = useCallback(
    (newMessage, options = {}) => {
      // If specific message ID to replace is provided, use that
      if (options.replaceMessageId) {
        const found = findMessageById(options.replaceMessageId);
        if (found) {
          // Update the existing message
          const updatedMessage = {
            ...found.message,
            ...newMessage,
            updatedAt: new Date().toISOString(), // Update timestamp
          };

          // Replace in messages array
          updateMessage(found.index, updatedMessage);
          return updatedMessage;
        }
      }

      // If message is in response to a query, check if there's an existing response to replace
      if (options.inResponseTo) {
        const queryId = options.inResponseTo.id;

        // Find existing response for this query
        const existingResponseIds = Object.entries(responseToQuery)
          .filter(([_, qId]) => qId === queryId)
          .map(([respId]) => respId);

        // If we found existing responses, update the most recent one
        if (existingResponseIds.length > 0) {
          // Find the most recent response message
          let latestResponseIndex = -1;
          let latestResponseTimestamp = null;

          for (let i = 0; i < messages.length; i++) {
            const msg = messages[i];
            if (!msg.isUser && existingResponseIds.includes(msg.id)) {
              const msgTimestamp = msg.timestamp || msg.createdAt;
              if (
                !latestResponseTimestamp ||
                msgTimestamp > latestResponseTimestamp
              ) {
                latestResponseIndex = i;
                latestResponseTimestamp = msgTimestamp;
              }
            }
          }

          if (latestResponseIndex !== -1) {
            // Update the existing response message
            const updatedMessage = {
              ...messages[latestResponseIndex],
              ...newMessage,
              updatedAt: new Date().toISOString(), // Update timestamp
            };

            // Preserve the ID of the original message
            updatedMessage.id = messages[latestResponseIndex].id;

            // Update in messages array
            updateMessage(latestResponseIndex, updatedMessage);
            return updatedMessage;
          }
        }
      }

      // If no message to replace was found, add as new message
      if (newMessage.isUser) {
        return addUserMessage(newMessage.content, {
          timestamp: newMessage.timestamp || new Date().toISOString(),
          ...options,
        });
      } else {
        return addAIMessage(newMessage.content, {
          timestamp: newMessage.timestamp || new Date().toISOString(),
          namespace: newMessage.namespace,
          inResponseTo: options.inResponseTo,
          ...options,
        });
      }
    },
    [
      messages,
      responseToQuery,
      addUserMessage,
      addAIMessage,
      updateMessage,
      findMessageById,
    ],
  );

  /**
   * Clear all messages
   */
  const clearMessages = useCallback(() => {
    setMessages([]);
    setResponseToQuery({});
  }, []);

  /**
   * Get the last message
   *
   * @returns {Object|null} The last message or null if no messages
   */
  const getLastMessage = useCallback(() => {
    if (messages.length === 0) {
      return null;
    }
    return messages[messages.length - 1];
  }, [messages]);

  /**
   * Get the last user message
   *
   * @returns {Object|null} The last user message or null if no user messages
   */
  const getLastUserMessage = useCallback(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].isUser) {
        return messages[i];
      }
    }
    return null;
  }, [messages]);

  /**
   * Get a response message by query ID
   *
   * @param {string} queryId - The ID of the query message
   * @returns {Object|null} The response message or null if not found
   */
  const getResponseByQueryId = useCallback(
    (queryId) => {
      // Find response IDs that are mapped to this query ID
      const responseIds = Object.entries(responseToQuery)
        .filter(([_, qId]) => qId === queryId)
        .map(([respId]) => respId);

      if (responseIds.length === 0) {
        return null;
      }

      // Find the response message by ID
      for (const message of messages) {
        if (!message.isUser && responseIds.includes(message.id)) {
          return message;
        }
      }

      return null;
    },
    [messages, responseToQuery],
  );

  return {
    messages,
    isLoading,
    responseToQuery,
    addUserMessage,
    addAIMessage,
    addResponseMessage,
    updateMessage,
    updateOrReplaceMessage,
    findMessageById,
    clearMessages,
    setLoading,
    getLastMessage,
    getLastUserMessage,
    getResponseByQueryId,
  };
};

export default useChatMessages;
