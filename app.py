from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_from_directory
from werkzeug.security import generate_password_hash as _werkzeug_generate_password_hash, check_password_hash

def generate_password_hash(password, method='pbkdf2:sha256'):
    """Safe password hash generator using pbkdf2:sha256 for OpenSSL 1.0.2k / ClearOS 7 compatibility."""
    return _werkzeug_generate_password_hash(password, method=method)

from werkzeug.utils import secure_filename
import os
import json
import re
from datetime import datetime
from db import query_db, get_db_connection

app = Flask(__name__)
app.secret_key = "notes_library_shobhit_university_secret_key_2026"

# Load student roster into memory (zero-dependency JSON first, Excel fallback)
STUDENT_ROSTER = {}

def load_student_roster():
    # 1. Try loading from pre-parsed JSON (fast, zero external dependencies)
    json_path = os.path.join(app.root_path, 'cslist.json')
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                STUDENT_ROSTER.update(data)
                # Seed test student roll number for integration testing
                STUDENT_ROSTER['TEST_STUDENT_001'] = 'Test Student A'
                print(f"Loaded {len(data)} students from cslist.json")
                return
        except Exception as e:
            print(f"Warning: Could not read cslist.json ({e}), falling back to Excel...")

    # 2. Fallback to cslist.xlsx with openpyxl if available
    wb_path = os.path.join(app.root_path, 'cslist.xlsx')
    if not os.path.exists(wb_path):
        print(f"Warning: Neither cslist.json nor cslist.xlsx found at {app.root_path}")
        STUDENT_ROSTER['TEST_STUDENT_001'] = 'Test Student A'
        return
    try:
        import openpyxl
        wb = openpyxl.load_workbook(wb_path, data_only=True, read_only=True)
        sheet = wb.active
        count = 0
        for row in sheet.iter_rows(values_only=True):
            if not row or len(row) < 2:
                continue
            roll_raw = row[0]
            name_raw = row[1]
            if roll_raw is None or name_raw is None:
                continue
            # skip header
            if "roll" in str(roll_raw).lower():
                continue
            # normalize roll number (remove trailing .0 if float and make uppercase)
            roll_str = str(roll_raw).strip()
            if roll_str.endswith('.0'):
                roll_str = roll_str[:-2]
            roll_str = roll_str.upper()
            STUDENT_ROSTER[roll_str] = str(name_raw).strip()
            count += 1
        wb.close()
        # Seed test student roll number for integration testing
        STUDENT_ROSTER['TEST_STUDENT_001'] = 'Test Student A'
        print(f"Loaded {count} students from cslist.xlsx")
    except Exception as e:
        print("Error loading student roster from Excel:", e)
        STUDENT_ROSTER['TEST_STUDENT_001'] = 'Test Student A'

# Run loader
load_student_roster()

# Configure Uploads
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB limit

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/login-required')
def login_required_page():
    return render_template('login_required.html')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

# Decorators for authentication
def require_student():
    if 'role' not in session or session['role'] != 'student':
        return False
    return True

def require_admin():
    if 'role' not in session or session['role'] != 'admin':
        return False
    return True

def require_superuser():
    if 'role' not in session or session['role'] != 'superuser':
        return False
    return True

# --- HTML Page Routes ---

@app.route('/')
def index():
    if 'role' in session:
        if session['role'] == 'student':
            return redirect(url_for('student_dashboard'))
        elif session['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session['role'] == 'superuser':
            return redirect(url_for('superuser_dashboard'))
    
    # Fetch classrooms for student registration dropdown
    classrooms = query_db("SELECT id, course, branch, semester FROM classrooms WHERE status = 'active' ORDER BY course, branch, semester")
    return render_template('login.html', classrooms=classrooms)

@app.route('/student')
def student_dashboard():
    if not require_student():
        return redirect(url_for('index'))
    return render_template('student.html')

@app.route('/admin')
def admin_dashboard():
    if not require_admin():
        return redirect(url_for('index'))
    return render_template('admin.html')

@app.route('/superuser')
def superuser_dashboard():
    if not require_superuser():
        return redirect(url_for('index'))
    return render_template('superuser.html')

# --- API Authentication Routes ---

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    role = data.get('role')
    
    if role == 'student':
        roll_number = data.get('roll_number')
        password = data.get('password')
        
        if not roll_number or not password:
            return jsonify({"success": False, "message": "Roll number and password are required."}), 400
            
        student = query_db("SELECT * FROM students WHERE roll_number = %s", (roll_number,), one=True)
        if not student:
            return jsonify({"success": False, "message": "Invalid Roll Number or Password."}), 401
            
        if not check_password_hash(student['password_hash'], password):
            return jsonify({"success": False, "message": "Invalid Roll Number or Password."}), 401
            
        if student['status'] == 'pending':
            return jsonify({"success": False, "message": "Your registration is pending approval by the Admin."}), 403
        elif student['status'] == 'blocked':
            return jsonify({"success": False, "message": "Your account has been blocked. Please contact the Admin."}), 403
            
        # Check if classroom is paused
        classroom = query_db("SELECT status FROM classrooms WHERE id = %s", (student['classroom_id'],), one=True)
        if classroom and classroom['status'] == 'paused':
            return jsonify({"success": False, "message": "Your classroom has been paused by the Superuser. Access suspended."}), 403
            
        session['role'] = 'student'
        session['roll_number'] = student['roll_number']
        session['name'] = student['name']
        session['classroom_id'] = student['classroom_id']
        
        next_url = session.pop('next_url', None)
        redirect_to = next_url if next_url else "/student"
        return jsonify({"success": True, "redirect": redirect_to})
        
    elif role == 'admin':
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"success": False, "message": "Username and password are required."}), 400
            
        admin = query_db("SELECT * FROM admins WHERE username = %s", (username,), one=True)
        if not admin or not check_password_hash(admin['password_hash'], password):
            return jsonify({"success": False, "message": "Invalid Username or Password."}), 401
            
        # Check if classroom is paused
        classroom = query_db("SELECT status FROM classrooms WHERE id = %s", (admin['classroom_id'],), one=True)
        if classroom and classroom['status'] == 'paused':
            return jsonify({"success": False, "message": "Your classroom has been paused by the Superuser. Access suspended."}), 403
            
        session['role'] = 'admin'
        session['admin_id'] = admin['id']
        session['username'] = admin['username']
        session['admin_name'] = admin['admin_name']
        session['classroom_id'] = admin['classroom_id']
        
        next_url = session.pop('next_url', None)
        redirect_to = next_url if next_url else "/admin"
        return jsonify({"success": True, "redirect": redirect_to})
        
    elif role == 'superuser':
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"success": False, "message": "Username and password are required."}), 400
            
        super_user = query_db("SELECT * FROM superusers WHERE username = %s", (username,), one=True)
        if not super_user or not check_password_hash(super_user['password_hash'], password):
            return jsonify({"success": False, "message": "Invalid Username or Password."}), 401
            
        session['role'] = 'superuser'
        session['username'] = super_user['username']
        
        next_url = session.pop('next_url', None)
        redirect_to = next_url if next_url else "/superuser"
        return jsonify({"success": True, "redirect": redirect_to})
        
    return jsonify({"success": False, "message": "Invalid login role specified."}), 400

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({"success": True, "redirect": "/"})

@app.route('/api/classrooms/active', methods=['GET'])
def api_active_classrooms():
    classrooms = query_db("SELECT id, course, branch, semester FROM classrooms WHERE status = 'active' ORDER BY course, branch, semester")
    return jsonify({"success": True, "classrooms": classrooms})


@app.route('/api/student/lookup/<roll_number>', methods=['GET'])
def api_student_lookup(roll_number):
    roll_clean = roll_number.strip().upper()
    if roll_clean in STUDENT_ROSTER:
        return jsonify({"success": True, "name": STUDENT_ROSTER[roll_clean]})
    return jsonify({"success": False, "message": "Roll number not found in university roster."}), 404

# --- Student Panel APIs ---

@app.route('/api/student/register', methods=['POST'])
def api_student_register():
    data = request.get_json() or {}
    roll_number = data.get('roll_number')
    contact = data.get('contact')
    classroom_id = data.get('classroom_id')
    password = data.get('password')
    
    if not all([roll_number, contact, classroom_id, password]):
        return jsonify({"success": False, "message": "All registration fields are required."}), 400
        
    # Validate contact number is exactly 10 digits
    contact_clean = str(contact).strip()
    if not re.match(r'^\d{10}$', contact_clean):
        return jsonify({"success": False, "message": "Contact number must be exactly 10 digits."}), 400
        
    roll_clean = roll_number.strip().upper()
    # Enforce roster check
    if roll_clean not in STUDENT_ROSTER:
        return jsonify({"success": False, "message": "Roll number not found in university roster. Registration blocked."}), 403
        
    name = STUDENT_ROSTER[roll_clean]
    
    # Check if student already exists
    existing = query_db("SELECT roll_number FROM students WHERE roll_number = %s", (roll_clean,), one=True)
    if existing:
        return jsonify({"success": False, "message": "A student with this Roll Number is already registered."}), 409
        
    try:
        pw_hash = generate_password_hash(password)
        query_db(
            "INSERT INTO students (roll_number, name, contact, classroom_id, password_hash, status) VALUES (%s, %s, %s, %s, %s, 'pending')",
            (roll_clean, name, contact, classroom_id, pw_hash),
            commit=True
        )
        return jsonify({"success": True, "message": "Registration successful! Waiting for Admin approval."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Database error: {str(e)}"}), 500

@app.route('/api/student/profile', methods=['GET'])
def api_student_profile():
    if not require_student():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    student = query_db(
        """SELECT s.roll_number, s.name, s.contact, s.year, c.course, c.branch, c.semester 
           FROM students s 
           JOIN classrooms c ON s.classroom_id = c.id 
           WHERE s.roll_number = %s""",
        (session['roll_number'],), one=True
    )
    return jsonify({"success": True, "profile": student})

@app.route('/api/student/notes', methods=['GET'])
def api_student_notes():
    if not require_student():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    # Student can only see notes for their own classroom, marked with is_favourite status
    notes = query_db(
        """SELECT n.id, n.subject, n.unit, n.topic, n.file_path, n.credit_roll, n.credit_name, n.uploaded_at, a.admin_name,
                  IF(sf.student_roll IS NULL, 0, 1) as is_favourite
           FROM notes n
           JOIN admins a ON n.uploaded_by_admin = a.id
           LEFT JOIN student_favourites sf ON n.id = sf.note_id AND sf.student_roll = %s
           WHERE n.classroom_id = %s
           ORDER BY n.uploaded_at DESC""",
        (session['roll_number'], session['classroom_id'])
    )
    return jsonify({"success": True, "notes": notes})


# --- Admin Panel APIs ---

@app.route('/api/admin/classroom', methods=['GET'])
def api_admin_classroom():
    if not require_admin():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    classroom = query_db(
        "SELECT id, course, branch, semester FROM classrooms WHERE id = %s",
        (session['classroom_id'],), one=True
    )
    if classroom:
        # Fetch subjects
        subs = query_db("SELECT subject_name FROM classroom_subjects WHERE classroom_id = %s", (classroom['id'],))
        classroom['subjects'] = [s['subject_name'] for s in subs]
    return jsonify({"success": True, "classroom": classroom})

@app.route('/api/admin/students/pending', methods=['GET'])
def api_admin_pending_students():
    if not require_admin():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    students = query_db(
        "SELECT roll_number, name, contact, year FROM students WHERE classroom_id = %s AND status = 'pending' ORDER BY name",
        (session['classroom_id'],)
    )
    return jsonify({"success": True, "students": students})

@app.route('/api/admin/students/approved', methods=['GET'])
def api_admin_approved_students():
    if not require_admin():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    students = query_db(
        "SELECT roll_number, name, contact, year, status FROM students WHERE classroom_id = %s AND status != 'pending' ORDER BY name",
        (session['classroom_id'],)
    )
    return jsonify({"success": True, "students": students})

@app.route('/api/admin/student/approve', methods=['POST'])
def api_admin_approve_student():
    if not require_admin():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    roll_number = data.get('roll_number')
    
    if not roll_number:
        return jsonify({"success": False, "message": "Roll number is required."}), 400
        
    # Verify student is in admin's classroom
    student = query_db("SELECT classroom_id FROM students WHERE roll_number = %s", (roll_number,), one=True)
    if not student or student['classroom_id'] != session['classroom_id']:
        return jsonify({"success": False, "message": "Student not found or access denied."}), 403
        
    query_db("UPDATE students SET status = 'approved' WHERE roll_number = %s", (roll_number,), commit=True)
    return jsonify({"success": True, "message": "Student approved successfully."})

@app.route('/api/admin/student/delete_request', methods=['POST'])
def api_admin_delete_student_request():
    if not require_admin():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    roll_number = data.get('roll_number')
    
    if not roll_number:
        return jsonify({"success": False, "message": "Roll number is required."}), 400
        
    # Verify student is in admin's classroom and status is pending
    student = query_db("SELECT classroom_id, status FROM students WHERE roll_number = %s", (roll_number,), one=True)
    if not student or student['classroom_id'] != session['classroom_id']:
        return jsonify({"success": False, "message": "Student not found or access denied."}), 403
        
    if student['status'] != 'pending':
        return jsonify({"success": False, "message": "Can only delete pending registration requests."}), 400
        
    query_db("DELETE FROM students WHERE roll_number = %s", (roll_number,), commit=True)
    return jsonify({"success": True, "message": "Student registration request deleted successfully."})

@app.route('/api/admin/student/block', methods=['POST'])
def api_admin_block_student():
    if not require_admin():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    roll_number = data.get('roll_number')
    status = data.get('status')  # 'approved' (to unblock) or 'blocked'
    
    if not roll_number or status not in ['approved', 'blocked']:
        return jsonify({"success": False, "message": "Invalid parameters."}), 400
        
    # Verify student is in admin's classroom
    student = query_db("SELECT classroom_id FROM students WHERE roll_number = %s", (roll_number,), one=True)
    if not student or student['classroom_id'] != session['classroom_id']:
        return jsonify({"success": False, "message": "Student not found or access denied."}), 403
        
    query_db("UPDATE students SET status = %s WHERE roll_number = %s", (status, roll_number), commit=True)
    action = "blocked" if status == "blocked" else "unblocked"
    return jsonify({"success": True, "message": f"Student has been {action}."})

@app.route('/api/admin/student/change_password', methods=['POST'])
def api_admin_change_student_password():
    if not require_admin():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    roll_number = data.get('roll_number')
    new_password = data.get('new_password')
    
    if not roll_number or not new_password:
        return jsonify({"success": False, "message": "Roll number and new password are required."}), 400
        
    # Verify student is in admin's classroom
    student = query_db("SELECT classroom_id FROM students WHERE roll_number = %s", (roll_number,), one=True)
    if not student or student['classroom_id'] != session['classroom_id']:
        return jsonify({"success": False, "message": "Student not found or access denied."}), 403
        
    pw_hash = generate_password_hash(new_password)
    query_db("UPDATE students SET password_hash = %s WHERE roll_number = %s", (pw_hash, roll_number), commit=True)
    return jsonify({"success": True, "message": "Student password updated successfully."})

@app.route('/api/admin/notes/upload', methods=['POST'])
def api_admin_upload_notes():
    if not require_admin():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    if 'notes_file' not in request.files:
        return jsonify({"success": False, "message": "No file part in request."}), 400
        
    file = request.files['notes_file']
    subject = request.form.get('subject')
    unit = request.form.get('unit', '').strip()
    topic = request.form.get('topic', '').strip() or None
    credit_roll = request.form.get('credit_roll', '').strip().upper()
    
    if not subject or file.filename == '':
        return jsonify({"success": False, "message": "Subject and PDF file are required."}), 400
        
    if not unit:
        return jsonify({"success": False, "message": "Unit is required."}), 400
        
    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Only PDF files are allowed."}), 400
        
    # Enforce roster check for credit roll number
    if credit_roll not in STUDENT_ROSTER:
        return jsonify({"success": False, "message": f"Roll number '{credit_roll}' not found in university roster."}), 400
        
    credit_name = STUDENT_ROSTER[credit_roll]
        
    # Get admin's classroom details to tag the file
    classroom = query_db("SELECT course, branch, semester FROM classrooms WHERE id = %s", (session['classroom_id'],), one=True)
    if not classroom:
        return jsonify({"success": False, "message": "Classroom assignment error."}), 500
        
    course_clean = re.sub(r'[^a-zA-Z0-9]', '_', classroom['course'])
    branch_clean = re.sub(r'[^a-zA-Z0-9]', '_', classroom['branch'])
    sem_clean = f"Sem{classroom['semester']}"
    sub_clean = re.sub(r'[^a-zA-Z0-9]', '_', subject)
    
    # Automatically mark/rename the PDF with course, branch, and semester
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    secured_orig = secure_filename(file.filename)
    new_filename = f"{course_clean}_{branch_clean}_{sem_clean}_{sub_clean}_{timestamp}.pdf"
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
    file.save(file_path)
    
    # Save metadata in database
    relative_path = f"uploads/{new_filename}"
    try:
        query_db(
            """INSERT INTO notes (subject, unit, topic, file_path, classroom_id, credit_roll, credit_name, uploaded_by_admin) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (subject, unit, topic, relative_path, session['classroom_id'], credit_roll, credit_name, session['admin_id']),
            commit=True
        )
        return jsonify({"success": True, "message": "Notes uploaded and classroom-marked successfully!"})
    except Exception as e:
        # Delete file if DB insert fails
        if os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({"success": False, "message": f"Database error: {str(e)}"}), 500

@app.route('/api/admin/notes', methods=['GET'])
def api_admin_notes():
    if not require_admin():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    notes = query_db(
        "SELECT id, subject, unit, topic, file_path, credit_roll, credit_name, uploaded_at FROM notes WHERE uploaded_by_admin = %s ORDER BY uploaded_at DESC",
        (session['admin_id'],)
    )
    return jsonify({"success": True, "notes": notes})

@app.route('/api/admin/notes/delete', methods=['POST'])
def api_admin_delete_note():
    if not require_admin():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    note_id = data.get('note_id')
    
    if not note_id:
        return jsonify({"success": False, "message": "Note ID is required."}), 400
        
    # Verify admin owns the note or handles the same classroom
    note = query_db("SELECT file_path, uploaded_by_admin FROM notes WHERE id = %s", (note_id,), one=True)
    if not note or note['uploaded_by_admin'] != session['admin_id']:
        return jsonify({"success": False, "message": "Note not found or access denied."}), 403
        
    # Delete file from disk
    full_path = os.path.join(app.root_path, note['file_path'])
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
        except Exception as e:
            print(f"Error removing physical file: {e}")
            
    # Delete from DB
    query_db("DELETE FROM notes WHERE id = %s", (note_id,), commit=True)
    return jsonify({"success": True, "message": "Note deleted successfully."})


# --- Superuser Panel APIs ---

@app.route('/api/superuser/stats', methods=['GET'])
def api_superuser_stats():
    if not require_superuser():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    student_count = query_db("SELECT COUNT(*) as count FROM students", one=True)['count']
    admin_count = query_db("SELECT COUNT(*) as count FROM admins", one=True)['count']
    note_count = query_db("SELECT COUNT(*) as count FROM notes", one=True)['count']
    classroom_count = query_db("SELECT COUNT(*) as count FROM classrooms", one=True)['count']
    
    return jsonify({
        "success": True,
        "stats": {
            "students": student_count,
            "admins": admin_count,
            "notes": note_count,
            "classrooms": classroom_count
        }
    })

@app.route('/api/superuser/classrooms', methods=['GET'])
def api_superuser_classrooms():
    if not require_superuser():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    classrooms = query_db("SELECT id, course, branch, semester, status FROM classrooms ORDER BY course, branch, semester")
    # Fetch subjects for each classroom
    for cls in classrooms:
        subs = query_db("SELECT subject_name FROM classroom_subjects WHERE classroom_id = %s", (cls['id'],))
        cls['subjects'] = [s['subject_name'] for s in subs]
    return jsonify({"success": True, "classrooms": classrooms})

@app.route('/api/superuser/classroom/create', methods=['POST'])
def api_superuser_create_classroom():
    if not require_superuser():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    course = data.get('course')
    branch = data.get('branch')
    semester = data.get('semester')
    subjects_str = data.get('subjects', '')
    
    if not course or not branch or not semester:
        return jsonify({"success": False, "message": "Course, branch, and semester are required."}), 400
        
    try:
        semester_int = int(semester)
        if semester_int < 1:
            return jsonify({"success": False, "message": "Semester must be a positive integer."}), 400
    except ValueError:
        return jsonify({"success": False, "message": "Semester must be an integer."}), 400
        
    # Check course configuration limit
    course_config = query_db("SELECT total_semesters FROM configured_courses WHERE course_name = %s", (course,), one=True)
    if not course_config:
        return jsonify({"success": False, "message": f"Course '{course}' must first be configured in Configure Courses panel."}), 400
        
    if semester_int > course_config['total_semesters']:
        return jsonify({"success": False, "message": f"Classroom semester cannot exceed the configured course limit of {course_config['total_semesters']} semesters."}), 400
        
    # Check if duplicate
    existing = query_db(
        "SELECT id FROM classrooms WHERE course = %s AND branch = %s AND semester = %s",
        (course, branch, semester_int), one=True
    )
    if existing:
        return jsonify({"success": False, "message": "This classroom already exists."}), 409
        
    try:
        # Save classroom and get its ID
        classroom_id = query_db(
            "INSERT INTO classrooms (course, branch, semester) VALUES (%s, %s, %s)",
            (course, branch, semester_int), commit=True
        )
        
        # Save subjects
        if subjects_str:
            subjects = [s.strip() for s in subjects_str.split(',') if s.strip()]
            for sub in subjects:
                query_db(
                    "INSERT INTO classroom_subjects (classroom_id, subject_name) VALUES (%s, %s)",
                    (classroom_id, sub), commit=True
                )
                
        return jsonify({"success": True, "message": "Classroom created successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Database error: {str(e)}"}), 500

@app.route('/api/superuser/classroom/delete', methods=['POST'])
def api_superuser_delete_classroom():
    if not require_superuser():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    classroom_id = data.get('classroom_id')
    
    if not classroom_id:
        return jsonify({"success": False, "message": "Classroom ID is required."}), 400
        
    try:
        query_db("DELETE FROM classrooms WHERE id = %s", (classroom_id,), commit=True)
        return jsonify({"success": True, "message": "Classroom deleted successfully (along with associated students, admins, and notes)."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Database error: {str(e)}"}), 500

@app.route('/api/superuser/classroom/toggle_pause', methods=['POST'])
def api_superuser_toggle_pause_classroom():
    if not require_superuser():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    classroom_id = data.get('classroom_id')
    
    if not classroom_id:
        return jsonify({"success": False, "message": "Classroom ID is required."}), 400
        
    classroom = query_db("SELECT status FROM classrooms WHERE id = %s", (classroom_id,), one=True)
    if not classroom:
        return jsonify({"success": False, "message": "Classroom not found."}), 404
        
    new_status = 'paused' if classroom['status'] == 'active' else 'active'
    try:
        query_db("UPDATE classrooms SET status = %s WHERE id = %s", (new_status, classroom_id), commit=True)
        return jsonify({"success": True, "message": f"Classroom status updated to {new_status}."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Database error: {str(e)}"}), 500

@app.route('/api/superuser/admins', methods=['GET'])
def api_superuser_admins():
    if not require_superuser():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    admins = query_db(
        """SELECT a.id, a.username, a.admin_name, a.classroom_id, c.course, c.branch, c.semester 
           FROM admins a
           JOIN classrooms c ON a.classroom_id = c.id
           ORDER BY a.admin_name"""
    )
    return jsonify({"success": True, "admins": admins})

@app.route('/api/superuser/admin/create', methods=['POST'])
def api_superuser_create_admin():
    if not require_superuser():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    admin_name = data.get('admin_name')
    classroom_id = data.get('classroom_id')
    
    if not all([username, password, admin_name, classroom_id]):
        return jsonify({"success": False, "message": "All fields are required."}), 400
        
    # Check duplicate username in both admins and superusers (safety check)
    dup = query_db("SELECT id FROM admins WHERE username = %s", (username,), one=True)
    dup_su = query_db("SELECT id FROM superusers WHERE username = %s", (username,), one=True)
    if dup or dup_su:
        return jsonify({"success": False, "message": "Username is already taken."}), 409
        
    try:
        pw_hash = generate_password_hash(password)
        query_db(
            "INSERT INTO admins (username, password_hash, admin_name, classroom_id) VALUES (%s, %s, %s, %s)",
            (username, pw_hash, admin_name, classroom_id), commit=True
        )
        return jsonify({"success": True, "message": "Admin account created successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Database error: {str(e)}"}), 500

@app.route('/api/superuser/admin/update', methods=['POST'])
def api_superuser_update_admin():
    if not require_superuser():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    admin_id = data.get('admin_id')
    username = data.get('username')
    password = data.get('password')  # optional
    admin_name = data.get('admin_name')
    classroom_id = data.get('classroom_id')
    
    if not all([admin_id, username, admin_name, classroom_id]):
        return jsonify({"success": False, "message": "Admin ID, username, admin name, and classroom are required."}), 400
        
    # Check duplicate username (exclude this admin_id)
    dup = query_db("SELECT id FROM admins WHERE username = %s AND id != %s", (username, admin_id), one=True)
    if dup:
        return jsonify({"success": False, "message": "Username is already taken by another user."}), 409
        
    try:
        if password:
            pw_hash = generate_password_hash(password)
            query_db(
                "UPDATE admins SET username = %s, password_hash = %s, admin_name = %s, classroom_id = %s WHERE id = %s",
                (username, pw_hash, admin_name, classroom_id, admin_id), commit=True
            )
        else:
            query_db(
                "UPDATE admins SET username = %s, admin_name = %s, classroom_id = %s WHERE id = %s",
                (username, admin_name, classroom_id, admin_id), commit=True
            )
        return jsonify({"success": True, "message": "Admin account updated successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Database error: {str(e)}"}), 500

@app.route('/api/superuser/admin/delete', methods=['POST'])
def api_superuser_delete_admin():
    if not require_superuser():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    admin_id = data.get('admin_id')
    
    if not admin_id:
        return jsonify({"success": False, "message": "Admin ID is required."}), 400
        
    try:
        query_db("DELETE FROM admins WHERE id = %s", (admin_id,), commit=True)
        return jsonify({"success": True, "message": "Admin account deleted successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Database error: {str(e)}"}), 500

@app.route('/api/superuser/promote', methods=['POST'])
def api_superuser_promote_all():
    if not require_superuser():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    password = data.get('superuser_password')
    
    if not password:
        return jsonify({"success": False, "message": "Superuser password confirmation is required."}), 400
        
    # Verify superuser password
    su = query_db("SELECT password_hash FROM superusers WHERE username = %s", (session['username'],), one=True)
    if not su or not check_password_hash(su['password_hash'], password):
        return jsonify({"success": False, "message": "Incorrect password. Promotion aborted."}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        # Get course semester limits
        cursor.execute("SELECT course_name, total_semesters FROM configured_courses")
        course_limits = {row['course_name']: row['total_semesters'] for row in cursor.fetchall()}
        
        for course_name, limit in course_limits.items():
            cursor.execute("""
                DELETE FROM students 
                WHERE classroom_id IN (
                    SELECT c.id FROM classrooms c
                    WHERE c.course = %s AND c.semester >= %s
                )
            """, (course_name, limit))
        
        # 2. Fetch all classrooms that have non-graduating students currently registered
        cursor.execute("""
            SELECT DISTINCT c.id, c.course, c.branch, c.semester 
            FROM classrooms c
            JOIN students s ON s.classroom_id = c.id
        """)
        active_classrooms = cursor.fetchall()
        
        classroom_shifts = {}
        for cls in active_classrooms:
            course = cls['course']
            branch = cls['branch']
            curr_sem = cls['semester']
            next_sem = curr_sem + 1
            
            # Verify the next semester classroom exists
            cursor.execute(
                "SELECT id FROM classrooms WHERE course = %s AND branch = %s AND semester = %s",
                (course, branch, next_sem)
            )
            next_cls = cursor.fetchone()
            if not next_cls:
                raise Exception(f"Next semester classroom for '{course} - {branch} - Semester {next_sem}' does not exist. Please create appropriate classrooms first.")
                
            classroom_shifts[cls['id']] = next_cls['id']
            
        # 3. Update students (in descending order to avoid overlap)
        classrooms_sorted = sorted(active_classrooms, key=lambda x: x['semester'], reverse=True)
        for cls in classrooms_sorted:
            old_id = cls['id']
            if old_id in classroom_shifts:
                new_id = classroom_shifts[old_id]
                cursor.execute(
                    "UPDATE students SET classroom_id = %s WHERE classroom_id = %s",
                    (new_id, old_id)
                )
                
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True, 
            "message": "All students have been successfully promoted to the next semester! Graduating students in their last semester were permanently deleted."
        })
        
    except Exception as e:
        conn.rollback()
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": f"Promotion failed: {str(e)}"}), 500


@app.route('/api/superuser/catchback', methods=['POST'])
def api_superuser_catchback_all():
    if not require_superuser():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    password = data.get('superuser_password')
    
    if not password:
        return jsonify({"success": False, "message": "Superuser password confirmation is required."}), 400
        
    # Verify superuser password
    su = query_db("SELECT password_hash FROM superusers WHERE username = %s", (session['username'],), one=True)
    if not su or not check_password_hash(su['password_hash'], password):
        return jsonify({"success": False, "message": "Incorrect password. Catchback aborted."}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        # 1. Fetch classrooms that currently have students
        cursor.execute("""
            SELECT DISTINCT c.id, c.course, c.branch, c.semester 
            FROM classrooms c
            JOIN students s ON s.classroom_id = c.id
        """)
        active_classrooms = cursor.fetchall()
        
        classroom_shifts = {}
        for cls in active_classrooms:
            course = cls['course']
            branch = cls['branch']
            curr_sem = cls['semester']
            
            if curr_sem <= 1:
                raise Exception(f"Cannot catch back students of '{course} - {branch} - Sem 1' because they are already in Semester 1.")
                
            prev_sem = curr_sem - 1
            
            # Verify previous semester classroom exists
            cursor.execute(
                "SELECT id FROM classrooms WHERE course = %s AND branch = %s AND semester = %s",
                (course, branch, prev_sem)
            )
            prev_cls = cursor.fetchone()
            if not prev_cls:
                raise Exception(f"Previous semester classroom for '{course} - {branch} - Semester {prev_sem}' does not exist. Please create appropriate classrooms first.")
                
            classroom_shifts[cls['id']] = prev_cls['id']
            
        # 2. Update students (in ascending order of semester to avoid conflicts)
        classrooms_sorted = sorted(active_classrooms, key=lambda x: x['semester'], reverse=False)
        for cls in classrooms_sorted:
            old_id = cls['id']
            if old_id in classroom_shifts:
                new_id = classroom_shifts[old_id]
                cursor.execute(
                    "UPDATE students SET classroom_id = %s WHERE classroom_id = %s",
                    (new_id, old_id)
                )
                
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"success": True, "message": "All students have been successfully rolled back to their previous semester!"})
        
    except Exception as e:
        conn.rollback()
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": f"Catchback failed: {str(e)}"}), 500


@app.route('/api/superuser/classroom/<int:classroom_id>/subjects', methods=['GET'])
def api_superuser_classroom_subjects(classroom_id):
    if not require_superuser():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    subs = query_db("SELECT subject_name FROM classroom_subjects WHERE classroom_id = %s ORDER BY subject_name", (classroom_id,))
    subjects = [s['subject_name'] for s in subs]
    return jsonify({"success": True, "subjects": subjects})

@app.route('/api/superuser/classroom/<int:classroom_id>/subject/add', methods=['POST'])
def api_superuser_classroom_subject_add(classroom_id):
    if not require_superuser():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    data = request.get_json() or {}
    subject_name = data.get('subject_name', '').strip()
    if not subject_name:
        return jsonify({"success": False, "message": "Subject name is required."}), 400
        
    # Check duplicate
    exists = query_db("SELECT id FROM classroom_subjects WHERE classroom_id = %s AND subject_name = %s", (classroom_id, subject_name), one=True)
    if exists:
        return jsonify({"success": False, "message": "Subject already exists in this classroom."}), 400
        
    query_db("INSERT INTO classroom_subjects (classroom_id, subject_name) VALUES (%s, %s)", (classroom_id, subject_name), commit=True)
    return jsonify({"success": True, "message": "Subject added successfully."})

@app.route('/api/superuser/classroom/<int:classroom_id>/subject/delete', methods=['POST'])
def api_superuser_classroom_subject_delete(classroom_id):
    if not require_superuser():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    data = request.get_json() or {}
    subject_name = data.get('subject_name', '').strip()
    if not subject_name:
        return jsonify({"success": False, "message": "Subject name is required."}), 400
        
    query_db("DELETE FROM classroom_subjects WHERE classroom_id = %s AND subject_name = %s", (classroom_id, subject_name), commit=True)
    return jsonify({"success": True, "message": "Subject removed successfully."})


# --- Superuser profile / credentials change ---

@app.route('/api/superuser/change_password', methods=['POST'])
def api_superuser_change_password():
    if not require_superuser():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    new_password = data.get('new_password')
    
    if not new_password:
        return jsonify({"success": False, "message": "New password is required."}), 400
        
    pw_hash = generate_password_hash(new_password)
    query_db(
        "UPDATE superusers SET password_hash = %s WHERE username = %s",
        (pw_hash, session['username']),
        commit=True
    )
    return jsonify({"success": True, "message": "Superuser password updated successfully."})


# --- Static Uploads Serving (Secured) ---
@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    if 'role' not in session:
        session['next_url'] = request.path
        return redirect(url_for('login_required_page'))
    
    # If student, log the view event
    if session['role'] == 'student':
        relative_path = f"uploads/{filename}"
        note = query_db("SELECT id FROM notes WHERE file_path = %s", (relative_path,), one=True)
        if note:
            try:
                query_db("INSERT INTO note_views (note_id, student_roll) VALUES (%s, %s)",
                         (note['id'], session['roll_number']), commit=True)
            except Exception as e:
                print(f"Error logging note view: {e}")
                
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# --- Student Favorites APIs ---

@app.route('/api/student/favourites', methods=['GET'])
def api_student_favourites():
    if not require_student():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    favs = query_db("SELECT note_id FROM student_favourites WHERE student_roll = %s", (session['roll_number'],))
    fav_ids = [f['note_id'] for f in favs]
    return jsonify({"success": True, "favourites": fav_ids})

@app.route('/api/student/favourite/toggle', methods=['POST'])
def api_student_favourite_toggle():
    if not require_student():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    data = request.get_json() or {}
    note_id = data.get('note_id')
    if not note_id:
        return jsonify({"success": False, "message": "Note ID is required"}), 400
        
    fav = query_db("SELECT * FROM student_favourites WHERE student_roll = %s AND note_id = %s",
                   (session['roll_number'], note_id), one=True)
    if fav:
        query_db("DELETE FROM student_favourites WHERE student_roll = %s AND note_id = %s",
                 (session['roll_number'], note_id), commit=True)
        return jsonify({"success": True, "favourited": False, "message": "Removed from Favourites."})
    else:
        try:
            query_db("INSERT INTO student_favourites (student_roll, note_id) VALUES (%s, %s)",
                     (session['roll_number'], note_id), commit=True)
            return jsonify({"success": True, "favourited": True, "message": "Added to Favourites."})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500


# --- Admin Analytics API ---

@app.route('/api/admin/analytics', methods=['GET'])
def api_admin_analytics():
    if not require_admin():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    classroom_id = session['classroom_id']
    
    total_views = query_db(
        """SELECT COUNT(nv.id) as count 
           FROM note_views nv
           JOIN notes n ON nv.note_id = n.id
           WHERE n.classroom_id = %s""",
        (classroom_id,), one=True
    )['count']
    
    active_students = query_db(
        """SELECT COUNT(DISTINCT nv.student_roll) as count 
           FROM note_views nv
           JOIN notes n ON nv.note_id = n.id
           WHERE n.classroom_id = %s""",
        (classroom_id,), one=True
    )['count']
    
    total_notes = query_db(
        "SELECT COUNT(*) as count FROM notes WHERE classroom_id = %s",
        (classroom_id,), one=True
    )['count']
    
    popular_notes = query_db(
        """SELECT n.subject, n.credit_name, COUNT(nv.id) as views
           FROM notes n
           LEFT JOIN note_views nv ON n.id = nv.note_id
           WHERE n.classroom_id = %s
           GROUP BY n.id, n.subject, n.credit_name
           ORDER BY views DESC
           LIMIT 5""",
        (classroom_id,)
    )
    
    return jsonify({
        "success": True,
        "analytics": {
            "total_views": total_views,
            "active_students": active_students,
            "total_notes": total_notes,
            "popular_notes": popular_notes
        }
    })


# --- Superuser Course Configurations APIs ---

@app.route('/api/superuser/courses', methods=['GET'])
def api_superuser_courses():
    if not require_superuser() and not require_student() and not require_admin():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    courses = query_db("SELECT id, course_name, total_semesters FROM configured_courses ORDER BY course_name")
    return jsonify({"success": True, "courses": courses})

@app.route('/api/superuser/course/create', methods=['POST'])
def api_superuser_create_course():
    if not require_superuser():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    data = request.get_json() or {}
    course_name = data.get('course_name')
    total_semesters = data.get('total_semesters')
    
    if not course_name or not total_semesters:
        return jsonify({"success": False, "message": "Course name and total semesters are required."}), 400
        
    try:
        query_db(
            "INSERT INTO configured_courses (course_name, total_semesters) VALUES (%s, %s)",
            (course_name, int(total_semesters)),
            commit=True
        )
        return jsonify({"success": True, "message": "Course configured successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/superuser/course/delete', methods=['POST'])
def api_superuser_delete_course():
    if not require_superuser():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    data = request.get_json() or {}
    course_id = data.get('course_id')
    if not course_id:
        return jsonify({"success": False, "message": "Course ID is required."}), 400
    try:
        query_db("DELETE FROM configured_courses WHERE id = %s", (course_id,), commit=True)
        return jsonify({"success": True, "message": "Course deleted successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/superuser/course/branches/<int:course_id>', methods=['GET'])
def api_superuser_course_branches(course_id):
    if not require_superuser() and not require_student() and not require_admin():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    branches = query_db("SELECT id, branch_name FROM configured_branches WHERE course_id = %s ORDER BY branch_name", (course_id,))
    return jsonify({"success": True, "branches": branches})

@app.route('/api/superuser/course/branch/create', methods=['POST'])
def api_superuser_create_branch():
    if not require_superuser():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    data = request.get_json() or {}
    course_id = data.get('course_id')
    branch_name = data.get('branch_name')
    
    if not course_id or not branch_name:
        return jsonify({"success": False, "message": "Course ID and branch name are required."}), 400
        
    try:
        query_db(
            "INSERT INTO configured_branches (course_id, branch_name) VALUES (%s, %s)",
            (course_id, branch_name),
            commit=True
        )
        return jsonify({"success": True, "message": "Branch configured successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/superuser/course/branch/delete', methods=['POST'])
def api_superuser_delete_branch():
    if not require_superuser():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    data = request.get_json() or {}
    branch_id = data.get('branch_id')
    if not branch_id:
        return jsonify({"success": False, "message": "Branch ID is required."}), 400
    try:
        query_db("DELETE FROM configured_branches WHERE id = %s", (branch_id,), commit=True)
        return jsonify({"success": True, "message": "Branch deleted successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# --- Superuser System Analytics API ---

@app.route('/api/superuser/analytics', methods=['GET'])
def api_superuser_analytics():
    if not require_superuser():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    total_views = query_db("SELECT COUNT(*) as count FROM note_views", one=True)['count']
    active_students = query_db("SELECT COUNT(DISTINCT student_roll) as count FROM note_views", one=True)['count']
    total_notes = query_db("SELECT COUNT(*) as count FROM notes", one=True)['count']
    
    # Most active classrooms
    active_classrooms = query_db(
        """SELECT c.course, c.branch, c.semester, COUNT(nv.id) as views
           FROM note_views nv
           JOIN notes n ON nv.note_id = n.id
           JOIN classrooms c ON n.classroom_id = c.id
           GROUP BY c.id, c.course, c.branch, c.semester
           ORDER BY views DESC
           LIMIT 5"""
    )
    
    # Top viewed notes
    popular_notes = query_db(
        """SELECT n.subject, c.course, c.branch, c.semester, COUNT(nv.id) as views
           FROM notes n
           JOIN classrooms c ON n.classroom_id = c.id
           LEFT JOIN note_views nv ON n.id = nv.note_id
           GROUP BY n.id, n.subject, c.course, c.branch, c.semester
           ORDER BY views DESC
           LIMIT 5"""
    )
    
    return jsonify({
        "success": True,
        "analytics": {
            "total_views": total_views,
            "active_students": active_students,
            "total_notes": total_notes,
            "active_classrooms": active_classrooms,
            "popular_notes": popular_notes
        }
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(debug=True, host='0.0.0.0', port=port)
