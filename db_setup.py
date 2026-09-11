import os
import sys

try:
    import sqlite3
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
from werkzeug.security import generate_password_hash as _werkzeug_generate_password_hash

def generate_password_hash(password, method='pbkdf2:sha256'):
    """Safe password hash generator using pbkdf2:sha256 for OpenSSL 1.0.2k / ClearOS 7 compatibility."""
    return _werkzeug_generate_password_hash(password, method=method)

# Database path (defaults to notes_library.db in the application directory)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "notes_library.db"))

def setup_database(db_path=None):
    target_db = db_path or DB_PATH
    print(f"[INFO] Initializing SQLite database at: {target_db}")

    # Ensure parent directory exists
    os.makedirs(os.path.dirname(os.path.abspath(target_db)), exist_ok=True)

    conn = sqlite3.connect(target_db, timeout=60.0)
    cursor = conn.cursor()

    try:
        # Enable Write-Ahead Logging for high concurrency and performance
        cursor.execute("PRAGMA journal_mode = WAL;")
        cursor.execute("PRAGMA synchronous = NORMAL;")
        cursor.execute("PRAGMA foreign_keys = ON;")

        # 1. Classrooms Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classrooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course TEXT NOT NULL,
                branch TEXT NOT NULL,
                semester INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                UNIQUE (course, branch, semester)
            );
        """)
        print("Table 'classrooms' verified/created.")

        # 2. Superusers Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS superusers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            );
        """)
        print("Table 'superusers' verified/created.")

        # 3. Admins Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                admin_name TEXT NOT NULL,
                classroom_id INTEGER NOT NULL,
                FOREIGN KEY (classroom_id) REFERENCES classrooms (id) ON DELETE CASCADE
            );
        """)
        print("Table 'admins' verified/created.")

        # 4. Students Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                roll_number TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                contact TEXT NOT NULL,
                classroom_id INTEGER NOT NULL,
                year INTEGER NULL,
                password_hash TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                FOREIGN KEY (classroom_id) REFERENCES classrooms (id) ON DELETE CASCADE
            );
        """)
        print("Table 'students' verified/created.")

        # 5. Notes Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                unit TEXT NOT NULL,
                topic TEXT NULL,
                file_path TEXT NOT NULL,
                classroom_id INTEGER NOT NULL,
                credit_roll TEXT NOT NULL,
                credit_name TEXT NOT NULL,
                uploaded_by_admin INTEGER NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (classroom_id) REFERENCES classrooms (id) ON DELETE CASCADE,
                FOREIGN KEY (uploaded_by_admin) REFERENCES admins (id) ON DELETE CASCADE
            );
        """)
        print("Table 'notes' verified/created.")

        # 6. Configured Courses Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configured_courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_name TEXT NOT NULL UNIQUE,
                total_semesters INTEGER NOT NULL
            );
        """)
        print("Table 'configured_courses' verified/created.")

        # 7. Configured Branches Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configured_branches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                branch_name TEXT NOT NULL,
                FOREIGN KEY (course_id) REFERENCES configured_courses (id) ON DELETE CASCADE,
                UNIQUE (course_id, branch_name)
            );
        """)
        print("Table 'configured_branches' verified/created.")

        # 8. Classroom Subjects Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classroom_subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                classroom_id INTEGER NOT NULL,
                subject_name TEXT NOT NULL,
                FOREIGN KEY (classroom_id) REFERENCES classrooms (id) ON DELETE CASCADE
            );
        """)
        print("Table 'classroom_subjects' verified/created.")

        # 9. Student Favourites Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_favourites (
                student_roll TEXT NOT NULL,
                note_id INTEGER NOT NULL,
                PRIMARY KEY (student_roll, note_id),
                FOREIGN KEY (student_roll) REFERENCES students (roll_number) ON DELETE CASCADE,
                FOREIGN KEY (note_id) REFERENCES notes (id) ON DELETE CASCADE
            );
        """)
        print("Table 'student_favourites' verified/created.")

        # 10. Note Views Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS note_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL,
                student_roll TEXT NOT NULL,
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (note_id) REFERENCES notes (id) ON DELETE CASCADE,
                FOREIGN KEY (student_roll) REFERENCES students (roll_number) ON DELETE CASCADE
            );
        """)
        print("Table 'note_views' verified/created.")

        conn.commit()

        # Seed default superuser if not exists
        cursor.execute("SELECT COUNT(*) FROM superusers WHERE username = ?", ("superuser",))
        if cursor.fetchone()[0] == 0:
            default_pass_hash = generate_password_hash("superuser123")
            cursor.execute(
                "INSERT INTO superusers (username, password_hash) VALUES (?, ?)",
                ("superuser", default_pass_hash)
            )
            conn.commit()
            print("Seeded default superuser ('superuser' / 'superuser123').")

        print("[SUCCESS] SQLite database setup completed successfully!")
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"[ERROR] Failed to set up SQLite database: {e}")
        cursor.close()
        conn.close()
        raise e

if __name__ == "__main__":
    setup_database()
