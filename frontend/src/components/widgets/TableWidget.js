import React, { useState, useMemo } from "react";
import PropTypes from "prop-types";
import "./TableWidget.css"; // We'll create this CSS file later

/**
 * TableWidget - Displays tabular data with sorting and pagination
 *
 * This component handles the display of structured data in a table format
 * with support for:
 * - Column sorting
 * - Pagination
 * - Responsive layout
 * - Empty state handling
 * - Accessibility features
 */
const TableWidget = ({ data, metadata = {}, onAction }) => {
  // Debug - Log the props received by TableWidget with component start marker
  console.log("🔶 TABLE WIDGET COMPONENT RENDERING START 🔶");
  console.log("TableWidget received data:", data);
  console.log("TableWidget received metadata:", metadata);

  // Debug-specific marker for the rendering process
  console.log("🔵 TABLE WIDGET RENDER CALLED - Component lifecycle checkpoint");

  // Extract data from props - handle both direct data and nested data structure
  let columns = [];
  let rows = [];

  console.log("TableWidget detailed data structure analysis:", {
    dataType: typeof data,
    isArray: Array.isArray(data),
    hasColumns: data && data.columns,
    hasRows: data && data.rows,
    hasHeaders: data && data.headers,
    dataKeys: data ? Object.keys(data) : [],
    metadata: metadata ? Object.keys(metadata) : [],
    widgetType: metadata?.widgetType || "unknown",
    transition: metadata?.widgetTransition
      ? `${metadata.widgetTransition.from} -> ${metadata.widgetTransition.to}`
      : "none",
  });

  if (data) {
    // Check if data follows the backend structure with nested columns and rows
    if (data.columns && data.rows) {
      columns = data.columns;
      rows = data.rows;
      console.log("Using columns and rows from data object");
    }
    // Also check for headers field which might be an alias for columns
    else if (data.headers && data.rows) {
      columns = data.headers;
      rows = data.rows;
      console.log("Using headers and rows from data object");
    }
    // If data itself is an array of objects, extract columns from first item
    else if (
      Array.isArray(data) &&
      data.length > 0 &&
      typeof data[0] === "object"
    ) {
      rows = data;
      columns = Object.keys(data[0]);
      console.log("Extracted columns from array of objects");
    }
  }

  const memoizedRows = useMemo(() => rows, [rows]);

  // Debug - Log extracted columns and rows
  console.log("TableWidget extracted columns:", columns);
  console.log("TableWidget extracted rows:", memoizedRows);

  // Extract metadata with defaults
  const {
    title = "",
    sortable = true,
    pagination = { enabled: memoizedRows.length > 10, pageSize: 10 },
    emptyStateMessage = "No data available",
    highlightedColumns = [],
    stickyHeader = true,
    stickyFirstColumn = false,
    dense = false,
    zebra = true,
  } = metadata;

  // Component state
  const [sortConfig, setSortConfig] = useState({
    key: null,
    direction: "ascending",
  });

  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = pagination.pageSize || 10;
  const paginationEnabled =
    pagination.enabled && memoizedRows.length > pageSize;

  // Handle sorting request
  const requestSort = (key) => {
    if (!sortable) return;

    let direction = "ascending";
    if (sortConfig.key === key && sortConfig.direction === "ascending") {
      direction = "descending";
    }
    setSortConfig({ key, direction });
  };

  // Get sorted data
  const sortedData = useMemo(() => {
    // Return original data if sorting is disabled or no sort key
    if (!sortable || !sortConfig.key) {
      return memoizedRows;
    }

    return [...memoizedRows].sort((a, b) => {
      // Handle null/undefined values
      if (a[sortConfig.key] == null)
        return sortConfig.direction === "ascending" ? -1 : 1;
      if (b[sortConfig.key] == null)
        return sortConfig.direction === "ascending" ? 1 : -1;

      // Compare based on data type
      if (typeof a[sortConfig.key] === "string") {
        return sortConfig.direction === "ascending"
          ? a[sortConfig.key].localeCompare(b[sortConfig.key])
          : b[sortConfig.key].localeCompare(a[sortConfig.key]);
      } else {
        if (a[sortConfig.key] < b[sortConfig.key]) {
          return sortConfig.direction === "ascending" ? -1 : 1;
        }
        if (a[sortConfig.key] > b[sortConfig.key]) {
          return sortConfig.direction === "ascending" ? 1 : -1;
        }
      }
      return 0;
    });
  }, [memoizedRows, sortConfig, sortable]);

  // Get paginated data
  const paginatedData = useMemo(() => {
    if (!paginationEnabled) {
      return sortedData;
    }

    const startIndex = (currentPage - 1) * pageSize;
    return sortedData.slice(startIndex, startIndex + pageSize);
  }, [sortedData, currentPage, pageSize, paginationEnabled]);

  // Pagination controls
  const totalPages = Math.ceil(sortedData.length / pageSize);

  const handlePageChange = (newPage) => {
    if (newPage < 1 || newPage > totalPages) return;
    setCurrentPage(newPage);

    // Notify parent of pagination change if callback provided
    if (onAction) {
      onAction("pagination", {
        page: newPage,
        pageSize,
        totalPages,
        totalRows: memoizedRows.length,
      });
    }
  };

  // Sort indicator
  const getSortDirectionIndicator = (column) => {
    if (!sortable || column !== sortConfig.key) return null;
    return sortConfig.direction === "ascending" ? (
      <span className="sort-indicator asc" aria-label="sorted ascending">
        ▲
      </span>
    ) : (
      <span className="sort-indicator desc" aria-label="sorted descending">
        ▼
      </span>
    );
  };

  // Generate appropriate CSS classes
  const tableClasses = [
    "table-widget",
    stickyHeader ? "sticky-header" : "",
    stickyFirstColumn ? "sticky-first-column" : "",
    dense ? "dense" : "",
    zebra ? "zebra" : "",
  ]
    .filter(Boolean)
    .join(" ");

  // Handle row click
  const handleRowClick = (row, index) => {
    if (onAction) {
      onAction("rowClick", { row, index });
    }
  };

  // Debug - Check empty state conditions with detailed info
  console.log("🔴 Empty state check - columns length:", columns.length);
  console.log("🔴 Empty state check - rows length:", memoizedRows.length);
  console.log("🔴 Empty state check - columns content:", columns);
  console.log(
    "🔴 Empty state check - first few rows:",
    memoizedRows.slice(0, 2),
  );

  // Empty state
  if (!columns.length || !memoizedRows.length) {
    console.warn(
      "⚠️ TableWidget rendering EMPTY STATE due to missing columns or rows",
    );
    console.log("Empty state reason:", {
      noColumns: !columns.length,
      noRows: !memoizedRows.length,
      columnsType: typeof columns,
      rowsType: typeof memoizedRows,
    });
    return (
      <div className="table-widget table-empty-state">
        <div className="empty-message">{emptyStateMessage}</div>
      </div>
    );
  }

  console.log(
    "✅ TableWidget passed empty state check, proceeding to render table",
  );

  // Add final rendering log
  console.log("🟢 TABLE WIDGET FINAL RENDERING with:", {
    columnCount: columns.length,
    rowCount: paginatedData.length,
    title: title || "No title",
    sortable,
    paginationEnabled,
    tableClasses,
  });

  return (
    <div className="table-widget-container">
      {title && <h3 className="table-title">{title}</h3>}

      <div className="table-responsive">
        <table className={tableClasses}>
          <thead>
            <tr>
              {columns.map((column, index) => (
                <th
                  key={column}
                  onClick={() => requestSort(column)}
                  className={`
                    ${sortable ? "sortable" : ""}
                    ${highlightedColumns.includes(column) ? "highlighted" : ""}
                    ${sortConfig.key === column ? "sorted" : ""}
                  `.trim()}
                  aria-sort={
                    sortConfig.key === column ? sortConfig.direction : "none"
                  }
                >
                  {column}
                  {getSortDirectionIndicator(column)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginatedData.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                onClick={() => handleRowClick(row, rowIndex)}
                className={rowIndex % 2 === 0 ? "even" : "odd"}
              >
                {columns.map((column, columnIndex) => (
                  <td
                    key={`${rowIndex}-${column}`}
                    className={
                      highlightedColumns.includes(column) ? "highlighted" : ""
                    }
                  >
                    {/* Handle both array rows (indexed access) and object rows (property access) */}
                    {Array.isArray(row)
                      ? row[columnIndex] != null
                        ? row[columnIndex].toString()
                        : ""
                      : row[column] != null
                        ? row[column].toString()
                        : ""}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination UI */}
      {paginationEnabled && (
        <div className="table-pagination">
          <button
            className="pagination-button prev"
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={currentPage === 1}
            aria-label="Previous page"
          >
            ← Previous
          </button>

          <div className="pagination-info">
            Page {currentPage} of {totalPages}
            <span className="pagination-detail">
              ({sortedData.length} total rows)
            </span>
          </div>

          <button
            className="pagination-button next"
            onClick={() => handlePageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
            aria-label="Next page"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
};

// PropTypes for documentation and type checking
TableWidget.propTypes = {
  data: PropTypes.shape({
    columns: PropTypes.arrayOf(PropTypes.string),
    rows: PropTypes.arrayOf(PropTypes.object),
  }),
  metadata: PropTypes.shape({
    title: PropTypes.string,
    sortable: PropTypes.bool,
    pagination: PropTypes.shape({
      enabled: PropTypes.bool,
      pageSize: PropTypes.number,
    }),
    emptyStateMessage: PropTypes.string,
    highlightedColumns: PropTypes.arrayOf(PropTypes.string),
    stickyHeader: PropTypes.bool,
    stickyFirstColumn: PropTypes.bool,
    dense: PropTypes.bool,
    zebra: PropTypes.bool,
  }),
  onAction: PropTypes.func,
};

// Default props
TableWidget.defaultProps = {
  data: { columns: [], rows: [] },
  metadata: {
    sortable: true,
    pagination: { enabled: true, pageSize: 10 },
    emptyStateMessage: "No data available",
    highlightedColumns: [],
    stickyHeader: true,
    stickyFirstColumn: false,
    dense: false,
    zebra: true,
  },
};

export default TableWidget;
