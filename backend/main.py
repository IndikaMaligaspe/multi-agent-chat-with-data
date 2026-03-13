from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from  guardrails_validators import validate_query
from observability.tracing import trace_agent_run
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="DataChat Backend API")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,    
)

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    success: bool
    answer: str = None
    error: str = None
    trace_id: str = None

@app.get("/")
def read_root():
    return {"message": "Welcome to the DataChat Backend API"}   

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/query", response_model=QueryResponse)
def handle_query(request: QueryRequest):
    """ Main endpoint to handle naltural language queries  """
    try:
        # 1. Validate the query using Guardrails
        logger.info(f"Validating query: {request.query}")
        validation_result = validate_query(request.query)
        if not validation_result['valid']:
            raise HTTPException(status_code=400, detail=validation_result['error'])

        validated_query = validation_result['validated_query']

        logger.info(f"Executing query: {validated_query}")
        # 2. Process the query with tracing
        answer = trace_agent_run(validated_query)

        return QueryResponse(
            success=True, 
            answer=answer.get('final_answer', 'No answer generated'),trace_id="check_langfuse")
    except HTTPException as http_exc:
        logger.error(f"HTTP error: {http_exc.detail}",exc_info=True)
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error",exc_info=True)
    
@app.get("/schema")
def get_schema():
    """Get database schema"""
    from mcp_server import mcp_server
    return mcp_server.get_schema()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)