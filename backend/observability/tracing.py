from langfuse import Langfuse
from langfuse import observe, get_client, propagate_attributes
from langfuse.langchain import CallbackHandler
from opentelemetry import trace
import os
from dotenv import load_dotenv

load_dotenv()

#Initialize the Langfuse 
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_BASE_URL"),
)


@observe(name="DatacChat Query")
def trace_agent_run(query: str):
    """Wrapper for agent execution with tracing. """
    from graph.workflow import create_workflow
    graph = create_workflow()

    # 1. Define attributes (user_id, session_id, tags) via context manager
    # These will automatically propagate to the LangGraph callback below
    with propagate_attributes(user_id="12345",
                            tags={"query_type": "analytics"}):
        
        # 2. Add arbitrary metadata via OpenTelemetry attributes
        trace.get_current_span().set_attribute("query_type", "analytics")


        # 3. Invoke LangGraph with the handler
        result = graph.invoke({'query' : query,
                                'sql_result':[],
                                'validation_result': [],
                                'final_answer': '',
                                'errors':[]
                                })
    # The decorator automatically captures the return value 
    # as the trace output. No need for manual update_observation.
    return result