from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from langgraph.prebuilt import create_react_agent
from mcp_server import mcp_server
import json
from typing import Dict, Any

class SQLAgent:
    """
    Agent that converts natural language to SQL using LangGraph's create_react_agent
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0  # Deterministic for SQL generation
        )
        self.tools = self._create_tools()
        self.agent_executor = self._create_agent()
    
    def _create_tools(self):
        """Create MCP-based tools for the agent"""
        return [
            Tool(
                name="get_schema",
                func=lambda table: json.dumps(mcp_server.get_schema(table)),
                description="""Get database schema information. 
                Input: table name (string) or empty string for all tables.
                Returns: JSON with table structure including columns and types."""
            ),
            Tool(
                name="execute_sql",
                func=lambda query: json.dumps(mcp_server.execute_query(query)),
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

        # Create the ReAct agent using LangGraph
        agent_executor = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=system_message  # This replaces the system prompt
        )
        
        return agent_executor
    
    def run(self, query: str) -> Dict[str, Any]:
        """
        Execute natural language query
        
        Args:
            query: Natural language question about the database
            
        Returns:
            Dict with 'success' and either 'output' or 'error'
        """
        try:
            # Invoke the agent with the user query
            result = self.agent_executor.invoke({
                "messages": [("user", query)]
            })
            
            # Extract the final answer from the agent's response
            # The result contains all messages including agent's thoughts and final answer
            messages = result.get("messages", [])
            
            # Get the last AI message (the final answer)
            final_answer = None
            for msg in reversed(messages):
                if hasattr(msg, 'content') and msg.type == 'ai':
                    final_answer = msg.content
                    break
            
            return {
                'success': True,
                'output': final_answer or "No answer generated",
                'full_trace': messages  # Useful for debugging
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }