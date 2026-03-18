from langfuse import Langfuse
from langfuse import observe, get_client, propagate_attributes
from langfuse.langchain import CallbackHandler
from opentelemetry import trace
import os
import time
from dotenv import load_dotenv
from observability.logging import get_logger, RequestContext, log_with_props, log_execution_time

# Initialize logger
logger = get_logger(__name__)

load_dotenv()

# Initialize the Langfuse
logger.debug("Initializing Langfuse client")
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_BASE_URL"),
)


@observe(name="DataChat Query")
def trace_agent_run(query: str):
    """
    Wrapper for agent execution with tracing.
    Integrates with Langfuse tracing and structured logging.
    """
    # Get the current request ID from logging context
    request_id = RequestContext.get_request_id()
    user_id = RequestContext.get_user_id() or "12345"
    session_id = RequestContext.get_session_id()
    
    log_with_props(logger, "info", "Starting traced agent execution",
                  query_length=len(query),
                  request_id=request_id,
                  user_id=user_id)
    
    # Import here to avoid circular imports
    from graph.workflow import create_workflow
    
    start_time = time.time()
    try:
        graph = create_workflow()
        
        # Build tags with request context for correlation
        trace_tags = {
            "query_type": "analytics",
            "request_id": request_id,  # Link logs and traces with request_id
        }
        
        if session_id:
            trace_tags["session_id"] = session_id
            
        # 1. Define attributes that propagate to the LangGraph callback
        with propagate_attributes(
            user_id=user_id,
            tags=trace_tags
        ):
            # 2. Add additional metadata via OpenTelemetry attributes
            current_span = trace.get_current_span()
            current_span.set_attribute("request_id", request_id)
            current_span.set_attribute("query_type", "analytics")
            
            # Add any additional context from RequestContext
            for key, value in RequestContext.get_all_context().items():
                if key not in ["request_id", "user_id", "session_id"]:
                    current_span.set_attribute(key, str(value))
            
            # 3. Invoke LangGraph with the handler
            logger.debug("Invoking LangGraph workflow")
            result = graph.invoke({
                'query': query,
                'sql_result': [],
                'validation_result': [],
                'final_answer': '',
                'errors': []
            })
            
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Log successful completion
        log_with_props(logger, "info", "Traced agent execution completed successfully",
                      execution_time_ms=round(execution_time * 1000, 2),
                      result_type=type(result).__name__,
                      has_answer=bool(result.get('final_answer')),
                      request_id=request_id)
        
        # The decorator automatically captures the return value
        # as the trace output. No need for manual update_observation.
        return result
        
    except Exception as e:
        # Calculate execution time even for errors
        execution_time = time.time() - start_time
        
        # Log the error
        log_with_props(logger, "error", "Error in traced agent execution",
                      error=str(e),
                      execution_time_ms=round(execution_time * 1000, 2),
                      request_id=request_id,
                      exc_info=True)
        
        # Re-raise the exception
        raise