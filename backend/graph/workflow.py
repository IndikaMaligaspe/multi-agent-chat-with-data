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
        
        # Prepare prompt
        sql_result = state['sql_result'][-1] if state.get('sql_result') and len(state['sql_result']) > 0 else {}
        prompt = f"""Based on the following SQL query and result, provide a natural language answer.
        
        Query: {state['query']}
        Results: {sql_result}
        
        Provide a clear, concise answer.
        """
        
        # Log LLM invocation
        log_with_props(logger, "debug", f"Invoking LLM in {node_name}",
                      node=node_name,
                      request_id=request_id,
                      model="gpt-4",
                      prompt_length=len(prompt))
        
        # Measure LLM execution time
        with log_execution_time(logger, "llm_invoke"):
            response = llm.invoke(prompt)
        
        # Log response info
        log_with_props(logger, "info", f"LLM response received",
                      node=node_name,
                      request_id=request_id,
                      response_length=len(response.content) if response.content else 0)
        
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
        log_with_props(logger, "error", f"Error in {node_name}",
                      node=node_name,
                      request_id=request_id,
                      error=str(e),
                      exc_info=True)
        # Re-raise to maintain normal flow
        raise

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