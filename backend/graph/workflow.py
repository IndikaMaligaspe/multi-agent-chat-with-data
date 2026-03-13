from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
import operator

class AgentState(TypedDict):
    """State shared between agents"""
    query: str
    sql_result: Annotated[dict, operator.add]
    validation_result: Annotated[dict, operator.add]
    final_answer: str
    errors: Annotated[list, operator.add]

def sql_node(state:AgentState) -> AgentState:
    """SQL Agent Node"""
    # Here you would call your SQL agent to execute the query and get results
    from agents.sql_agent import SQLAgent

    agent = SQLAgent()
    result = agent.run(state['query'])
    return {
        **state,
        'sql_result': result,
    }

def validation_node(state:AgentState) -> AgentState:
    """Validation Agent Node"""
    # Here you would call your validation agent to validate the SQL results

    sql_result = state['sql_result'][-1] if state.get('sql_result') else {}

    #simple validation
    is_valid = sql_result.get('success', False)

    validation = {
        'is_valid': is_valid,
        'message': 'Query execution successful' if is_valid else 'Validation failed'
    }

    return {
        **state,
        'validation_result': [validation],
    }

def answer_node(state:AgentState) -> AgentState:
    """ Final Answer Genertaion Node """
    llm = ChatOpenAI(model="gpt-4", temperature=0.3)

    sql_result = state['sql_result'][-1] if state.get('sql_result') else {}
    propmpt = f"""Based on the following SQL query and result,  provide a natural language answer. 
    
    Query: {state['query']}
    Results: {sql_result}
    
    Provide a clear, concise answer.
    """

    response = llm.invoke(propmpt)

    return {
        **state,
        'final_answer': response.content
    }

def should_continue(state:AgentState) -> str:
    """ Routing logic """
    validation = state.get('validation_result', [{}])[-1]
    if validation.get('is_valid'):
        return 'answer_node'
    else:
        return END
    

#Build the graph
def create_workflow():
    graph = StateGraph(AgentState)

    graph.add_node('sql_agent', sql_node)
    graph.add_node('validator', validation_node)
    graph.add_node('answer', answer_node)

    #Add edges
    graph.set_entry_point('sql_agent')
    graph.add_edge('sql_agent', 'validator')
    graph.add_conditional_edges(
        'validator', should_continue, {
            "answer": "answer",
            END:END
        }
    )
    graph.add_edge('answer', END)
    
    # Initialize the handler
    langfuse_handler = CallbackHandler()

    return graph.compile().with_config({"callbacks": [langfuse_handler]})