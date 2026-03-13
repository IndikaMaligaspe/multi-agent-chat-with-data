"""
Custom validators using guardrails-ai
"""
from pydantic import BaseModel, Field, validator
import re
from typing import Optional

class QueryRequest(BaseModel):
    """Validated query request with SQL injection prevention"""
    query: str = Field(..., description="User's natural language query")
    max_results: int = Field(default=100, le=1000, description="Maximum results")
    
    @validator('query')
    def prevent_sql_injection(cls, v):
        """Prevent SQL injection attempts"""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        
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
        
        for pattern, description in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(
                    f"Potential SQL injection detected: {description}. "
                    f"Please rephrase your question."
                )
        
        return v.strip()

def validate_query(query: str, max_results: int = 100) -> dict:
    """
    Validate incoming query using Pydantic
    
    Args:
        query: Natural language query from user
        max_results: Maximum number of results to return
        
    Returns:
        dict with 'valid' boolean and either 'validated_query' or 'error'
    """
    try:
        validated = QueryRequest(query=query, max_results=max_results)
        return {
            'valid': True,
            'validated_query': validated.query,
            'max_results': validated.max_results
        }
    except Exception as e:
        return {
            'valid': False,
            'error': str(e)
        }

# Alternative: Simple function-based validator without Pydantic
def simple_validate_query(query: str) -> dict:
    """
    Lightweight query validator without Pydantic
    Use this if you want minimal dependencies
    """
    if not query or not query.strip():
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
            return {
                'valid': False,
                'error': f'Potentially dangerous SQL keyword detected: {keyword}'
            }
    
    return {
        'valid': True,
        'validated_query': query.strip()
    }