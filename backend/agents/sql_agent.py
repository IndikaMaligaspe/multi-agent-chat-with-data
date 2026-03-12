from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_agent
from langchain.tools import Tool
from mcp_server import mcp_server
import json

class SQLAgent:
    """
    Agent that interacts with a MySQL database using the MCP server.
    """

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4", temperature=0)
        self.agent = self._create_agent()
        self.tools = self.__create_tools()

    def _create_tools(self):
        """ Create tools for the agent to interact with the MCP server. """
        return[
            Tool(
                name="get_schema",
                func=lambda table: json.dumps(mcp_server.get_schema(table)),
                description="Get database schema. Input: Table name of empty for all tables."
            ),
            Tool(
                name="execute_sql",
                func=lambda query: json.dumps(mcp_server.execute_query(query)),
                description="Execute a SQL query. Input: SQL query string."
            )
        ]
    
    def _create_agent(self):
        """ Create the agent with the defined tools and prompt template. """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an SQL expert. Converts natural language to SQL queries and interacts with a MySQL database using the provided tools.
             Rules:
            1. ALWAYS get schema first using get_schema tool
            2. Generate valid SQL based on the schema
            3. Execute using execute_sql tool
            4. Return results in a user-friendly format
            
            Available tables: customers, orders
            """),
            ("human", "{input}")
            ("placeholder", "{agent_scratchpad}")
        ])
        
        agent  = create_agent(self.tools, self.llm, prompt)

        return AgentExecutor(agent=agent, tools=self.tools, verbose=True)
    
    def run(self, query: str) -> str:
        """ Execute natural language query. """
        try:
            result = self.agent.invoke({"input": query})
            return {
                'success': True,
                'output': result['output'],
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        