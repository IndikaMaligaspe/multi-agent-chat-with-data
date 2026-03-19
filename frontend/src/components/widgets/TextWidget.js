import React, { useState } from "react";
import PropTypes from "prop-types";

/**
 * TextWidget - Displays text content with optional formatting
 *
 * This widget serves as the default fallback for displaying text content.
 * It supports plain text as well as simple formatting options.
 */
const TextWidget = ({ data, metadata = {} }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Extract text and formatting options
  const text = data?.text || "";
  const {
    truncateLength = 300,
    enableTruncation = text.length > truncateLength,
    formatLinks = true,
    formatLineBreaks = true,
  } = metadata;

  // Skip processing for empty content
  if (!text || text.trim() === "") {
    return (
      <div className="text-widget text-widget-empty">No content available</div>
    );
  }

  // Format text - handle basic formatting automatically
  const formatText = (content) => {
    let formatted = content;

    // Convert URLs to clickable links
    if (formatLinks) {
      formatted = formatted.replace(
        /(https?:\/\/[^\s]+)/g,
        '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>',
      );
    }

    // Convert line breaks to <br> tags
    if (formatLineBreaks) {
      formatted = formatted.replace(/\n/g, "<br>");
    }

    return formatted;
  };

  // Determine if we should truncate the text
  const shouldTruncate =
    enableTruncation && !isExpanded && text.length > truncateLength;

  // Truncate if needed
  const displayText = shouldTruncate
    ? `${text.substring(0, truncateLength)}...`
    : text;

  const formattedText = formatText(displayText);

  // Toggle expansion state
  const toggleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  return (
    <div className="text-widget">
      {/* Render formatted text with dangerouslySetInnerHTML for the simple formatting we've applied */}
      <div
        className="text-widget-content"
        dangerouslySetInnerHTML={{ __html: formattedText }}
      />

      {/* Show expand/collapse button if truncation is enabled and needed */}
      {enableTruncation && text.length > truncateLength && (
        <button className="text-widget-toggle" onClick={toggleExpand}>
          {isExpanded ? "Show less" : "Show more"}
        </button>
      )}
    </div>
  );
};

// PropTypes for documentation and type checking
TextWidget.propTypes = {
  data: PropTypes.shape({
    text: PropTypes.string,
  }),
  metadata: PropTypes.shape({
    truncateLength: PropTypes.number,
    enableTruncation: PropTypes.bool,
    formatLinks: PropTypes.bool,
    formatLineBreaks: PropTypes.bool,
  }),
  onAction: PropTypes.func, // Not used in TextWidget but included for consistency
};

// Default props
TextWidget.defaultProps = {
  data: { text: "" },
  metadata: {
    truncateLength: 300,
    enableTruncation: true,
    formatLinks: true,
    formatLineBreaks: true,
  },
};

export default TextWidget;
