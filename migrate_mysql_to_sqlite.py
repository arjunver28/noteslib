#!/usr/bin/env python3
"""
Migration Utility: MySQL / MariaDB -> SQLite for Notes Library
--------------------------------------------------------------
Transfers all existing academic data, classrooms, admin/superuser credentials,
student records, notes, and view counts from MySQL into the new SQLite database.

Usage:
    python migrate_mysql_to_sqlite.py
    
Optional Environment Variables:
    DB_HOST (default: localhost)
    DB_USER (default: root)
    DB_PASSWORD (default: MySQL@123)
    DB_NAME (default: notes_library)
    DB_PORT (default: 3306)
    DB_PATH (default: notes_library.db)
"""

import os
import sys
import sqlite3

# Try importing PyMySQL or mysql.connector for reading from MySQL
mysql_driver = None
try:
    import pymysql
    from pymysql.cursors import DictCursor
    mysql_driver = "pymysql"
except ImportError:
    try:
        import mysql.connector
        mysql_driver = "mysql.connector"
    except ImportError:
        print("[ERROR] Neither 'pymysql' nor 'mysql.connector' is installed.")
        print("To migrate data from MySQL, temporarily install pymysql:")
        print("    pip install pymysql")
        sys.exit(1)

# Configuration
MYSQL_HOST = os.environ.get("DB_HOST", "localhost")
MYSQL_USER = os.environ.get("DB_USER", "root")
MYSQL_PASSWORD = os.environ.get("DB_PASSWORD", "MySQL@123")
MYSQL_DB = os.environ.get("DB_NAME", "notes_library")
MYSQL_PORT = int(os.environ.get("DB_PORT", 3306))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "notes_library.db"))

TABLES_IN_ORDER = [
    "configured_courses",
    "configured_branches",
    "classrooms",
    "superusers",
    "admins",
    "students",
    "notes",
    "classroom_subjects",
    "student_favourites",
    "note_views"
]

def get_mysql_conn():
    if mysql_driver == "pymysql":
        return pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            port=MYSQL_PORT,
            charset="utf8mb4",
            cursorclass=DictCursor
        )
    else:
        return mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            port=MYSQL_PORT
        )

def migrate():
    print("=================================================================")
    print("  Notes Library: MySQL to SQLite Data Migration Tool")
    print("=================================================================")
    print(f"Source (MySQL):  {MYSQL_USER}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}")
    print(f"Target (SQLite): {SQLITE_PATH}")
    print("-----------------------------------------------------------------")

    # 1. Connect to MySQL
    try:
        mysql_conn = get_mysql_conn()
        print("[INFO] Connected to source MySQL database successfully.")
    except Exception as e:
        print(f"[ERROR] Could not connect to MySQL database: {e}")
        print("Please check your MySQL service and credentials.")
        sys.exit(1)

    # 2. Ensure SQLite database and tables exist
    from db_setup import setup_database
    setup_database(SQLITE_PATH)

    sqlite_conn = sqlite3.connect(SQLITE_PATH, timeout=60.0)
    sqlite_conn.execute("PRAGMA foreign_keys = OFF;") # Temporarily off during batch import
    sqlite_cursor = sqlite_conn.cursor()

    total_records = 0

    try:
        if mysql_driver == "pymysql":
            mysql_cursor = mysql_conn.cursor()
        else:
            mysql_cursor = mysql_conn.cursor(dictionary=True)

        for table in TABLES_IN_ORDER:
            try:
                mysql_cursor.execute(f"SELECT * FROM `{table}`")
                rows = mysql_cursor.fetchall()
            except Exception as e:
                print(f"[WARN] Could not read table '{table}' from MySQL: {e}")
                continue

            if not rows:
                print(f"[-] Table '{table}': 0 rows found in MySQL. Skipping.")
                continue

            # Detect columns from first row
            columns = list(rows[0].keys())
            placeholders = ", ".join(["?"] * len(columns))
            col_names = ", ".join([f'"{c}"' for c in columns])
            insert_sql = f'INSERT OR REPLACE INTO "{table}" ({col_names}) VALUES ({placeholders})'

            data = [[row[col] for col in columns] for row in rows]
            sqlite_cursor.executemany(insert_sql, data)
            sqlite_conn.commit()

            print(f"[+] Table '{table}': successfully migrated {len(rows)} records.")
            total_records += len(rows)

        # Re-enable foreign keys
        sqlite_conn.execute("PRAGMA foreign_keys = ON;")
        sqlite_conn.commit()

        print("-----------------------------------------------------------------")
        print(f"[SUCCESS] Migration completed! Total {total_records} records copied to SQLite.")
        print(f"Your database is ready at: {SQLITE_PATH}")
        print("You can now safely stop your MySQL/MariaDB service.")
        print("=================================================================")

    except Exception as e:
        sqlite_conn.rollback()
        print(f"[ERROR] Migration failed: {e}")
        sys.exit(1)
    finally:
        mysql_conn.close()
        sqlite_conn.close()

if __name__ == "__main__":
    migrate()
