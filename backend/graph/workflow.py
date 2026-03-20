from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List, Dict, Any
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
import operator
import time
from observability.logging import get_logger, log_with_props, log_execution_time, RequestContext
import re
import json
from langchain_core.messages import AIMessage

# Try to import WidgetFormatter with proper error handling
try:
    from widget_formatter import WidgetFormatter, DateTimeEncoder
    WIDGET_FORMATTER_AVAILABLE = True
except ImportError:
    logger = get_logger(__name__)  # Create logger early for error reporting
    logger.error("Failed to import WidgetFormatter. Widget functionality will be limited.", exc_info=True)
    WIDGET_FORMATTER_AVAILABLE = False
    
    # Create fallback implementations to avoid errors
    class FallbackWidgetFormatter:
        """Fallback implementation when real WidgetFormatter is unavailable"""
        @staticmethod
        def format_response(data, query="", widget_type="text", metadata=None, fallback=None):
            """Simple fallback that returns data as text widget"""
            return {
                "type": "text",
                "data": str(data),
                "query": query,
                "fallback": fallback or str(data)
            }
    
    class FallbackDateTimeEncoder(json.JSONEncoder):
        """Simple fallback encoder that converts datetime to ISO format string"""
        def default(self, obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            return str(obj)
    
    # Assign fallbacks to the expected names
    WidgetFormatter = FallbackWidgetFormatter
    DateTimeEncoder = FallbackDateTimeEncoder

# Initialize logger (after potential import errors)
logger = get_logger(__name__)

class AgentState(TypedDict):
    """State shared between agents"""
    query: str
    sql_result: Annotated[List[Dict[str, Any]], operator.add]
    validation_result:Annotated[List[Dict[str, Any]], operator.add]
    final_answer: str
    errors: Annotated[List[Dict[str, Any]], operator.add]

    # Feedback evaluation fields
    feedback_score: int          # LLM quality score 1-10 (0 = not yet evaluated)
    feedback_message: str        # Evaluator's critique / reasoning
    feedback_attempt: int        # Number of improvement attempts so far
    feedback_exceeded: bool      # True when max attempts reached without passing

def sql_node(state: AgentState) -> AgentState:
    """SQL Agent Node"""
    node_name = "sql_node"
    request_id = RequestContext.get_request_id()
    
    # Log node entry with query info
    log_with_props(logger, "info", f"Entering {node_name}",
                  node=node_name,
                  request_id=request_id,
                  query_length=len(state['query']) if 'query' in state else 0)
    
    try:
        # Measure execution time
        with log_execution_time(logger, f"{node_name}_execution"):
            # Here you would call your SQL agent to execute the query and get results
            from agents.sql_agent import SQLAgent
            
            agent = SQLAgent()
            result = agent.run(state['query'])
        
        # Log successful execution
        success = result.get('success', False)
        log_with_props(logger, "info" if success else "warning",
                      f"SQL agent execution {'succeeded' if success else 'failed'}",
                      node=node_name,
                      request_id=request_id,
                      success=success,
                      error=result.get('error') if not success else None)
        
        updated_state = {
            **state,
            'sql_result': state.get('sql_result', []) + [result],
        }
        
        # Log node exit
        log_with_props(logger, "info", f"Exiting {node_name}",
                      node=node_name,
                      request_id=request_id)
        return updated_state
    except Exception as e:
        # Log any exceptions
        log_with_props(logger, "error", f"Error in {node_name}",
                      node=node_name,
                      request_id=request_id,
                      error=str(e),
                      exc_info=True)
        # Re-raise to maintain normal flow
        raise

def validation_node(state: AgentState) -> AgentState:
    """Validation Agent Node"""
    node_name = "validation_node"
    request_id = RequestContext.get_request_id()
    
    # Log node entry
    log_with_props(logger, "info", f"Entering {node_name}",
                  node=node_name,
                  request_id=request_id)
    
    try:
        # Measure execution time
        start_time = time.time()
        
        # Here you would call your validation agent to validate the SQL results
        sql_result = state['sql_result'][-1] if state.get('sql_result') and len(state['sql_result']) > 0 else {}
        
        # Simple validation
        is_valid = sql_result.get('success', False)
        
        validation = {
            'is_valid': is_valid,
            'message': 'Query execution successful' if is_valid else 'Validation failed'
        }
        
        # Log validation result
        log_with_props(logger, "info", f"Validation {'succeeded' if is_valid else 'failed'}",
                      node=node_name,
                      request_id=request_id,
                      is_valid=is_valid,
                      execution_time_ms=round((time.time() - start_time) * 1000, 2))
        
        updated_state = {
            **state,
            'validation_result': [validation],
        }
        
        # Log node exit
        log_with_props(logger, "info", f"Exiting {node_name}",
                      node=node_name,
                      request_id=request_id)
        return updated_state
    except Exception as e:
        # Log any exceptions
        log_with_props(logger, "error", f"Error in {node_name}",
                      node=node_name,
                      request_id=request_id,
                      error=str(e),
                      exc_info=True)
        # Re-raise to maintain normal flow
        raise

def answer_node(state: AgentState) -> AgentState:
    """ Final Answer Generation Node """
    node_name = "answer_node"
    request_id = RequestContext.get_request_id()
    
    # Log node entry
    log_with_props(logger, "info", f"Entering {node_name}",
                  node=node_name,
                  request_id=request_id)
    
    try:
        # Initialize LLM
        llm = ChatOpenAI(model="gpt-4", temperature=0.3)
        
        # Get the raw SQL result object
        sql_result_obj = state['sql_result'][-1] if state.get('sql_result') and len(state['sql_result']) > 0 else {}
        
        # Extract success status and error message from the SQL result object
        success = sql_result_obj.get('success', False)
        error_message = sql_result_obj.get('error')
        existing_answer = sql_result_obj.get('output', '')

        # Function to extract numerical data from simple text responses
        def extract_numerical_data(text):
            """
            Extract numerical data from simple text responses like:
            "You have a total of 3 customers."
            "There are 42 orders in the database."
            "The average order value is $56.78."
            
            Returns a list with a dict containing the extracted value and appropriate labels,
            or None if no numerical data could be extracted.
            """
            if not isinstance(text, str) or not text:
                return None
                
            # Patterns to match different types of numerical responses
            count_patterns = [
                # "You have X customers", "There are X customers"
                r'(?:have|has|are|is)(?:\sa\stotal\sof)?(?:\sabout)?\s+(\d+)\s+(\w+)',
                # "Total customers: X", "Number of orders: X"
                r'(?:total|number\sof)\s+(\w+)[:\s]+(\d+)',
                # "X customers found", "X records match"
                r'(\d+)\s+(\w+)(?:\s+found|\s+exist|\s+match)',
            ]
            
            for pattern in count_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    for match in matches:
                        # Check which group contains the number vs the label
                        if match[0].isdigit():
                            value, label = int(match[0]), match[1]
                        else:
                            label, value = match[0], int(match[1])
                        
                        log_with_props(logger, "debug", f"Extracted numerical data in {node_name}",
                                      node=node_name,
                                      request_id=request_id,
                                      value=value,
                                      label=label)
                        
                        return [{
                            "value": value,
                            "label": f"Total {label.title()}"
                        }]
            
            # Extract floating point values (like prices, averages)
            decimal_patterns = [
                # "Average is X", "Price is X"
                r'(?:average|avg|price|cost|value)(?:\s+is|\s*:)\s*\$?(\d+\.\d+)',
                # "X dollars average"
                r'\$?(\d+\.\d+)(?:\s+dollars|\s+average|\s+mean)'
            ]
            
            for pattern in decimal_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    value = float(matches[0])
                    
                    # Try to determine an appropriate label based on the text
                    label = "Value"
                    if "price" in text.lower() or "$" in text or "dollar" in text.lower():
                        label = "Price"
                    elif "average" in text.lower() or "avg" in text.lower():
                        label = "Average"
                    elif "cost" in text.lower():
                        label = "Cost"
                    
                    log_with_props(logger, "debug", f"Extracted decimal value in {node_name}",
                                  node=node_name,
                                  request_id=request_id,
                                  value=value,
                                  label=label)
                    
                    return [{
                        "value": value,
                        "label": label
                    }]
            
            return None
            
        # Function to parse text-formatted SQL results into structured data
        def parse_formatted_text(text):
            """
            Parse text-formatted SQL results into structured data.
            Handles formats like:
            ```
            1. **John Doe**
               - Email: john@example.com
               - Country: USA
               - Created At: March 11, 2026
            ```
            """
            log_with_props(logger, "debug", f"Attempting to parse formatted text in {node_name}",
                           node=node_name,
                           request_id=request_id,
                           text_length=len(text) if text else 0)
            
            # Check if it's a text-formatted result
            if not isinstance(text, str) or not text or not ('**' in text and '-' in text):
                log_with_props(logger, "debug", f"Text doesn't match expected format in {node_name}",
                               node=node_name,
                               request_id=request_id)
                return []
            
            # Extract customer entries using regex
            # This pattern looks for numbered entries with bold names
            customer_pattern = r'(\d+)\.\s+\*\*(.*?)\*\*(.*?)(?=\d+\.\s+\*\*|\Z)'
            customers = re.findall(customer_pattern, text, re.DOTALL)
            
            if not customers:
                log_with_props(logger, "debug", f"No customer entries found in text in {node_name}",
                               node=node_name,
                               request_id=request_id)
                return []
                
            structured_data = []
            
            # Process each customer entry
            for customer in customers:
                # Extract fields like "- Field: Value"
                number, name, details = customer
                field_pattern = r'-\s+(.*?):\s+(.*?)(?=\n\s+-|\Z)'
                fields = re.findall(field_pattern, details, re.DOTALL)
                
                # Create customer object
                customer_obj = {"Customer Number": number.strip(), "Customer Name": name.strip()}
                
                # Add each field
                for field_name, field_value in fields:
                    customer_obj[field_name.strip()] = field_value.strip()
                    
                structured_data.append(customer_obj)
            
            log_with_props(logger, "info", f"Successfully parsed {len(structured_data)} customers from text in {node_name}",
                           node=node_name,
                           request_id=request_id,
                           fields=list(structured_data[0].keys()) if structured_data else [])
                           
            return structured_data
        
        # Dump the full structure for debugging
        log_with_props(logger, "debug", f"Full SQL result object in {node_name}",
                      node=node_name,
                      request_id=request_id,
                      sql_result_obj=str(sql_result_obj)[:500])  # Truncate to avoid huge logs
        
        # More aggressive approach to find data anywhere in the structure
        raw_data = []
        
        # First check direct access
        if 'data' in sql_result_obj:
            raw_data = sql_result_obj.get('data', [])
        # Check if it's in a result dictionary
        elif 'result' in sql_result_obj and isinstance(sql_result_obj['result'], dict):
            if 'data' in sql_result_obj['result']:
                raw_data = sql_result_obj['result'].get('data', [])
        # Check if it's in the SQL output
        elif 'output' in sql_result_obj and isinstance(sql_result_obj['output'], dict):
            if 'data' in sql_result_obj['output']:
                raw_data = sql_result_obj['output'].get('data', [])
        # Check if the output is a text-formatted result like the customer example
        elif 'output' in sql_result_obj and isinstance(sql_result_obj['output'], str):
            log_with_props(logger, "info", f"Detected text-formatted SQL output in {node_name}",
                          node=node_name,
                          request_id=request_id,
                          output_sample=sql_result_obj['output'][:100] if sql_result_obj['output'] else "")
            # Try to parse the text-formatted output
            text_data = parse_formatted_text(sql_result_obj['output'])
            if text_data:
                raw_data = text_data
                log_with_props(logger, "info", f"Successfully parsed text-formatted SQL output in {node_name}",
                              node=node_name,
                              request_id=request_id,
                              parsed_rows=len(text_data))
            else:
                # Try to extract numerical information from simple text responses
                numerical_data = extract_numerical_data(sql_result_obj['output'])
                if numerical_data:
                    raw_data = numerical_data
                    log_with_props(logger, "info", f"Extracted numerical data from text response in {node_name}",
                                  node=node_name,
                                  request_id=request_id,
                                  numerical_value=str(numerical_data))
        # Check if we need to parse the last SQL agent message
        elif 'messages' in sql_result_obj and isinstance(sql_result_obj['messages'], list) and sql_result_obj['messages']:
            last_message = sql_result_obj['messages'][-1]
            if isinstance(last_message, dict) and 'content' in last_message:
                content = last_message['content']
                # Try to find and parse a JSON block in the content
                try:
                    json_matches = re.findall(r'```json\n(.*?)\n```', content, re.DOTALL)
                    if json_matches:
                        parsed_content = json.loads(json_matches[0])
                        if isinstance(parsed_content, dict) and 'data' in parsed_content:
                            raw_data = parsed_content['data']
                    else:
                        # If no JSON block, try to parse as text-formatted output
                        text_data = parse_formatted_text(content)
                        if text_data:
                            raw_data = text_data
                except Exception as e:
                    log_with_props(logger, "warning", f"Failed to extract data from message content: {str(e)}",
                                  node=node_name,
                                  request_id=request_id,
                                  error=str(e))
        
        # Add detailed logging about the data extraction
        log_with_props(logger, "debug", f"Data extraction attempt in {node_name}",
                      node=node_name,
                      request_id=request_id,
                      sql_result_keys=list(sql_result_obj.keys()) if isinstance(sql_result_obj, dict) else "Not a dict",
                      raw_data_length=len(raw_data) if isinstance(raw_data, list) else "Not a list",
                      raw_data_type=type(raw_data).__name__)
        
        # Pre-serialize data to handle datetime objects before processing
        if isinstance(raw_data, list):
            try:
                # Convert datetime objects to ISO format strings using DateTimeEncoder
                # Split into two steps for better debugging
                json_str = json.dumps(raw_data, cls=DateTimeEncoder)
                data = json.loads(json_str)
                log_with_props(logger, "debug", f"Successfully pre-serialized data in {node_name}",
                              node=node_name,
                              request_id=request_id,
                              raw_data_length=len(raw_data),
                              processed_data_length=len(data))
            except Exception as e:
                log_with_props(logger, "warning", f"Failed to pre-serialize data: {str(e)}",
                              node=node_name,
                              request_id=request_id,
                              error=str(e))
                # Fall back to raw data if serialization fails
                data = raw_data
        else:
            data = raw_data
        
        # Log data extraction for debugging
        log_with_props(logger, "debug", f"Extracted SQL result data in {node_name}",
                      node=node_name,
                      request_id=request_id,
                      data_rows=len(data) if isinstance(data, list) else 0,
                      raw_data_rows=len(raw_data) if isinstance(raw_data, list) else 0,
                      success=success,
                      data_sample=str(data[:1]) if isinstance(data, list) and data else "No data")
        
        if not success:
            # Handle error case with text widget
            log_with_props(logger, "warning", f"SQL query failed: {error_message}",
                          node=node_name,
                          request_id=request_id,
                          error=error_message)
                          
            error_response = WidgetFormatter.format_response(
                f"The query failed: {error_message}",
                query=state['query'],
                widget_type="text"
            )
            
            return {
                **state,
                'final_answer': error_response
            }
        
        # If we have text output but parsing failed, check for simple numerical response before falling back to text
        if 'output' in sql_result_obj and isinstance(sql_result_obj['output'], str) and not data:
            # Try to detect if this is a numerical response that should be an aggregation widget
            numerical_data = extract_numerical_data(sql_result_obj['output'])
            
            if numerical_data and len(numerical_data) == 1:
                # Log the numerical data using JSON serialization for debugging
                # Use the json module that's imported at the top level
                json_data = json.dumps(numerical_data, cls=DateTimeEncoder)
                
                log_with_props(logger, "info", f"Converting simple text to aggregation widget in {node_name}",
                              node=node_name,
                              request_id=request_id,
                              numerical_data=json_data,
                              data_value=numerical_data[0].get('value'),
                              data_label=numerical_data[0].get('label'))
                
                # Create a clean data object for the aggregation widget
                aggregation_data = {
                    "value": numerical_data[0].get('value'),
                    "label": numerical_data[0].get('label'),
                    "unit": ""  # Add an empty unit for consistency
                }
                
                log_with_props(logger, "info", f"Detected numerical data structure from extract_numerical_data",
                              node=node_name,
                              request_id=request_id,
                              data_value=aggregation_data['value'],
                              data_label=aggregation_data['label'])
                
                # Use the properly structured data object for the aggregation widget
                aggregation_response = WidgetFormatter.format_response(
                    data=aggregation_data,  # Use the clean data object
                    query=state['query'],
                    widget_type="aggregation",  # Explicitly set to aggregation
                    fallback=sql_result_obj['output']  # Keep original text as fallback
                )
                
                # Double-check the widget type in the response
                log_with_props(logger, "info", f"Using explicitly set aggregation widget type",
                              node=node_name,
                              request_id=request_id,
                              widget_type=aggregation_response.get('type'),
                              data_value=aggregation_data['value'],
                              data_label=aggregation_data['label'])
                
                # Additional log to verify the final widget type
                log_with_props(logger, "info", f"Final widget type: {aggregation_response.get('type')}",
                              node=node_name,
                              request_id=request_id,
                              widget_type=aggregation_response.get('type'),
                              is_numerical_format=True)
                
                # Return immediately with the aggregation response
                return {
                    **state,
                    'final_answer': aggregation_response
                }
            else:
                # No numerical data found, fall back to text widget
                log_with_props(logger, "info", f"Using text widget as fallback for unparseable output in {node_name}",
                              node=node_name,
                              request_id=request_id)
                
                text_response = WidgetFormatter.format_response(
                    data=sql_result_obj['output'],
                    query=state['query'],
                    widget_type="text"
                )
                
                return {
                    **state,
                    'final_answer': text_response
                }

        # If data is empty, fall back to LLM to explain why
        if not data:
            log_with_props(logger, "info", f"SQL query returned no data. Falling back to LLM for response.",
                           node=node_name,
                           request_id=request_id)
            prompt = f"""The SQL query for "{state['query']}" returned no data. Please generate a user-friendly response indicating that no records were found.
                         Also, provide suggestions for how the user might rephrase their query or what other information they might ask for.
                         Format the response using markdown."""
            response = llm.invoke(prompt)
            formatted_widget = WidgetFormatter.format_response(
                data=response.content,
                query=state['query'],
                widget_type="text"
            )
            return {
                **state,
                'final_answer': formatted_widget
            }

        # If query is about customers or looks like it should be a table, force table widget
        should_be_table = False
        query_lower = state['query'].lower()
        
        # More robust detection for customer-related queries
        customer_keywords = ["customer", "customers", "client", "clients"]
        show_keywords = ["show", "list", "display", "get", "give", "see"]
        
        # Check if query is asking to show customer data
        is_customer_query = any(keyword in query_lower for keyword in customer_keywords)
        is_show_query = any(keyword in query_lower for keyword in show_keywords) or "all" in query_lower
        
        if (is_customer_query and is_show_query) or \
           ("show" in query_lower and "all" in query_lower) or \
           (isinstance(data, list) and len(data) > 2 and all(isinstance(row, dict) for row in data)):
            should_be_table = True
            
        # Log the detection for debugging
        log_with_props(logger, "info", f"Table widget detection for query: {state['query']}",
                       node=node_name,
                       request_id=request_id,
                       is_customer_query=is_customer_query,
                       is_show_query=is_show_query,
                       should_be_table=should_be_table)
            
        log_with_props(logger, "info", f"Determining widget type for query: {state['query']}",
                       node=node_name,
                       request_id=request_id,
                       should_be_table=should_be_table,
                       data_length=len(data) if isinstance(data, list) else 0,
                       data_fields=list(data[0].keys()) if isinstance(data, list) and data and isinstance(data[0], dict) else [])
        
        try:
            # Format the result as a widget
            log_with_props(logger, "info", f"Formatting query result as widget",
                          node=node_name,
                          request_id=request_id,
                          data_length=len(data) if isinstance(data, list) else 0)
            
            # If it should be a table, explicitly set the widget type
            # Data has already been serialized above, so we can use it directly
            if should_be_table:
                # Data is already serialized properly with DateTimeEncoder
                serialized_data = data
                
                # Log the table data being used
                log_with_props(logger, "info", f"Using serialized data for table widget",
                            node=node_name,
                            request_id=request_id,
                            rows=len(serialized_data) if isinstance(serialized_data, list) else 0,
                            columns=list(serialized_data[0].keys()) if isinstance(serialized_data, list) and serialized_data and isinstance(serialized_data[0], dict) else [])
                    
                try:
                    # Attempt to format as table with explicit type
                    formatted_widget = WidgetFormatter.format_response(
                        data=serialized_data,
                        query=state['query'],
                        widget_type="table"
                    )
                    
                    # Log successful table widget creation
                    log_with_props(logger, "info", f"Successfully created table widget",
                                  node=node_name,
                                  request_id=request_id,
                                  widget_type="table",
                                  data_rows=len(serialized_data) if isinstance(serialized_data, list) else 0)
                except Exception as table_error:
                    # Log the error and fall back to auto-detection
                    log_with_props(logger, "error", f"Failed to create table widget: {str(table_error)}",
                                  node=node_name,
                                  request_id=request_id,
                                  error=str(table_error),
                                  exc_info=True)
                    
                    # Fall back to auto-detection
                    formatted_widget = WidgetFormatter.format_response(
                        data=serialized_data,
                        query=state['query']
                    )
            else:
                # Check for numerical data format (list with dictionary containing value and label)
                # This is the pattern created by extract_numerical_data function
                if (isinstance(data, list) and len(data) == 1 and
                    isinstance(data[0], dict) and 'value' in data[0] and 'label' in data[0]):
                    
                    log_with_props(logger, "info", f"Detected numerical data structure from extract_numerical_data",
                                  node=node_name,
                                  request_id=request_id,
                                  data_value=data[0].get('value'),
                                  data_label=data[0].get('label'))
                    
                    # Use just the dictionary, not the list, and specify aggregation widget type
                    formatted_widget = WidgetFormatter.format_response(
                        data=data[0],  # Pass the dictionary item directly, not the list
                        query=state['query'],
                        widget_type="aggregation"  # Explicitly set to aggregation type
                    )
                    
                    # Log the explicitly set widget type
                    log_with_props(logger, "info", f"Using explicitly set aggregation widget type",
                                  node=node_name,
                                  request_id=request_id,
                                  widget_type="aggregation",
                                  data_value=data[0].get('value'),
                                  data_label=data[0].get('label'))
                else:
                    # Otherwise let widget_type be auto-detected
                    formatted_widget = WidgetFormatter.format_response(
                        data=data,
                        query=state['query']
                    )
                    
                    # Log the auto-detected widget type for non-numerical data
                    log_with_props(logger, "info", f"Using auto-detected widget type",
                                  node=node_name,
                                  request_id=request_id,
                                  widget_type=formatted_widget.get('type', 'unknown'),
                                  data_sample=str(data[:1]) if isinstance(data, list) and data else "No data")
            
            # Log widget type for both normal and numerical data cases
            log_with_props(logger, "info", f"Final widget type: {formatted_widget['type']}",
                          node=node_name,
                          request_id=request_id,
                          widget_type=formatted_widget['type'],
                          is_numerical_format=isinstance(data, list) and len(data) == 1 and
                                             isinstance(data[0], dict) and 'value' in data[0] and 'label' in data[0])
            
            # Ensure widget type is preserved in the response
            if formatted_widget['type'] != 'aggregation' and isinstance(data, list) and len(data) == 1 and \
               isinstance(data[0], dict) and 'value' in data[0] and 'label' in data[0]:
                # Force aggregation type if our special format was detected but widget type doesn't match
                log_with_props(logger, "warning", f"Forcing widget type to aggregation for numerical data",
                              node=node_name,
                              request_id=request_id,
                              original_widget_type=formatted_widget['type'])
                
                # Recreate with explicit widget type
                formatted_widget = WidgetFormatter.format_response(
                    data=data[0],  # Pass the dictionary item directly, not the list
                    query=state['query'],
                    widget_type="aggregation"  # Force aggregation type
                )
            
            return {
                **state,
                'final_answer': formatted_widget
            }
            
        except Exception as e:
            # If widget formatting fails, fall back to text and LLM formatting
            log_with_props(logger, "error", f"Widget formatting failed: {str(e)}",
                          node=node_name,
                          request_id=request_id,
                          error=str(e),
                          exc_info=True)
            
            # Create a prompt for the LLM as fallback
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
            data_type_instruction = "This is tabular data. Format it in a clean, readable way for the user using markdown tables."
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
        
            # Log LLM invocation
            log_with_props(logger, "debug", f"Invoking LLM in {node_name}",
                          node=node_name,
                          request_id=request_id,
                          model="gpt-4",
                          prompt_length=len(prompt))
            
            # Measure LLM execution time - Add dedicated error handling for LLM invocation
            try:
                with log_execution_time(logger, "llm_invoke"):
                    response = llm.invoke(prompt)
                
                # Log response info
                log_with_props(logger, "info", f"LLM response received",
                              node=node_name,
                              request_id=request_id,
                              response_length=len(response.content) if response.content else 0)
            except Exception as llm_error:
                # Handle LLM errors gracefully
                error_msg = str(llm_error)
                log_with_props(logger, "error", f"LLM invocation failed in {node_name}",
                              node=node_name,
                              request_id=request_id,
                              error=error_msg,
                              exc_info=True)
                
                # Provide a fallback response with the error details
                fallback_message = f"""Sorry, I encountered an issue while generating a response.
                
                The query was: {state['query']}
                
                Technical details: {error_msg}
                
                Please try again or contact support if this issue persists.
                """
                
                # Create a mock response object with the fallback message
                response = AIMessage(content=fallback_message)
            
            # Format the LLM response as a text widget
            formatted_response = WidgetFormatter.format_response(
                data=response.content,
                query=state['query'],
                widget_type="text"
            )
            
            updated_state = {
                **state,
                'final_answer': formatted_response
            }
            
            # Log node exit
            log_with_props(logger, "info", f"Exiting {node_name}",
                          node=node_name,
                          request_id=request_id)
            return updated_state
    except Exception as e:
        # Log any exceptions
        error_message = str(e)
        log_with_props(logger, "error", f"Error in {node_name}",
                      node=node_name,
                      request_id=request_id,
                      error=error_message,
                      exc_info=True)
        
        # Instead of re-raising, provide a user-friendly error message
        # This ensures the workflow continues and the user gets a response
        error_response = f"""I encountered an error while processing your query:
        
        Query: {state.get('query', 'Unknown query')}
        
        Error details: {error_message}
        
        Please try rephrasing your question or contact support if this issue persists.
        """
        
        # Format the error message as a text widget
        formatted_error = WidgetFormatter.format_response(
            data=error_response,
            query=state.get('query', 'Unknown query'),
            widget_type="text"
        )
        
        # Return a state with the formatted error widget as the final answer
        return {
            **state,
            'final_answer': formatted_error,
            'errors': state.get('errors', []) + [{
                'node': node_name,
                'error': error_message,
                'timestamp': time.time()
            }]
        }

def feedback_node(state: AgentState) -> AgentState:
    """
    Evaluates the quality of final_answer on a scale of 1-10 using an LLM.
    Increments feedback_attempt counter.
    Updates feedback_score and feedback_message in state.
    """
    node_name = "feedback_node"
    request_id = RequestContext.get_request_id()
    attempt = state.get('feedback_attempt', 0) + 1

    log_with_props(logger, "info", f"Entering {node_name}",
                  node=node_name,
                  request_id=request_id,
                  attempt=attempt)

    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        # Extract text from final_answer widget
        final_answer = state.get('final_answer', '')
        if isinstance(final_answer, dict):
            answer_text = (
                final_answer.get('data', '') or
                final_answer.get('fallback', '') or
                str(final_answer)
            )
        else:
            answer_text = str(final_answer)

        prompt = f"""You are a quality evaluator for a data chatbot.

Evaluate the following answer to the user's question on a scale of 1 to 10.

User Question: {state['query']}

Answer Provided: {answer_text}

Scoring Criteria:
- 9-10: Complete, accurate, clear, and directly addresses the question
- 7-8: Mostly complete with minor gaps; still useful
- 5-6: Partially addresses the question; missing key information
- 3-4: Superficial or vague; does not really help the user
- 1-2: Wrong, empty, error response, or no actionable information

Note: If the answer is an error message because the query failed, score based on
whether the error message is clear and actionable for the user (a clear, helpful
error message can still score 6+).

Return ONLY valid JSON, no markdown or extra text:
{{
  "score": <integer 1-10>,
  "reasoning": "<brief explanation of score>",
  "improvement_suggestions": "<specific suggestions for improvement if score < 6, else empty string>"
}}"""

        with log_execution_time(logger, f"{node_name}_llm_invoke"):
            response = llm.invoke(prompt)

        # Parse JSON response
        try:
            evaluation = json.loads(response.content)
            score = int(evaluation.get('score', 5))
            reasoning = evaluation.get('reasoning', '')
            suggestions = evaluation.get('improvement_suggestions', '')
            feedback_message = f"{reasoning} SUGGESTIONS: {suggestions}".strip()
        except (json.JSONDecodeError, ValueError, TypeError) as parse_error:
            log_with_props(logger, "warning", f"Failed to parse LLM feedback JSON in {node_name}",
                          node=node_name,
                          request_id=request_id,
                          error=str(parse_error),
                          raw_response=response.content[:200])
            # Default to neutral score to trigger improvement
            score = 5
            feedback_message = "Unable to parse evaluator response. Triggering improvement."

        log_with_props(logger, "info", f"Feedback evaluation complete",
                      node=node_name,
                      request_id=request_id,
                      score=score,
                      attempt=attempt,
                      reasoning_preview=feedback_message[:100] if feedback_message else "")

        # Log node exit
        log_with_props(logger, "info", f"Exiting {node_name}",
                      node=node_name,
                      request_id=request_id)

        return {
            **state,
            'feedback_score': score,
            'feedback_message': feedback_message,
            'feedback_attempt': attempt,
        }

    except Exception as e:
        log_with_props(logger, "error", f"Error in {node_name}",
                      node=node_name,
                      request_id=request_id,
                      error=str(e),
                      exc_info=True)
        # On unexpected error, pass through with a high score to avoid blocking the user
        return {
            **state,
            'feedback_score': 10,
            'feedback_message': f"Feedback evaluation error (pass-through): {str(e)}",
            'feedback_attempt': attempt,
        }

def improve_answer_node(state: AgentState) -> AgentState:
    """
    Uses LLM feedback critique to generate an improved final_answer.
    Preserves the widget format expected by the frontend.
    """
    node_name = "improve_answer_node"
    request_id = RequestContext.get_request_id()

    log_with_props(logger, "info", f"Entering {node_name}",
                  node=node_name,
                  request_id=request_id,
                  current_score=state.get('feedback_score', 0),
                  attempt=state.get('feedback_attempt', 0))

    try:
        llm = ChatOpenAI(model="gpt-4", temperature=0.3)

        # Extract text from existing final_answer widget
        final_answer = state.get('final_answer', '')
        if isinstance(final_answer, dict):
            original_text = (
                final_answer.get('data', '') or
                final_answer.get('fallback', '') or
                str(final_answer)
            )
            original_widget_type = final_answer.get('type', 'text')
        else:
            original_text = str(final_answer)
            original_widget_type = 'text'

        # Build context about the SQL result
        sql_result_obj = state.get('sql_result', [{}])[-1] if state.get('sql_result') else {}
        sql_context = f"SQL Success: {sql_result_obj.get('success', False)}"
        if sql_result_obj.get('output'):
            sql_context += f"\nSQL Output (first 300 chars): {str(sql_result_obj['output'])[:300]}"
        if sql_result_obj.get('error'):
            sql_context += f"\nSQL Error: {sql_result_obj.get('error')}"

        prompt = f"""You are a data chatbot improvement assistant.

The following answer received a low quality score and needs improvement.

User Question: {state['query']}

Current Answer: {original_text}

Quality Score Given: {state.get('feedback_score', 0)}/10

Evaluator Feedback: {state.get('feedback_message', 'No feedback available')}

Data Context:
{sql_context}

Instructions:
1. Address the specific issues raised in the evaluator feedback
2. Make the answer clear, concise, and directly useful to the user
3. If the original was an error message, explain it more clearly and offer constructive next steps
4. Maintain markdown formatting for readability
5. Return ONLY the improved answer text, no commentary or metadata

Improved Answer:"""

        with log_execution_time(logger, f"{node_name}_llm_invoke"):
            response = llm.invoke(prompt)

        improved_text = response.content.strip()

        log_with_props(logger, "info", f"Answer improvement complete",
                      node=node_name,
                      request_id=request_id,
                      original_length=len(original_text),
                      improved_length=len(improved_text))

        # Re-wrap improved text in a widget format
        improved_widget = WidgetFormatter.format_response(
            data=improved_text,
            query=state['query'],
            widget_type=original_widget_type
        )
        
        # Log node exit
        log_with_props(logger, "info", f"Exiting {node_name}",
                      node=node_name,
                      request_id=request_id)

        return {
            **state,
            'final_answer': improved_widget,
        }

    except Exception as e:
        log_with_props(logger, "error", f"Error in {node_name}",
                      node=node_name,
                      request_id=request_id,
                      error=str(e),
                      exc_info=True)
        # On error, return state unchanged — feedback_node will re-evaluate existing answer
        return state

# Maximum number of feedback improvement attempts before failing
MAX_FEEDBACK_ATTEMPTS = 2

def feedback_router(state: AgentState) -> str:
    """
    Conditional edge function for routing after feedback evaluation.

    Returns:
        'accept'  — score >= 6, answer is good enough → END
        'improve' — score < 6, attempts < MAX_FEEDBACK_ATTEMPTS → improve_answer
        'fail'    — score < 6, attempts >= MAX_FEEDBACK_ATTEMPTS → error_end
    """
    node_name = "feedback_router"
    request_id = RequestContext.get_request_id()

    score = state.get('feedback_score', 0)
    attempts = state.get('feedback_attempt', 0)

    if score >= 6:
        decision = 'accept'
    elif attempts >= MAX_FEEDBACK_ATTEMPTS:
        decision = 'fail'
        # Update the feedback_exceeded flag when max attempts are reached
        state['feedback_exceeded'] = True
    else:
        decision = 'improve'

    log_with_props(logger, "info", f"Feedback routing decision: {decision}",
                  node=node_name,
                  request_id=request_id,
                  score=score,
                  attempts=attempts,
                  max_attempts=MAX_FEEDBACK_ATTEMPTS,
                  decision=decision)

    return decision

# Maximum number of feedback improvement attempts before failing
MAX_FEEDBACK_ATTEMPTS = 2

def feedback_router(state: AgentState) -> str:
    """
    Conditional edge function for routing after feedback evaluation.

    Returns:
        'accept'  — score >= 6, answer is good enough → END
        'improve' — score < 6, attempts < MAX_FEEDBACK_ATTEMPTS → improve_answer
        'fail'    — score < 6, attempts >= MAX_FEEDBACK_ATTEMPTS → error_end
    """
    node_name = "feedback_router"
    request_id = RequestContext.get_request_id()

    score = state.get('feedback_score', 0)
    attempts = state.get('feedback_attempt', 0)

    if score >= 6:
        decision = 'accept'
    elif attempts >= MAX_FEEDBACK_ATTEMPTS:
        decision = 'fail'
        # Update the feedback_exceeded flag when max attempts are reached
        state['feedback_exceeded'] = True
    else:
        decision = 'improve'

    log_with_props(logger, "info", f"Feedback routing decision: {decision}",
                  node=node_name,
                  request_id=request_id,
                  score=score,
                  attempts=attempts,
                  max_attempts=MAX_FEEDBACK_ATTEMPTS,
                  decision=decision)

    return decision

def error_end_node(state: AgentState) -> AgentState:
    """
    Handles persistent low-quality answers after max feedback attempts.
    Logs a structured ERROR and produces a clear, actionable user-facing message.
    """
    node_name = "error_end_node"
    request_id = RequestContext.get_request_id()

    # Log a full diagnostic ERROR for observability
    log_with_props(logger, "error",
                  "Max feedback attempts exceeded — unable to generate satisfactory answer",
                  node=node_name,
                  request_id=request_id,
                  query=state.get('query', ''),
                  final_score=state.get('feedback_score', 0),
                  total_attempts=state.get('feedback_attempt', 0),
                  max_attempts=MAX_FEEDBACK_ATTEMPTS,
                  last_feedback=state.get('feedback_message', '')[:200])

    user_message = f"""I wasn't able to generate a satisfactory answer to your question after {MAX_FEEDBACK_ATTEMPTS} attempts.

**Your question:** {state.get('query', 'Unknown question')}

**What you can try:**
- Rephrase your question with more specific details
- Break complex questions into simpler parts
- Ask about a single metric or entity at a time
- Check if you're asking about data that exists in the system

If this issue persists, please contact your data team for assistance.

*Reference ID: {request_id}*"""

    error_widget = WidgetFormatter.format_response(
        data=user_message,
        query=state.get('query', ''),
        widget_type="text"
    )

    return {
        **state,
        'final_answer': error_widget,
        'feedback_exceeded': True,
        'errors': state.get('errors', []) + [{
            'node': node_name,
            'error': 'Max feedback attempts exceeded without passing quality threshold',
            'final_score': state.get('feedback_score', 0),
            'total_attempts': state.get('feedback_attempt', 0),
            'last_feedback_message': state.get('feedback_message', ''),
            'timestamp': time.time()
        }]
    }

# Build the graph
def create_workflow():
    """Build and return the workflow graph"""
    request_id = RequestContext.get_request_id()
    
    logger.info("Creating LangGraph workflow",
               extra={"props": {"request_id": request_id}})
    
    # Create the state graph
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node('sql_agent', sql_node)
    graph.add_node('validator', validation_node)
    graph.add_node('answer', answer_node)
    graph.add_node('feedback', feedback_node)
    graph.add_node('improve_answer', improve_answer_node)
    graph.add_node('error_end', error_end_node)
    
    logger.debug("Added nodes to workflow graph",
                extra={"props": {"request_id": request_id,
                                "nodes": "sql_agent, validator, answer, feedback, improve_answer, error_end"}})
    
    # Add edges
    graph.set_entry_point('sql_agent')
    graph.add_edge('sql_agent', 'validator')
    graph.add_edge('validator', 'answer')
    graph.add_edge('answer', 'feedback')
    
    # Add conditional edges from feedback based on the feedback_router function
    graph.add_conditional_edges(
        'feedback',
        feedback_router,
        {
            'accept': END,
            'improve': 'improve_answer',
            'fail': 'error_end'
        }
    )
    
    # Add edge from improve_answer back to feedback to create the improvement loop
    graph.add_edge('improve_answer', 'feedback')
    graph.add_edge('error_end', END)
    
    logger.debug("Added edges to workflow graph",
                extra={"props": {"request_id": request_id}})
    
    # Initialize the handler for Langfuse tracing
    langfuse_handler = CallbackHandler()
    
    # Compile and return the graph
    compiled_graph = graph.compile().with_config({"callbacks": [langfuse_handler]})
    
    logger.info("LangGraph workflow created successfully",
               extra={"props": {"request_id": request_id}})
    
    return compiled_graph
