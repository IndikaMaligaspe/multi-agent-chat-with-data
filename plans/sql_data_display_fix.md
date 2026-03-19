# SQL Data Display Fix Plan

## Issue Identified

When querying customer data, the frontend doesn't display any response despite the SQL query being successfully executed in the backend. Based on the Langfuse trace and code analysis, the issue is in the `answer_node` function in `workflow.py`.

### Root Cause

The current implementation passes the entire SQL result object (including metadata) to the LLM instead of properly extracting and formatting just the data portion. This makes it difficult for the LLM to generate a proper, readable response.

```python
# Current problematic code
sql_result = state['sql_result'][-1] if state.get('sql_result') and len(state['sql_result']) > 0 else {}
prompt = f"""Based on the following SQL query and result, provide a natural language answer.

Query: {state['query']}
Results: {sql_result}

Provide a clear, concise answer.
"""
```

The `sql_result` variable contains the entire response object with structure like:

```
{
  "success": true,
  "data": [...actual customer rows...],
  "row_count": 5,
  "error": null
}
```

## Proposed Solution

Update the `answer_node` function to:

1. Extract the actual data from the result object
2. Detect the type of data (raw table data, aggregated result, grouped data, etc.)
3. Format different types of data appropriately
4. Provide clear instructions to the LLM about how to present each type of data
5. Add better error handling and reporting

### Code Changes Required

Replace the current prompt construction with this improved version:

```python
# Get the raw SQL result object
sql_result_obj = state['sql_result'][-1] if state.get('sql_result') and len(state['sql_result']) > 0 else {}

# Extract just the data portion and the success status
data = sql_result_obj.get('data', [])
success = sql_result_obj.get('success', False)
error_message = sql_result_obj.get('error')

# Log data extraction for debugging
log_with_props(logger, "debug", f"Extracted SQL result data in {node_name}",
              node=node_name,
              request_id=request_id,
              data_rows=len(data) if isinstance(data, list) else 0,
              success=success)

# Create an optimized prompt based on success and data type
if not success:
    prompt = f"""The SQL query failed with the following error:

    Query: {state['query']}
    Error: {error_message}

    Please explain what went wrong in simple terms and suggest a fix.
    """
else:
    # Determine query type based on data structure
    is_aggregation = False
    is_grouped = False

    if isinstance(data, list) and data:
        # Check for aggregation (typically single row with 1-2 columns)
        is_aggregation = (len(data) == 1 and len(data[0].keys()) <= 2)

        # Check for grouped data (multiple rows with count/aggregate columns)
        if len(data) > 1 and any(k for k in data[0].keys() if k.lower().startswith(('count', 'sum', 'avg', 'min', 'max'))):
            is_grouped = True

    # Customize prompt based on data type
    data_type_instruction = "This is tabular data. Format it in a clean, readable way for the user."
    if is_aggregation:
        data_type_instruction = "This is an aggregation result. Present it clearly with proper context."
    elif is_grouped:
        data_type_instruction = "This is grouped data with aggregations. Present it as a summary with key insights."

    prompt = f"""Based on the following SQL query and result, provide a natural language answer.

    Query: {state['query']}
    Data: {data}

    {data_type_instruction}

    If the data is empty, mention that no records were found that match the criteria.
    Provide any valuable insights visible in the data.
    Use markdown formatting when appropriate for better readability.
    """
```

### Additional Improvements

1. **Tabular Formatting**: When displaying raw table data, instruct the LLM to use markdown tables for better readability.

2. **Error Messages**: Better handling of various error scenarios (empty data, query errors, etc.).

3. **Auto-detection of Query Types**: Automatically detect the type of SQL query (SELECT, COUNT, AVG, etc.) by examining both the query string and result structure.

4. **Enhanced Logging**: Add detailed logging to track how the data is being processed and formatted.

## Implementation Steps

1. Modify the `answer_node` function in `workflow.py` with the improved code
2. Add log statements to track data processing
3. Test with various types of queries:
   - Raw data query: `SELECT * FROM customers`
   - Count query: `SELECT COUNT(*) FROM customers`
   - Group by query: `SELECT country, COUNT(*) FROM customers GROUP BY country`
   - No results query: `SELECT * FROM customers WHERE email = 'nonexistent@example.com'`
   - Error-causing query: `SELECT * FROM nonexistent_table`

## Expected Outcome

After implementing these changes:

1. Raw customer data will be properly displayed in a readable format
2. Different query types (aggregation, grouped data, etc.) will be presented appropriately
3. Error messages will be clear and helpful
4. The user experience will be consistent across all query types
