import os
import sys

# Read database connection parameters from environment with local defaults
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "MySQL@123"),
    "database": os.environ.get("DB_NAME", "notes_library"),
    "port": int(os.environ.get("DB_PORT", 3306))
}

DRIVER = None
connection_pool = None
DictCursor = None

# 1. Try PyMySQL first (100% Pure Python, zero glibc/C-dependencies, ideal for ClearOS 7 / CentOS 7)
try:
    import pymysql
    from pymysql.cursors import DictCursor as PyMySQLDictCursor
    DRIVER = "pymysql"
    DictCursor = PyMySQLDictCursor
    
    # Try connection pooling via DBUtils if available
    try:
        from dbutils.pooled_db import PooledDB
        connection_pool = PooledDB(
            creator=pymysql,
            mincached=2,
            maxcached=10,
            maxconnections=20,
            blocking=True,
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
            port=DB_CONFIG["port"],
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=False
        )
    except Exception as e:
        # Fallback to direct connections if DBUtils pool is not installed
        connection_pool = None
except ImportError:
    # 2. Fallback to mysql.connector if PyMySQL is not installed
    try:
        import mysql.connector
        from mysql.connector import pooling
        DRIVER = "mysql.connector"
        try:
            connection_pool = pooling.MySQLConnectionPool(
                pool_name="notes_lib_pool",
                pool_size=10,
                **DB_CONFIG
            )
        except Exception as e:
            print(f"Warning: Error creating mysql.connector connection pool: {e}")
            connection_pool = None
    except ImportError:
        print("CRITICAL: Neither 'pymysql' nor 'mysql.connector' is installed.")
        print("Please install PyMySQL (recommended): pip install pymysql")

def get_db_connection():
    """
    Get a database connection from the pool or create a direct connection.
    Supports both PyMySQL and mysql.connector.
    """
    if DRIVER == "pymysql":
        if connection_pool:
            return connection_pool.connection()
        import pymysql
        return pymysql.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
            port=DB_CONFIG["port"],
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=False
        )
    elif DRIVER == "mysql.connector":
        import mysql.connector
        if connection_pool:
            return connection_pool.get_connection()
        return mysql.connector.connect(**DB_CONFIG)
    else:
        raise RuntimeError("No MySQL database driver available. Please install PyMySQL: pip install pymysql")

def query_db(query, args=(), one=False, commit=False):
    """
    Execute a query and return results or lastrowid.
    Standardized across both PyMySQL and mysql.connector.
    """
    conn = get_db_connection()
    if DRIVER == "pymysql":
        cursor = conn.cursor(DictCursor)
    else:
        cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(query, args)
        if commit:
            conn.commit()
            last_id = cursor.lastrowid
            cursor.close()
            conn.close()
            return last_id
        else:
            rv = cursor.fetchall()
            cursor.close()
            conn.close()
            return (rv[0] if rv else None) if one else rv
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        cursor.close()
        conn.close()
        raise e
