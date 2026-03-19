import React, { useState } from "react";
import "./App.css";
import MessageList from "./components/messages/MessageList";
import useChatMessages from "./components/hooks/useChatMessages";
import useSendMessage from "./components/hooks/useSendMessage";
import useWidgetActions from "./components/hooks/useWidgetActions";
import TestTableComponent from "./components/widgets/TestTableComponent";

function App() {
  const [input, setInput] = useState("");
  const {
    messages,
    loading,
    error: chatError,
    addUserMessage,
    addResponseMessage,
  } = useChatMessages();

  const { sendMessage, isSending } = useSendMessage({
    onMessageSent: (query) => {
      // Add user message to the chat when sent
      addUserMessage(query);
    },
    onResponseReceived: (response) => {
      // Add AI response to the chat when received
      console.log(
        "🔄 Response received in App.js, adding to messages:",
        response,
      );
      addResponseMessage(response);
    },
    onError: (err) => {
      console.error("Send message error:", err);
    },
  });
  const handleUpdateState = (newState) => {
    console.log("Widget wishes to update state:", newState);
    // In a real app, you'd integrate this with your state management\
  };

  const handleApiCall = (endpoint, data) => {
    console.log(`Widget making API call to ${endpoint} with data:`, data);
    // In a real app, you'd integrate this with your API service
  };

  const { handleAction: handleWidgetAction } = useWidgetActions({
    onSubmitQuery: sendMessage,
    onUpdateState: handleUpdateState,
    onApiCall: handleApiCall,
  });

  const handleSendMessage = async () => {
    if (!input.trim()) return;
    await sendMessage(input);
    setInput("");
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Define state for showing debug widgets
  const [showDebugWidget, setShowDebugWidget] = useState(false);
  const [showTestTable, setShowTestTable] = useState(false);

  // Define test data for debugging - but don't show by default
  const [debugWidgetType, setDebugWidgetType] = useState("aggregation");

  // Sample widgets for testing
  const debugWidgets = {
    aggregation: {
      type: "aggregation",
      data: {
        value: 3,
        label: "Total Customers (DEBUG)",
        unit: "",
      },
      metadata: {
        format: "number",
        precision: 0,
        size: "medium",
        isDebugWidget: true,
        refreshTimestamp: new Date().toISOString(),
      },
      fallback: "Total Customers: 3 (DEBUG WIDGET)",
    },
    table: {
      type: "table",
      data: {
        columns: ["Customer Number", "Customer Name"],
        rows: [
          ["1", "Customer ID:"],
          ["2", "Customer ID:"],
          ["3", "Customer ID:"],
        ],
        headers: ["Customer Number", "Customer Name"],
      },
      metadata: {
        sortable: true,
        pagination: {
          enabled: false,
          pageSize: 10,
        },
        title: "My customer details (TEST)",
        freshData: true,
        refreshTimestamp: new Date().toISOString(),
        widgetType: "table",
        widgetTransition: {
          from: "aggregation",
          to: "table",
          timestamp: new Date().toISOString(),
          forced: true,
        },
      },
      fallback:
        "Customer Number | Customer Name\n-------------------------------\n1 | Customer ID:\n2 | Customer ID:\n3 | Customer ID:",
    },
  };

  const debugData = debugWidgets[debugWidgetType];

  // Import relevant components for testing
  const WidgetContainer = React.lazy(
    () => import("./components/widgets/WidgetContainer"),
  );

  return (
    <div className="App">
      <div className="chat-container">
        <div className="chat-header">
          <h1>💬 DataChat</h1>
          <p>Ask questions about your data in natural language</p>

          {/* Debug Controls */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              marginTop: "10px",
            }}
          >
            <button
              onClick={() => setShowDebugWidget(!showDebugWidget)}
              style={{
                fontSize: "12px",
                padding: "4px 8px",
                backgroundColor: showDebugWidget ? "#ff6b6b" : "#f0f0f0",
                border: "1px solid #ccc",
                cursor: "pointer",
              }}
            >
              {showDebugWidget ? "Hide Debug Widget" : "Show Debug Widget"}
            </button>

            <button
              onClick={() => setShowTestTable(!showTestTable)}
              style={{
                fontSize: "12px",
                padding: "4px 8px",
                backgroundColor: showTestTable ? "#4a6dff" : "#f0f0f0",
                border: "1px solid #ccc",
                cursor: "pointer",
                marginLeft: "5px",
              }}
            >
              {showTestTable
                ? "Hide Direct Table Test"
                : "Show Direct Table Test"}
            </button>

            {showDebugWidget && (
              <div style={{ display: "flex", gap: "5px" }}>
                <button
                  onClick={() => setDebugWidgetType("aggregation")}
                  style={{
                    fontSize: "12px",
                    padding: "4px 8px",
                    backgroundColor:
                      debugWidgetType === "aggregation" ? "#4caf50" : "#f0f0f0",
                    border: "1px solid #ccc",
                    cursor: "pointer",
                  }}
                >
                  Test Aggregation
                </button>

                <button
                  onClick={() => setDebugWidgetType("table")}
                  style={{
                    fontSize: "12px",
                    padding: "4px 8px",
                    backgroundColor:
                      debugWidgetType === "table" ? "#2196f3" : "#f0f0f0",
                    border: "1px solid #ccc",
                    cursor: "pointer",
                  }}
                >
                  Test Table Widget
                </button>
              </div>
            )}
          </div>

          {/* Debug Widget Display - only shown when explicitly enabled */}
          {showDebugWidget && (
            <div
              style={{
                border: "2px solid red",
                padding: "10px",
                margin: "10px 0",
                background: "#f8f8f8",
              }}
            >
              <div
                style={{ fontSize: "12px", color: "red", marginBottom: "5px" }}
              >
                DEBUG WIDGET (Not from server)
              </div>
              <React.Suspense fallback={<div>Loading widget...</div>}>
                <WidgetContainer
                  widgetType={debugData.type}
                  widgetData={debugData}
                  showFallback={true}
                />
              </React.Suspense>
            </div>
          )}

          {/* Direct Table Widget Test - bypassing the normal message flow */}
          {showTestTable && <TestTableComponent visible={true} />}
        </div>

        <MessageList
          messages={messages}
          loading={loading || isSending}
          chatError={chatError}
          onWidgetAction={handleWidgetAction}
        />
        <div className="input-container">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask a question about your data..."
            disabled={loading || isSending}
          />
          <button
            onClick={handleSendMessage}
            disabled={loading || isSending || !input.trim()}
          >
            {loading || isSending ? "Thinking..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
