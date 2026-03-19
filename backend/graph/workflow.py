from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List, Dict, Any
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
import operator
import time
from observability.logging import get_logger, log_with_props, log_execution_time, RequestContext

# Initialize logger
logger = get_logger(__name__)

class AgentState(TypedDict):
    """State shared between agents"""
    query: str
    sql_result: Annotated[List[Dict[str, Any]], operator.add] 
    validation_result:Annotated[List[Dict[str, Any]], operator.add] 
    final_answer: str
    errors: Annotated[List[Dict[str, Any]], operator.add] 

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
        
        # Check if the SQL agent already produced a usable answer
        existing_answer = sql_result_obj.get('output')
        
        if existing_answer and isinstance(existing_answer, str) and existing_answer.strip():
            # Log that we're using the existing answer
            log_with_props(logger, "info", f"Using existing answer from SQL agent",
                          node=node_name,
                          request_id=request_id,
                          answer_length=len(existing_answer))
            
            # Return immediately with the existing answer
            return {
                **state,
                'final_answer': existing_answer
            }
            
        # If no existing answer, proceed with generating one
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
            
            # Log the detected data type
            log_with_props(logger, "debug", f"Data type detection in {node_name}",
                          node=node_name,
                          request_id=request_id,
                          is_aggregation=is_aggregation,
                          is_grouped=is_grouped,
                          row_count=len(data) if isinstance(data, list) else 0)
        
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
            from langchain_core.messages import AIMessage
            response = AIMessage(content=fallback_message)
        
        updated_state = {
            **state,
            'final_answer': response.content
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
        
        # Return a state with the error message as the final answer
        return {
            **state,
            'final_answer': error_response,
            'errors': state.get('errors', []) + [{
                'node': node_name,
                'error': error_message,
                'timestamp': time.time()
            }]
        }

def should_continue(state: AgentState) -> str:
    """ Routing logic """
    node_name = "routing"
    request_id = RequestContext.get_request_id()
    
    # Get validation result
    validation = state.get('validation_result', [{}])[-1]
    is_valid = validation.get('is_valid', False)
    
    # Determine next step
    next_step = 'answer' if is_valid else END
    
    # Log routing decision
    log_with_props(logger, "info", f"Routing decision: {next_step}",
                  node=node_name,
                  request_id=request_id,
                  is_valid=is_valid,
                  next_step=next_step)
    
    return next_step

#Build the graph
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
    
    logger.debug("Added nodes to workflow graph",
                extra={"props": {"request_id": request_id, "nodes": "sql_agent, validator, answer"}})
    
    # Add edges
    graph.set_entry_point('sql_agent')
    graph.add_edge('sql_agent', 'validator')
    graph.add_conditional_edges(
        'validator', should_continue, {
            "answer": "answer",
            END: END
        }
    )
    graph.add_edge('answer', END)
    
    logger.debug("Added edges to workflow graph",
                extra={"props": {"request_id": request_id}})
    
    # Initialize the handler for Langfuse tracing
    langfuse_handler = CallbackHandler()
    
    # Compile and return the graph
    compiled_graph = graph.compile().with_config({"callbacks": [langfuse_handler]})
    
    logger.info("LangGraph workflow created successfully",
               extra={"props": {"request_id": request_id}})
    
    return compiled_graph