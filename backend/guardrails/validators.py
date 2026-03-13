from guardrails import Guard, Validator, register_validator
from pydantic import BaseModel, Field
import re

@register_validator(name="sql_injection", data_type="string")
class SQLInjectionValidator(Validator):
    """
    A simple validator to check for potential SQL injection patterns in a string.
    This is a basic implementation and can be enhanced with more sophisticated checks.
    """

    def validate(self, value, metadata):
        # Basic regex pattern to detect common SQL injection attempts
        dangerous_patterns = [
            r";\s*DROP",
            r";\s*DELETE",
            r";\s*UPDATE.*WHERE\s+1=1",
            r"UNION\s+SELECT",
            r"--",
            r"/\*.*\*/"
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return ValueError(f"Potential SQL injection detected in input: {pattern}")
        
        return value
    
class QueryRequest(BaseModel):
    """ Validated query request"""
    query: str = Field(..., description="User's natural language query")
    max_results: int = Field(default=100, le=1000, description="Maximum number of results to return")

# Create Guard
guard = Guard.for_pydantic(
    output_class=QueryRequest,
    Validators= [SQLInjectionValidator()]
)

def validate_query(query: str) -> dict:
    """ Validate incoming query"""
    try:
        result  = Guard.parse(
            llm_output=f'{{query: "{query}", max_results: 100}}'
        )

        return {
            'valid': True,
            'validated_query': result.validated_output,
        }
    except Exception as e:
        return {
            'valid': False,
            'error': str(e)
        }   

