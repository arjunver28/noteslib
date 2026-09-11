import os
import sys

try:
    import sqlite3
    # Verify that the underlying C extension is functional
    _test_conn = sqlite3.connect(":memory:")
    _test_conn.close()
except (ImportError, ModuleNotFoundError, Exception):
    try:
        import pysqlite3 as sqlite3
        sys.modules['sqlite3'] = sqlite3
    except (ImportError, ModuleNotFoundError):
        print("[INFO] Missing _sqlite3 module. Automatically installing 'pysqlite3-binary'...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pysqlite3-binary"])
            import pysqlite3 as sqlite3
            sys.modules['sqlite3'] = sqlite3
            print("[SUCCESS] 'pysqlite3-binary' installed and activated successfully!")
        except Exception as err:
            raise RuntimeError(
                "\n" + "="*70 + "\n"
                "CRITICAL: Python cannot find '_sqlite3' C-extension.\n"
                "Please run inside your virtualenv on the server:\n"
                "    pip install pysqlite3-binary\n"
                f"Auto-installation failed: {err}\n"
                "="*70 + "\n"
            )

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "notes_library.db"))

def dict_factory(cursor, row):
    """Row factory to return real dictionary rows matching PyMySQL DictCursor behavior."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

class SQLiteCursorProxy:
    """Cursor wrapper that transparently translates MySQL syntax (%s, SET FOREIGN_KEY_CHECKS) to SQLite."""
    def __init__(self, cursor):
        self._cursor = cursor

    def _prepare_sql(self, sql):
        # Convert %s placeholder to ?
        if '%s' in sql:
            sql = sql.replace('%s', '?')
        
        # Convert MySQL SET FOREIGN_KEY_CHECKS to SQLite PRAGMA
        upper = sql.strip().upper()
        if upper.startswith("SET FOREIGN_KEY_CHECKS"):
            if "0" in upper or "OFF" in upper:
                return "PRAGMA foreign_keys = OFF;"
            else:
                return "PRAGMA foreign_keys = ON;"
        return sql

    def execute(self, sql, parameters=()):
        sql = self._prepare_sql(sql)
        return self._cursor.execute(sql, parameters)

    def executemany(self, sql, seq_of_parameters):
        sql = self._prepare_sql(sql)
        return self._cursor.executemany(sql, seq_of_parameters)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchmany(self, size=None):
        return self._cursor.fetchmany(size) if size is not None else self._cursor.fetchmany()

    def close(self):
        return self._cursor.close()

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description


class SQLiteConnectionProxy:
    """Connection wrapper ensuring thread-safety and compatibility with MySQL connection patterns."""
    def __init__(self, conn):
        self._conn = conn

    def cursor(self, *args, **kwargs):
        # Accepts and safely ignores MySQL arguments like cursor(dictionary=True)
        return SQLiteCursorProxy(self._conn.cursor())

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def execute(self, sql, *args, **kwargs):
        cursor = self.cursor()
        return cursor.execute(sql, *args, **kwargs)


def _ensure_db_initialized():
    """Verify tables exist; if database is empty or new, run db_setup automatically."""
    if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
        try:
            from db_setup import setup_database
            setup_database(DB_PATH)
        except Exception as e:
            print(f"[WARN] Auto-initialization of SQLite database: {e}")


def get_db_connection():
    """
    Open an embedded SQLite connection configured for high concurrency:
    - 60 second timeout for lock contention handling across Gunicorn workers
    - Write-Ahead Logging (WAL) enabled
    - Foreign key constraints enabled
    - Real dict rows returned
    """
    _ensure_db_initialized()
    conn = sqlite3.connect(DB_PATH, timeout=60.0, check_same_thread=False)
    conn.row_factory = dict_factory
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return SQLiteConnectionProxy(conn)


def query_db(query, args=(), one=False, commit=False):
    """
    Execute a query and return results or lastrowid.
    Maintains 100% backward compatibility with previous MySQL query_db signature.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

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
