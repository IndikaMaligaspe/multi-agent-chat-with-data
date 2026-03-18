from typing import Any, Dict, Optional
import mysql.connector as _mysql_connector
from mysql.connector import Error
import os
import time
from dotenv import load_dotenv
from observability.logging import get_logger, log_with_props, log_execution_time, RequestContext

# Initialize logger
logger = get_logger(__name__)

load_dotenv()

class ChatWithDataMCPServer:
    """
    A class to handle MySQL database operations for the MCP server.
    """

    def __init__(self):
        """Initialize the MCP server and establish database connection."""
        logger.info("Initializing ChatWithDataMCPServer")
        self.connection = None
        self.connect()

    def connect(self):
        """
        Establish a connection to the MySQL database using credentials from environment variables.
        """
        host = os.getenv('MYSQL_HOST')
        db = os.getenv('MYSQL_DATABASE')
        
        logger.info("Attempting to connect to MySQL database",
                  extra={"props": {"host": host, "database": db}})
        
        start_time = time.time()
        try:
            self.connection = _mysql_connector.connect(
                host=host,
                user=os.getenv('MYSQL_USER'),
                password=os.getenv('MYSQL_PASSWORD'),
                database=db
            )
            
            connection_time = time.time() - start_time
            log_with_props(logger, "info", "Connection to MySQL database established successfully",
                          host=host,
                          database=db,
                          connection_time_ms=round(connection_time * 1000, 2))
        except Error as e:
            connection_time = time.time() - start_time
            log_with_props(logger, "error", "Error connecting to MySQL database",
                          host=host,
                          database=db,
                          error=str(e),
                          connection_time_ms=round(connection_time * 1000, 2))
            self.connection = None
        
    def execute_query(self, query: str) -> Dict[str, Any]:
        """
        MCP Tool: Executes a given SQL query on the connected MySQL database and returns the result.
        Returns: {success:bool, data:list, error:str}
        """
        request_id = RequestContext.get_request_id()
        query_type = query.strip().upper().split()[0] if query.strip() else "UNKNOWN"
        
        # Truncate query for logging to avoid excessive log size
        safe_query = query[:150] + "..." if len(query) > 150 else query
        
        log_with_props(logger, "info", "Executing database query",
                      query_type=query_type,
                      query_preview=safe_query,
                      query_length=len(query),
                      request_id=request_id)

        # Check connection status
        if not self.connection or not self.connection.is_connected():
            log_with_props(logger, "debug", "Database connection not active, reconnecting",
                          request_id=request_id)
            self.connect()
        
        cursor = None
        start_time = time.time()
        try:
            # Create cursor and execute query
            cursor = self.connection.cursor(dictionary=True)
            
            with log_execution_time(logger, "db_query_execution"):
                cursor.execute(query)

            # Handle SELECT vs INSERT/UPDATE/DELETE
            if query_type == "SELECT":
                results = cursor.fetchall()
                row_count = len(results)
                
                execution_time = time.time() - start_time
                log_with_props(logger, "info", "SELECT query executed successfully",
                              query_type=query_type,
                              row_count=row_count,
                              execution_time_ms=round(execution_time * 1000, 2),
                              request_id=request_id)
                
                return {
                    "success": True,
                    "data": results,
                    "row_count": row_count,
                    "error": None
                }
            else:
                self.connection.commit()
                affected_rows = cursor.rowcount
                
                execution_time = time.time() - start_time
                log_with_props(logger, "info", "Non-SELECT query executed successfully",
                              query_type=query_type,
                              affected_rows=affected_rows,
                              execution_time_ms=round(execution_time * 1000, 2),
                              request_id=request_id)
                
                return {
                    "success": True,
                    "affected_rows": affected_rows,
                    "error": None
                }
        except Error as e:
            execution_time = time.time() - start_time
            log_with_props(logger, "error", "Error executing database query",
                          query_type=query_type,
                          error=str(e),
                          query_preview=safe_query,
                          execution_time_ms=round(execution_time * 1000, 2),
                          request_id=request_id)
            
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
        finally:
            if cursor:
                cursor.close()

    def get_schema(self, table_name: str) -> Dict[str, Any]:
        """
        MCP Tool: Retrieves the schema of the connected MySQL database.
        Returns: {success:bool, schema:dict, error:str}
        """
        request_id = RequestContext.get_request_id()
        
        log_with_props(logger, "info", "Retrieving database schema",
                      table=table_name if table_name else "ALL",
                      request_id=request_id)
        
        # Check connection status
        if not self.connection or not self.connection.is_connected():
            log_with_props(logger, "debug", "Database connection not active, reconnecting",
                          request_id=request_id)
            self.connect()
        
        cursor = None
        start_time = time.time()
        try:
            with log_execution_time(logger, "get_schema_execution"):
                if table_name:
                    cursor = self.connection.cursor(dictionary=True)
                    cursor.execute(f"DESCRIBE {table_name}")
                    schema = cursor.fetchall()
                    
                    execution_time = time.time() - start_time
                    log_with_props(logger, "info", "Schema retrieved successfully for table",
                                  table=table_name,
                                  column_count=len(schema),
                                  execution_time_ms=round(execution_time * 1000, 2),
                                  request_id=request_id)
                    
                    return {
                        "success": True,
                        "table": table_name,
                        "schema": schema,
                        "error": None
                    }
                else:
                    cursor = self.connection.cursor(dictionary=True)
                    cursor.execute("SHOW TABLES")
                    tables = [list(row.values())[0] for row in cursor.fetchall()]
                    
                    execution_time = time.time() - start_time
                    log_with_props(logger, "info", "Retrieved list of all tables",
                                  table_count=len(tables),
                                  execution_time_ms=round(execution_time * 1000, 2),
                                  request_id=request_id)
                    
                    return {
                        "success": True,
                        "tables": tables,
                        "error": None
                    }
        except Error as e:
            execution_time = time.time() - start_time
            log_with_props(logger, "error", "Error retrieving database schema",
                          table=table_name if table_name else "ALL",
                          error=str(e),
                          execution_time_ms=round(execution_time * 1000, 2),
                          request_id=request_id)
            
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if cursor:
                cursor.close()

#Singleton instance of the MCP server
mcp_server = ChatWithDataMCPServer()