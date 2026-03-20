from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from langgraph.prebuilt import create_react_agent
from mcp_server import mcp_server
import json
import time
from typing import Dict, Any
from observability.logging import get_logger, log_with_props, log_execution_time, RequestContext

# Initialize logger
logger = get_logger(__name__)

class SQLAgent:
    """
    Agent that converts natural language to SQL using LangGraph's create_react_agent
    """
    
    def __init__(self):
        logger.debug("Initializing SQL Agent")
        
        start_time = time.time()
        try:
            # Initialize LLM
            model_name = "gpt-4o-mini"
            logger.debug(f"Creating LLM instance with model: {model_name}")
            self.llm = ChatOpenAI(
                model=model_name,
                temperature=0  # Deterministic for SQL generation
            )
            
            # Create tools and agent
            self.tools = self._create_tools()
            self.agent_executor = self._create_agent()
            
            initialization_time = time.time() - start_time
            log_with_props(logger, "info", "SQL Agent initialized successfully",
                          model=model_name,
                          initialization_time_ms=round(initialization_time * 1000, 2),
                          tool_count=len(self.tools))
                          
        except Exception as e:
            log_with_props(logger, "error", "Failed to initialize SQL Agent",
                          error=str(e),
                          exc_info=True)
            raise
    
    def _create_tools(self):
        """Create MCP-based tools for the agent"""
        logger.debug("Creating SQL Agent tools")
        
        # Create wrapper functions that include logging
        def get_schema_with_logging(table):
            request_id = RequestContext.get_request_id()
            log_with_props(logger, "info", "Executing get_schema tool",
                          tool="get_schema",
                          table=table,
                          request_id=request_id)
                          
            try:
                with log_execution_time(logger, "get_schema_execution"):
                    result = mcp_server.get_schema(table)
                
                # Log success with metadata
                log_with_props(logger, "info", "get_schema tool executed successfully",
                              tool="get_schema",
                              table=table,
                              success=result.get('success', False),
                              result_size=len(str(result)) if result else 0,
                              request_id=request_id)
                              
                return json.dumps(result)
            except Exception as e:
                # Log failure
                log_with_props(logger, "error", "get_schema tool execution failed",
                              tool="get_schema",
                              table=table,
                              error=str(e),
                              request_id=request_id,
                              exc_info=True)
                raise
        
        def execute_sql_with_logging(query):
            request_id = RequestContext.get_request_id()
            # Log query but be careful not to log sensitive data
            safe_query = query[:100] + "..." if len(query) > 100 else query
            log_with_props(logger, "info", "Executing SQL query",
                          tool="execute_sql",
                          query_preview=safe_query,
                          query_length=len(query),
                          request_id=request_id)
                          
            try:
                with log_execution_time(logger, "execute_sql_execution"):
                    result = mcp_server.execute_query(query)
                
                # Log success or failure
                success = result.get('success', False)
                if success:
                    row_count = len(result.get('data', [])) if 'data' in result else 0
                    log_with_props(logger, "info", "SQL query executed successfully",
                                  tool="execute_sql",
                                  success=success,
                                  row_count=row_count,
                                  query_type=query.strip().upper().split()[0] if query else "UNKNOWN",
                                  request_id=request_id)
                else:
                    log_with_props(logger, "warning", "SQL query execution failed",
                                  tool="execute_sql",
                                  success=success,
                                  error=result.get('error', 'Unknown error'),
                                  request_id=request_id)
                
                return json.dumps(result)
            except Exception as e:
                # Log unexpected errors
                log_with_props(logger, "error", "execute_sql tool execution failed with exception",
                              tool="execute_sql",
                              error=str(e),
                              request_id=request_id,
                              exc_info=True)
                raise
        
        # Create and return tools with logging wrappers
        return [
            Tool(
                name="get_schema",
                func=get_schema_with_logging,
                description="""Get database schema information.
                Input: table name (string) or empty string for all tables.
                Returns: JSON with table structure including columns and types."""
            ),
            Tool(
                name="execute_sql",
                func=execute_sql_with_logging,
                description="""Execute a SQL query against the database.
                Input: A valid SQL SELECT query (string).
                Returns: JSON with success status and query results."""
            )
        ]
    
    def _create_agent(self):
        """
        Create the SQL agent using LangGraph's create_react_agent
        
        create_react_agent is the modern replacement for AgentExecutor
        """
        request_id = RequestContext.get_request_id()
        logger.debug("Creating ReAct agent for SQL execution")
        
        # System message with instructions
        system_message = """You are a SQL expert assistant. Your job is to help users query a database using natural language.

IMPORTANT RULES:
1. ALWAYS call get_schema first to understand the database structure
2. Generate valid SQL SELECT queries based on the schema
3. Use execute_sql to run the query
4. Return results in a clear, natural language format
5. If you need to JOIN tables, check the schema first to understand relationships
6. Use appropriate WHERE clauses, aggregations (COUNT, SUM, AVG), and GROUP BY when needed

Available tables: customers, orders

Be precise and only query for what the user asks."""

        try:
            with log_execution_time(logger, "create_agent_execution"):
                # Create the ReAct agent using LangGraph
                agent_executor = create_react_agent(
                    model=self.llm,
                    tools=self.tools,
                    prompt=system_message  # This replaces the system prompt
                )
            
            log_with_props(logger, "info", "ReAct agent created successfully",
                          agent_type="create_react_agent",
                          tool_count=len(self.tools),
                          request_id=request_id)
            
            return agent_executor
            
        except Exception as e:
            log_with_props(logger, "error", "Failed to create ReAct agent",
                          error=str(e),
                          request_id=request_id,
                          exc_info=True)
            raise
    
    def run(self, query: str) -> Dict[str, Any]:
        """
        Execute natural language query
        
        Args:
            query: Natural language question about the database
            
        Returns:
            Dict with 'success' and either 'output' or 'error'
        """
        request_id = RequestContext.get_request_id()
        
        log_with_props(logger, "info", "Executing natural language query with SQL Agent",
                      query_length=len(query),
                      query_preview=query[:100] + "..." if len(query) > 100 else query,
                      request_id=request_id)
        
        start_time = time.time()
        try:
            # Invoke the agent with the user query
            with log_execution_time(logger, "sql_agent_execution"):
                result = self.agent_executor.invoke({
                    "messages": [("user", query)]
                })
            
            # Log successful agent execution
            log_with_props(logger, "info", "Agent execution complete",
                          execution_time_ms=round((time.time() - start_time) * 1000, 2),
                          request_id=request_id)
            
            # Extract the final answer from the agent's response
            # The result contains all messages including agent's thoughts and final answer
            messages = result.get("messages", [])

            # Get the last AI message (the final answer)
            final_answer = None
            for msg in reversed(messages):
                if hasattr(msg, 'content') and msg.type == 'ai':
                    final_answer = msg.content
                    break
                    
            # Extract raw data from the last execute_sql tool result in the trace
            # This ensures we forward the actual DB rows to answer_node, not just the LLM's text
            raw_db_data = None
            for msg in reversed(messages):
                if getattr(msg, 'type', '') == 'tool':
                    try:
                        tool_content = getattr(msg, 'content', '')
                        parsed_tool = json.loads(tool_content) if isinstance(tool_content, str) else tool_content
                        if isinstance(parsed_tool, dict) and 'data' in parsed_tool:
                            raw_db_data = parsed_tool['data']
                            log_with_props(logger, "info", "Extracted raw DB data from tool result",
                                          request_id=request_id,
                                          row_count=len(raw_db_data) if isinstance(raw_db_data, list) else 0)
                            break
                    except Exception as e:
                        log_with_props(logger, "debug", "Failed to extract data from tool result",
                                      request_id=request_id,
                                      error=str(e))
            
            # Log outcome
            log_with_props(logger, "info", "SQL Agent produced final answer",
                          has_answer=bool(final_answer),
                          answer_length=len(final_answer) if final_answer else 0,
                          message_count=len(messages),
                          request_id=request_id)
            
            return {
                'success': True,
                'output': final_answer or "No answer generated",
                'data': raw_db_data,  # Forward raw DB rows to answer_node
                'full_trace': messages  # Useful for debugging
            }
            
        except Exception as e:
            # Calculate total execution time even for failures
            execution_time = time.time() - start_time
            
            # Log the error
            log_with_props(logger, "error", "SQL Agent execution failed",
                          error=str(e),
                          execution_time_ms=round(execution_time * 1000, 2),
                          query_preview=query[:100] + "..." if len(query) > 100 else query,
                          request_id=request_id,
                          exc_info=True)
            
            return {
                'success': False,
                'error': str(e)
            }