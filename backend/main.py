from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time
from guardrails_validators import validate_query
from observability.tracing import trace_agent_run
from observability.logging import get_logger, RequestContext, log_with_props, log_execution_time
from middleware.logging_middleware import LoggingMiddleware

# Setup Logging with our centralized configuration
logger = get_logger(__name__)

app = FastAPI(title="DataChat Backend API")

# Add middleware (order matters - logging middleware should be first to catch all requests)
app.add_middleware(LoggingMiddleware)
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
    logger.debug("Root endpoint accessed")
    return {"message": "Welcome to the DataChat Backend API"}

@app.get("/health")
def health_check():
    logger.debug("Health check endpoint accessed")
    return {"status": "healthy"}

@app.post("/query", response_model=QueryResponse)
def handle_query(request: QueryRequest):
    """ Main endpoint to handle natural language queries """
    request_id = RequestContext.get_request_id()
    
    try:
        # 1. Validate the query using Guardrails
        log_with_props(logger, "info", "Validating query",
                      query=request.query,
                      request_id=request_id)
        
        validation_result = validate_query(request.query)
        
        if not validation_result['valid']:
            log_with_props(logger, "warning", "Query validation failed",
                          error=validation_result['error'],
                          query=request.query)
            raise HTTPException(status_code=400, detail=validation_result['error'])

        validated_query = validation_result['validated_query']
        
        # 2. Process the query with tracing
        log_with_props(logger, "info", "Executing validated query",
                      validated_query=validated_query)
        
        # Execute with timing measurement
        with log_execution_time(logger, "query_processing"):
            answer = trace_agent_run(validated_query)
        
        # 3. Build and return the response
        final_answer = answer.get('final_answer', 'No answer generated')
        log_with_props(logger, "info", "Query successfully processed",
                      answer_length=len(final_answer) if final_answer else 0)
        
        return QueryResponse(
            success=True,
            answer=final_answer,
            trace_id=request_id  # Include request_id as trace_id for correlation
        )
    except HTTPException as http_exc:
        log_with_props(logger, "error", "HTTP error processing query",
                      status_code=http_exc.status_code,
                      detail=http_exc.detail,
                      query=request.query)
        raise http_exc
    except Exception as e:
        log_with_props(logger, "error", "Unexpected error processing query",
                      error=str(e),
                      query=request.query,
                      exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@app.get("/schema")
def get_schema():
    """Get database schema"""
    logger.debug("Database schema requested")
    try:
        from mcp_server import mcp_server
        schema = mcp_server.get_schema()
        log_with_props(logger, "info", "Schema retrieved successfully",
                      schema_size=len(str(schema)) if schema else 0)
        return schema
    except Exception as e:
        log_with_props(logger, "error", "Error retrieving database schema",
                      error=str(e),
                      exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving database schema")

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to response for performance monitoring"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

if __name__ == "__main__":
    import time
    import uvicorn
    logger.info("Starting DataChat Backend API",
               extra={"props": {"host": "0.0.0.0", "port": 8000}})
    uvicorn.run(app, host="0.0.0.0", port=8000)