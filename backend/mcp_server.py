from typing import Any, Dict
import mysql.connector as _mysql_connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

class ChatWithDataMCPServer:
    """
    A class to handle MySQL database operations for the MCP server.
    """

    def __init__(self):
        self.connection = None  
        self.connect()

    def connect(self):
        """
        Establish a connection to the MySQL database using credentials from environment variables.
        """
        try:
            self.connection = _mysql_connector.connect(
                host=os.getenv('MYSQL_HOST'),
                user=os.getenv('MYSQL_USER'),
                password=os.getenv('MYSQL_PASSWORD'),
                database=os.getenv('MYSQL_DATABASE')
            )
            print("Connection to MySQL database established successfully.")
        except Error as e:
            print(f"Error connecting to MySQL database: {e}")
            self.connection = None
        
    def execute_query(self, query: str) -> Any:
        """
        MCP Tool: Executes a given SQL query on the connected MySQL database and returns the result.
        Returns: {success:bool, data:list, error:str}
        """

        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query)

            #Handle SELECT vs INSRTE/UPDTAE/DELETE
            if query.strip().upper().startswith("SELECT"):
                results = cursor.fetchall()
                return {
                    "success": True,
                    "data": results,
                    "row_count": len(results),
                    "error": None   
                }
            else:   
                self.connection.commit()
                return {
                    "success": True,
                    "effected_rows": cursor.rowcount,
                    "error": None   
                }            
        except Error as e:
            print(f"Error executing query: {e}")
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
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        try:
            if table_name:
                cursor = self.connection.cursor(dictionary=True)
                cursor.execute(f"DESCRIBE {table_name}")
                schema = cursor.fetchall()
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
                return {
                    "success": True,
                    "tables": tables,
                    "error": None
                }
        except Error as e:
            print(f"Error retrieving schema: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if cursor:
                cursor.close()

#Singleton instance of the MCP server
mcp_server = ChatWithDataMCPServer()