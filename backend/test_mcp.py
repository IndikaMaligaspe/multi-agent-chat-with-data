from mcp_server import mcp_server

#Test 1: Get Schema
print(" Testing get_schema for all tables ")
result = mcp_server.get_schema(None)
print(result)   

#Test 2: Get Schema for Specific Table
print(" Testing get_schema for specific table ")
result = mcp_server.get_schema("customers")
print(result)   

#Test 3: Execute Query
print(" Testing execute_query ")
result = mcp_server.execute_query("SELECT * FROM customers LIMIT 3")
print(result)   

