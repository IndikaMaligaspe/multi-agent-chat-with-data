import React from "react";
import TableWidget from "./TableWidget";

/**
 * Test component that directly renders a TableWidget with sample data
 * This bypasses the normal message flow to test TableWidget in isolation
 */
const TestTableComponent = ({ visible = true }) => {
  // Use the exact data structure seen in the logs
  const testData = {
    columns: [
      "Customer Number",
      "Customer Name",
      "Email",
      "Location",
      "Registration Date",
    ],
    rows: [
      ["1", "John Doe", "john@example.com", "USA", "March 11, 2026"],
      ["2", "Jane Smith", "jane@example.com", "Canada", "March 12, 2026"],
      ["3", "Bob Johnson", "bob@example.com", "UK", "March 13, 2026"],
    ],
    headers: [
      "Customer Number",
      "Customer Name",
      "Email",
      "Location",
      "Registration Date",
    ],
  };

  const metadata = {
    sortable: true,
    pagination: {
      enabled: false,
      pageSize: 10,
    },
    title: "Test Customer Table (Direct Rendering)",
    freshData: true,
    refreshTimestamp: new Date().toISOString(),
    widgetType: "table",
  };

  if (!visible) {
    return null;
  }

  // Render with debugging information
  return (
    <div
      className="test-table-container"
      style={{
        border: "2px solid blue",
        padding: "15px",
        margin: "15px 0",
        backgroundColor: "#f5f5ff",
      }}
    >
      <h3 style={{ color: "blue" }}>TEST TABLE WIDGET (Direct Rendering)</h3>
      <div style={{ fontSize: "12px", marginBottom: "10px" }}>
        Bypassing normal message flow to test TableWidget directly
      </div>

      {/* Directly render TableWidget with test data */}
      <div style={{ position: "relative", minHeight: "200px" }}>
        <TableWidget
          data={testData}
          metadata={metadata}
          onAction={(type, data) => console.log("Table action:", type, data)}
        />
      </div>

      {/* Quick debugging info */}
      <div
        style={{
          margin: "10px 0",
          padding: "10px",
          backgroundColor: "#f0f0f0",
          fontSize: "12px",
          fontFamily: "monospace",
          borderTop: "1px solid #ccc",
        }}
      >
        <div>Data Structure:</div>
        <div>- Columns: {testData.columns.length}</div>
        <div>- Rows: {testData.rows.length}</div>
        <div>- First Row: [{testData.rows[0].join(", ")}]</div>
      </div>
    </div>
  );
};

export default TestTableComponent;
