import React from "react";

/**
 * A simple direct renderer for tables without using the widget system
 * This bypasses any potential issues in the widget pipeline
 */
const DirectTableRenderer = ({ data }) => {
  console.log("🔍 DIRECT TABLE RENDERER RECEIVED DATA:", data);

  // Extract data safely with enhanced logging
  const headers = data?.headers || data?.columns || [];
  const rows = data?.rows || [];

  // Additional logging for debugging
  console.log("🔍 DIRECT TABLE RENDERER DATA TYPE:", typeof data);
  console.log("🔍 DIRECT TABLE RENDERER DATA KEYS:", Object.keys(data || {}));

  console.log("🔍 DIRECT TABLE RENDERER EXTRACTED:", {
    headers,
    rows,
    headersLength: headers.length,
    rowsLength: rows.length,
    firstRow: rows.length > 0 ? rows[0] : null,
    isFirstRowArray: rows.length > 0 ? Array.isArray(rows[0]) : false,
    dataKeys: Object.keys(data || {}),
  });

  // Handle stringified JSON data
  if (
    typeof data === "string" &&
    (data.startsWith("{") || data.startsWith("["))
  ) {
    console.log(
      "🔍 DIRECT TABLE RENDERER: Attempting to parse stringified JSON data",
    );
    try {
      const parsedData = JSON.parse(data);
      // Extract headers and rows from parsed data
      const parsedHeaders =
        parsedData?.headers ||
        parsedData?.columns ||
        (Array.isArray(parsedData) && parsedData.length > 0
          ? Object.keys(parsedData[0])
          : []);
      const parsedRows =
        parsedData?.rows || (Array.isArray(parsedData) ? parsedData : []);

      if (parsedHeaders.length && parsedRows.length) {
        console.log("🔍 DIRECT TABLE RENDERER: Successfully parsed JSON data");
        return <DirectTableRenderer data={parsedData} />;
      }
    } catch (error) {
      console.error(
        "🔍 DIRECT TABLE RENDERER: Failed to parse JSON data",
        error,
      );
      console.error("🔍 DIRECT TABLE RENDERER: Error details:", {
        message: error.message,
        stack: error.stack,
        name: error.name,
        data: data,
      });
    }
  }

  // Simple check if we have valid data
  if (!headers.length || !rows.length) {
    console.warn(
      "❌ DIRECT TABLE RENDERER: Invalid data - missing headers or rows",
    );
    return (
      <div style={{ padding: "10px", color: "red" }}>
        Invalid table data (missing headers or rows)
      </div>
    );
  }

  console.log("✅ DIRECT TABLE RENDERER: Valid data, rendering table");
  console.log("📊 DIRECT TABLE RENDERER FINAL DATA:", {
    headers,
    headerCount: headers.length,
    rows,
    rowCount: rows.length,
    firstRowSample: rows.length > 0 ? rows[0] : null,
    firstRowType: rows.length > 0 ? typeof rows[0] : null,
    firstRowIsArray: rows.length > 0 ? Array.isArray(rows[0]) : null,
  });

  return (
    <div
      className="direct-table-renderer"
      style={{
        border: "1px solid #4caf50",
        borderRadius: "4px",
        padding: "10px",
        backgroundColor: "#f8fff8",
        marginBottom: "15px",
      }}
    >
      <div
        style={{
          fontSize: "13px",
          color: "#2e7d32",
          marginBottom: "8px",
          fontWeight: "bold",
        }}
      >
        DIRECT TABLE: {rows.length} rows × {headers.length} columns
      </div>

      {/* Simple table renderer */}
      <div style={{ overflowX: "auto" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            border: "1px solid #ddd",
          }}
        >
          <thead>
            <tr style={{ backgroundColor: "#f2f2f2" }}>
              {headers.map((header, index) => (
                <th
                  key={index}
                  style={{
                    padding: "8px",
                    textAlign: "left",
                    borderBottom: "2px solid #ddd",
                  }}
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                style={{
                  backgroundColor: rowIndex % 2 === 0 ? "#ffffff" : "#f9f9f9",
                }}
              >
                {Array.isArray(row)
                  ? row.map((cell, cellIndex) => (
                      <td
                        key={cellIndex}
                        style={{
                          padding: "8px",
                          borderTop: "1px solid #ddd",
                        }}
                      >
                        {cell != null ? String(cell) : ""}
                      </td>
                    ))
                  : headers.map((header, headerIndex) => (
                      <td
                        key={headerIndex}
                        style={{
                          padding: "8px",
                          borderTop: "1px solid #ddd",
                        }}
                      >
                        {row[header] != null ? String(row[header]) : ""}
                      </td>
                    ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DirectTableRenderer;
