import os
import sys
from werkzeug.security import generate_password_hash as _werkzeug_generate_password_hash

def generate_password_hash(password, method='pbkdf2:sha256'):
    """Safe password hash generator using pbkdf2:sha256 for OpenSSL 1.0.2k / ClearOS 7 compatibility."""
    return _werkzeug_generate_password_hash(password, method=method)

# Read database credentials from environment with defaults
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "MySQL@123")
DB_NAME = os.environ.get("DB_NAME", "notes_library")
DB_PORT = int(os.environ.get("DB_PORT", 3306))

DRIVER = None
try:
    import pymysql
    DRIVER = "pymysql"
except ImportError:
    try:
        import mysql.connector
        DRIVER = "mysql.connector"
    except ImportError:
        print("CRITICAL: Neither 'pymysql' nor 'mysql.connector' is installed.")
        print("Please install PyMySQL: pip install pymysql")
        sys.exit(1)

def get_connection(include_db=True):
    if DRIVER == "pymysql":
        return pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            database=DB_NAME if include_db else None,
            charset="utf8mb4",
            autocommit=True
        )
    else:
        return mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            database=DB_NAME if include_db else None
        )

def setup_database():
    print("Connecting to MySQL server...")
    try:
        conn = get_connection(include_db=False)
        cursor = conn.cursor()
        
        # Create database
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        print(f"Database '{DB_NAME}' verified/created.")
        conn.close()
    except Exception as e:
        print(f"Error creating database: {e}")
        sys.exit(1)

    try:
        conn = get_connection(include_db=True)
        cursor = conn.cursor()

        # Disable foreign key checks for table creation/reset
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

        # 1. Classrooms Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classrooms (
                id INT AUTO_INCREMENT PRIMARY KEY,
                course VARCHAR(100) NOT NULL,
                branch VARCHAR(100) NOT NULL,
                semester INT NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                UNIQUE KEY unique_classroom (course, branch, semester)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("Table 'classrooms' verified/created.")

        # 2. Superusers Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS superusers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("Table 'superusers' verified/created.")

        # 3. Admins Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                admin_name VARCHAR(150) NOT NULL,
                classroom_id INT NOT NULL,
                FOREIGN KEY (classroom_id) REFERENCES classrooms (id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("Table 'admins' verified/created.")

        # 4. Students Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                roll_number VARCHAR(100) PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                contact VARCHAR(20) NOT NULL,
                classroom_id INT NOT NULL,
                year INT NULL,
                password_hash VARCHAR(255) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                FOREIGN KEY (classroom_id) REFERENCES classrooms (id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("Table 'students' verified/created.")

        # 5. Notes Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                subject VARCHAR(150) NOT NULL,
                unit VARCHAR(50) NOT NULL,
                topic VARCHAR(150) NULL,
                file_path VARCHAR(255) NOT NULL,
                classroom_id INT NOT NULL,
                credit_roll VARCHAR(100) NOT NULL,
                credit_name VARCHAR(150) NOT NULL,
                uploaded_by_admin INT NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (classroom_id) REFERENCES classrooms (id) ON DELETE CASCADE,
                FOREIGN KEY (uploaded_by_admin) REFERENCES admins (id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("Table 'notes' verified/created.")

        # 6. Configured Courses Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configured_courses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                course_name VARCHAR(100) NOT NULL UNIQUE,
                total_semesters INT NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("Table 'configured_courses' verified/created.")

        # 7. Configured Branches Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configured_branches (
                id INT AUTO_INCREMENT PRIMARY KEY,
                course_id INT NOT NULL,
                branch_name VARCHAR(100) NOT NULL,
                FOREIGN KEY (course_id) REFERENCES configured_courses (id) ON DELETE CASCADE,
                UNIQUE KEY unique_branch (course_id, branch_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("Table 'configured_branches' verified/created.")

        # 8. Classroom Subjects Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classroom_subjects (
                id INT AUTO_INCREMENT PRIMARY KEY,
                classroom_id INT NOT NULL,
                subject_name VARCHAR(150) NOT NULL,
                FOREIGN KEY (classroom_id) REFERENCES classrooms (id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("Table 'classroom_subjects' verified/created.")

        # 9. Student Favourites Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_favourites (
                student_roll VARCHAR(100) NOT NULL,
                note_id INT NOT NULL,
                PRIMARY KEY (student_roll, note_id),
                FOREIGN KEY (student_roll) REFERENCES students (roll_number) ON DELETE CASCADE,
                FOREIGN KEY (note_id) REFERENCES notes (id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("Table 'student_favourites' verified/created.")

        # 10. Note Views Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS note_views (
                id INT AUTO_INCREMENT PRIMARY KEY,
                note_id INT NOT NULL,
                student_roll VARCHAR(100) NOT NULL,
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (note_id) REFERENCES notes (id) ON DELETE CASCADE,
                FOREIGN KEY (student_roll) REFERENCES students (roll_number) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("Table 'note_views' verified/created.")

        # Enable foreign key checks back
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()

        # Seed default superuser if not exists
        cursor.execute("SELECT COUNT(*) FROM superusers WHERE username = 'superuser'")
        if cursor.fetchone()[0] == 0:
            default_pass_hash = generate_password_hash("superuser123")
            cursor.execute(
                "INSERT INTO superusers (username, password_hash) VALUES (%s, %s)",
                ("superuser", default_pass_hash)
            )
            print("Seeded default superuser ('superuser' / 'superuser123').")

        conn.commit()
        print("Database setup completed successfully!")
        conn.close()

    except Exception as e:
        print(f"Error setting up tables: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_database()
