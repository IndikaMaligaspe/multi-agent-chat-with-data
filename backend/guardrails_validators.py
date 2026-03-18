"""
Custom validators using guardrails-ai

This module provides validation functions to ensure queries are safe and well-formed.
It includes SQL injection prevention and input validation.
"""
from pydantic import BaseModel, Field, validator
import re
import time
from typing import Optional, Dict, Any
from observability.logging import get_logger, log_with_props, RequestContext

# Initialize logger
logger = get_logger(__name__)

class QueryRequest(BaseModel):
    """Validated query request with SQL injection prevention"""
    query: str = Field(..., description="User's natural language query")
    max_results: int = Field(default=100, le=1000, description="Maximum results")
    
    @validator('query')
    def prevent_sql_injection(cls, v):
        """
        Prevent SQL injection attempts by checking for dangerous patterns.
        Logs any detected injection attempts as security warnings.
        """
        request_id = RequestContext.get_request_id()
        
        # Check for empty queries
        if not v or not v.strip():
            log_with_props(logger, "warning", "Empty query validation failure",
                          validation_type="empty_check",
                          request_id=request_id)
            raise ValueError("Query cannot be empty")
        
        # Log that we're starting injection validation
        log_with_props(logger, "debug", "Performing SQL injection validation",
                      query_length=len(v),
                      request_id=request_id)
        
        # List of dangerous patterns
        dangerous_patterns = [
            (r';\s*DROP', 'DROP statement'),
            (r';\s*DELETE\s+FROM', 'DELETE statement'),
            (r';\s*UPDATE.*SET', 'UPDATE statement'),
            (r';\s*INSERT\s+INTO', 'INSERT statement'),
            (r'UNION\s+SELECT', 'UNION injection'),
            (r'--', 'SQL comment'),
            (r'/\*.*\*/', 'Multi-line comment'),
            (r';\s*TRUNCATE', 'TRUNCATE statement'),
            (r';\s*ALTER', 'ALTER statement'),
            (r';\s*CREATE', 'CREATE statement'),
            (r'xp_cmdshell', 'Command execution'),
        ]
        
        # Check each pattern
        for pattern, description in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                # Log potential SQL injection as a security warning
                log_with_props(logger, "warning", "Potential SQL injection detected",
                              validation_type="sql_injection",
                              pattern=description,
                              query_preview=v[:50] + "..." if len(v) > 50 else v,
                              request_id=request_id)
                
                raise ValueError(
                    f"Potential SQL injection detected: {description}. "
                    f"Please rephrase your question."
                )
        
        # Log successful validation
        log_with_props(logger, "debug", "SQL injection validation passed",
                      request_id=request_id)
        
        return v.strip()

def validate_query(query: str, max_results: int = 100) -> Dict[str, Any]:
    """
    Validate incoming query using Pydantic
    
    Args:
        query: Natural language query from user
        max_results: Maximum number of results to return
        
    Returns:
        dict with 'valid' boolean and either 'validated_query' or 'error'
    """
    request_id = RequestContext.get_request_id()
    
    # Log validation attempt
    log_with_props(logger, "info", "Validating query",
                  query_preview=query[:50] + "..." if len(query) > 50 else query,
                  query_length=len(query),
                  max_results=max_results,
                  request_id=request_id)
    
    start_time = time.time()
    try:
        # Validate using Pydantic model
        validated = QueryRequest(query=query, max_results=max_results)
        
        # Calculate and log validation time
        validation_time = time.time() - start_time
        
        # Log successful validation
        log_with_props(logger, "info", "Query validation successful",
                      validation_time_ms=round(validation_time * 1000, 2),
                      query_length=len(validated.query),
                      max_results=validated.max_results,
                      request_id=request_id)
        
        return {
            'valid': True,
            'validated_query': validated.query,
            'max_results': validated.max_results
        }
    except Exception as e:
        # Calculate validation time even for failures
        validation_time = time.time() - start_time
        
        # Log validation failure
        log_with_props(logger, "warning", "Query validation failed",
                      validation_time_ms=round(validation_time * 1000, 2),
                      error=str(e),
                      request_id=request_id)
        
        return {
            'valid': False,
            'error': str(e)
        }

# Alternative: Simple function-based validator without Pydantic
def simple_validate_query(query: str) -> Dict[str, Any]:
    """
    Lightweight query validator without Pydantic
    Use this if you want minimal dependencies
    """
    request_id = RequestContext.get_request_id()
    
    # Log validation attempt
    log_with_props(logger, "info", "Performing simple query validation",
                  query_preview=query[:50] + "..." if len(query) > 50 else query,
                  query_length=len(query),
                  validator="simple",
                  request_id=request_id)
    
    start_time = time.time()
    
    # Check for empty queries
    if not query or not query.strip():
        validation_time = time.time() - start_time
        
        log_with_props(logger, "warning", "Empty query validation failure",
                      validation_time_ms=round(validation_time * 1000, 2),
                      validator="simple",
                      request_id=request_id)
        
        return {
            'valid': False,
            'error': 'Query cannot be empty'
        }
    
    # Check for SQL injection patterns
    dangerous_keywords = [
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE',
        'EXEC', 'EXECUTE', 'xp_', 'sp_'
    ]
    
    query_upper = query.upper()
    
    for keyword in dangerous_keywords:
        if f';{keyword}' in query_upper or f'; {keyword}' in query_upper:
            validation_time = time.time() - start_time
            
            # Log potential SQL injection
            log_with_props(logger, "warning", "SQL injection detected in simple validator",
                          validation_time_ms=round(validation_time * 1000, 2),
                          keyword=keyword,
                          query_preview=query[:50] + "..." if len(query) > 50 else query,
                          validator="simple",
                          request_id=request_id)
            
            return {
                'valid': False,
                'error': f'Potentially dangerous SQL keyword detected: {keyword}'
            }
    
    # Log successful validation
    validation_time = time.time() - start_time
    log_with_props(logger, "info", "Simple query validation succeeded",
                  validation_time_ms=round(validation_time * 1000, 2),
                  validator="simple",
                  request_id=request_id)
    
    return {
        'valid': True,
        'validated_query': query.strip()
    }