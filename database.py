import psycopg2
from psycopg2 import pool
from flask import current_app
import logging
from typing import Optional
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a connection pool
connection_pool: Optional[pool.SimpleConnectionPool] = None

def init_db(app) -> None:
    """
    Initialize the database connection pool.
    
    Args:
        app: Flask application instance
        
    Raises:
        Exception: If connection pool initialization fails
    """
    global connection_pool
    
    if connection_pool is not None:
        logger.info("Connection pool already initialized")
        return
        
    try:
        logger.info("Initializing connection pool...")
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=app.config['DB_HOST'],
            database=app.config['DB_NAME'],
            user=app.config['DB_USER'],
            password=app.config['DB_PASSWORD']
        )
        logger.info("Connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Error creating connection pool: {str(e)}")
        raise

@contextmanager
def get_db_connection():
    """
    Context manager for database connections.
    
    Yields:
        psycopg2.connection: Database connection
        
    Raises:
        Exception: If connection pool is not initialized or connection fails
    """
    if connection_pool is None:
        raise Exception("Database connection pool not initialized")
        
    conn = None
    try:
        conn = connection_pool.getconn()
        logger.debug("Got connection from pool")
        yield conn
    except Exception as e:
        logger.error(f"Error getting connection from pool: {str(e)}")
        raise
    finally:
        if conn is not None:
            connection_pool.putconn(conn)
            logger.debug("Connection returned to pool")

def close_db_connection(conn) -> None:
    """
    Return a connection to the pool.
    
    Args:
        conn: Database connection to return
    """
    if connection_pool is not None and conn is not None:
        connection_pool.putconn(conn)
        logger.debug("Connection returned to pool")

def execute_query(query: str, params: tuple = None) -> list:
    """
    Execute a database query and return results.
    
    Args:
        query (str): SQL query to execute
        params (tuple, optional): Query parameters
        
    Returns:
        list: Query results
        
    Raises:
        Exception: If query execution fails
    """
    with get_db_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                if cur.description:
                    return cur.fetchall()
                return []
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            raise 