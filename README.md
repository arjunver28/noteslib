# Notes Library — Shobhit University Gangoh

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0%2B-black?logo=flask&logoColor=white)
![Database](https://img.shields.io/badge/Database-MariaDB%20%7C%20MySQL-003545?logo=mariadb&logoColor=white)
![WSGI](https://img.shields.io/badge/WSGI-Gunicorn-green?logo=gunicorn&logoColor=white)
![UI](https://img.shields.io/badge/UI-Bootstrap%205%20%7C%20Glassmorphism-purple?logo=bootstrap&logoColor=white)
![Platform](https://img.shields.io/badge/Deployment-ClearOS%207%20%7C%20CentOS%207%20%7C%20Linux-orange?logo=linux&logoColor=white)
![License](https://img.shields.io/badge/License-Academic%20Use-lightgrey)

**A secure, modern, and lightweight digital academic resource-sharing platform designed for Shobhit University Gangoh.**

*Enabling verified students, faculty administrators, and university superusers to organize, share, and access unit-wise curriculum notes with role-based access control, analytics tracking, and automated semester management.*

---

[Key Features](#-key-features) • [Tech Stack](#-tech-stack--architecture) • [Repository Structure](#-repository-structure) • [Local Development](#-local-development-setup) • [Production Deployment](#-production-deployment-clearos-7--centos-7) • [Security & Compatibility](#-security--compatibility-hardening) • [Default Credentials](#-default-credentials)

---

</div>

## 📖 Overview

**Notes Library** is a specialized academic repository built to centralize lecture notes, assignments, and study materials across diverse degree programs (B.Tech, BCA, MCA, B.Sc, Diploma, etc.).

Unlike generic cloud storage links, this platform enforces strict **academic classroom isolation**:
* Students only see curated notes uploaded for their verified Course, Branch, and Semester.
* Registrations are automatically verified against an internal official university student roster (1,063+ student records).
* Faculty administrators manage approvals, note uploads, and engagement analytics.
* Root superusers oversee department creation, classroom lifecycles, and automated semester progression.

---

## 🚀 Key Features

### 👨‍🎓 1. Student Portal
* **Verified Registration:** Seamless student signup with instant validation against the official university roster (`cslist.json`).
* **Classroom-Locked Feeds:** Eliminates clutter; students only access verified academic notes matching their enrolled semester and curriculum.
* **Subject & Favourites System:** Dynamic subject pills for instant filtering, plus a persistent personal bookmarking ("Favourites") tab.
* **In-Browser PDF Viewer & Direct Links:** One-click preview with shareable links for peer collaboration.
* **Clean Download Experience:** Instant PDF retrieval with tracked view counters.

### 🛡️ 2. Faculty Admin Dashboard
* **Structured Note Upload Wizard:** Tag notes by Subject, Unit (Unit 1 to 5+), Topic, and contributing student roll number or faculty name.
* **Student Verification Desk:** Approve or reject pending student registrations within the assigned classroom.
* **Student Roster Management:** View all enrolled students, inspect active status, or issue one-click password resets.
* **Engagement Analytics:** Real-time metrics on total note views, active student readers, and most popular study resources.

### ⚙️ 3. Superuser Console (Root Control)
* **Classroom Lifecycle:** Create and configure classrooms mapped to course, branch, and maximum semester limits.
* **Admin Provisioning:** Generate faculty administrator credentials and assign departmental management scopes.
* **Automated Semester Shift ("Danger Zone"):**
  * One-click mass student promotion to the subsequent semester.
  * Catch-back reconciliation for odd/even semester transitions.
  * Automatic graduation cleanup archiving final-year students.
* **Curriculum Configuration:** Define course durations, authorized specializations, and departmental branches.

### 📱 4. Universal Glassmorphic UI/UX
* **320px to 4K Responsive:** Fully responsive layout with fluid scaling (`clamp()`), safe margins, and touch-optimized components.
* **Kinetic Navigation:** Horizontally scrollable touch tabs, sticky responsive headers, and view-safe modals with independent internal scrolling.
* **Accessibility Compliant:** Minimum 44px touch targets across mobile, tablet, and desktop viewports.

---

## 🛠️ Tech Stack & Architecture

| Layer | Technology | Details |
| :--- | :--- | :--- |
| **Backend** | Python 3.8+ / Flask 3.0+ | Lightweight RESTful routing and server-side template rendering |
| **WSGI Engine** | Gunicorn | High-performance multi-worker production WSGI server |
| **Database** | MariaDB / MySQL | Relational storage with indexing on roll numbers and classroom IDs |
| **DB Driver** | **PyMySQL** + **DBUtils** | 100% pure-Python database driver with thread-safe connection pooling |
| **Frontend** | Bootstrap 5, Bootstrap Icons, Custom CSS | Modern translucent glassmorphic interface with CSS variables |
| **Student Roster** | Pure JSON (`cslist.json`) | Ultra-fast 34 KB pre-parsed roster parsed from `cslist.xlsx` via `cslist.py` |
| **Target Host** | ClearOS 7 / CentOS 7 / RHEL 7 | Compatible with legacy enterprise kernels (`glibc 2.17`, `OpenSSL 1.0.2k`) |

---

## 📂 Repository Structure

```text
noteslib/
├── app.py                 # Core Flask app (authentication, route controllers, REST APIs)
├── db.py                  # Database connection pool manager (PyMySQL with fallback)
├── db_setup.py            # Automatic schema migration & default superuser seeder
├── cslist.py              # XLSX -> JSON converter & normalizer utility
├── cslist.json            # Fast, pre-parsed 34 KB student roster (1,063 records)
├── cslist.xlsx            # Master university student roster spreadsheet
├── wsgi.py                # WSGI entrypoint for Gunicorn production deployment
├── requirements.txt       # Capped dependency manifest (guaranteed Python 3.8 compatibility)
├── deploy_clearos.sh      # 1-command automated deployment script for ClearOS / CentOS
├── noteslib.service       # Systemd production unit file template
├── static/
│   ├── css/
│   │   └── style.css      # Core responsive glassmorphic stylesheet (320px to 4K)
│   └── uploads/           # Storage directory for uploaded PDF notes
└── templates/
    ├── base.html          # Master HTML layout with fluid navbar & responsive container
    ├── login.html         # Split-card unified login & student registration portal
    ├── student.html       # Student dashboard with notes grid, filters, and favourites
    ├── admin.html         # Faculty dashboard with approvals, roster, & analytics
    ├── superuser.html     # Superuser console with classroom setup & semester shifts
    └── login_required.html# Locked resource authentication modal
```

---

## ⚡ Local Development Setup

### Prerequisites
* Python 3.8 or higher installed
* MySQL 5.7+ or MariaDB 10.2+ installed and running

### 1. Clone & Navigate to Repository
```bash
git clone https://github.com/your-username/noteslib.git
cd noteslib
```

### 2. Create and Activate a Virtual Environment
```bash
# Linux / macOS:
python3 -m venv venv
source venv/bin/activate

# Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Required Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Database and Run Migrations
Make sure your MySQL / MariaDB service is running:
```bash
# Linux / macOS:
export DB_HOST="localhost"
export DB_USER="root"
export DB_PASSWORD="MySQL@123"
export DB_NAME="notes_library"

python db_setup.py
```
*(On Windows PowerShell, use `$env:DB_PASSWORD="MySQL@123"` before running `python db_setup.py`)*

### 5. Launch Development Server
```bash
python app.py
```
Open your browser and navigate to: **`http://localhost:3000`**

---

## 🌐 Production Deployment (ClearOS 7 / CentOS 7)

This codebase has been specifically designed to deploy seamlessly on enterprise servers such as **ClearOS 7** (CentOS 7 / RHEL 7 base) with legacy constraints:

### Option A: Automated 1-Script Deployment
```bash
cd /var/www/23014168025/noteslib
chmod +x deploy_clearos.sh
./deploy_clearos.sh
```

### Option B: Step-by-Step Manual Deployment

1. **Verify MariaDB service is active:**
   ```bash
   systemctl enable mariadb
   systemctl start mariadb
   ```

2. **Initialize Python 3.8 virtual environment:**
   ```bash
   cd /var/www/23014168025/noteslib
   python3.8 -m venv venv
   source venv/bin/activate
   pip install --upgrade "pip<24.1" "setuptools<69.0.0"
   pip install -r requirements.txt
   ```

3. **Run database setup:**
   ```bash
   export DB_PASSWORD="MySQL@123"
   python db_setup.py
   ```

4. **Install and start the Systemd service:**
   ```bash
   cp noteslib.service /etc/systemd/system/
   systemctl daemon-reload
   systemctl enable noteslib
   systemctl start noteslib
   systemctl status noteslib
   ```

5. **Open firewall port (ClearOS / CentOS):**
   ```bash
   firewall-cmd --permanent --add-port=3000/tcp
   firewall-cmd --reload
   ```

6. **(Optional) Standard Port 80 Forwarding:**
   ```bash
   # Allows accessing http://<server-ip>/ without typing :3000
   iptables -t nat -I PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 3000
   iptables -I INPUT -p tcp --dport 80 -j ACCEPT
   ```

---

## 🛡️ Security & Compatibility Hardening

* **OpenSSL 1.0.2k Fix (`scrypt` attribute fallback):**
  Legacy OpenSSL builds on CentOS 7 lack native hardware `scrypt` hashing support. Password generation is explicitly set to use standard `pbkdf2:sha256`, preventing fatal HTTP 500 crashes during administrator or student creation.
* **Binary Wheel Immunity (`glibc 2.17`):**
  C-based MySQL drivers frequently fail to build or link on CentOS 7 due to `glibc` incompatibilities. `noteslib` utilizes **PyMySQL** (pure Python) backed by **DBUtils** connection pooling for zero-compilation stability.
* **Role-Based Session Guard:**
  Server-side validation verifies session identities before servicing routes (`@student_required`, `@admin_required`, `@superuser_required`).
* **Safe Upload Handling:**
  Files uploaded are checked against an extension whitelist (`.pdf`) and stored under sanitized filesystem naming conventions.

---

## ⚙️ Environment Configuration

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `PORT` | `3000` | Port for Flask or Gunicorn to bind |
| `DB_HOST` | `localhost` | MySQL/MariaDB database host |
| `DB_PORT` | `3306` | MySQL/MariaDB port |
| `DB_USER` | `root` | Database username |
| `DB_PASSWORD` | `MySQL@123` | Database user password |
| `DB_NAME` | `notes_library` | Database schema name |

---

## 🔑 Default Credentials

| Portal | Username / Identifier | Default Password | Role Details |
| :--- | :--- | :--- | :--- |
| **Superuser Console** | `superuser` | `superuser123` | Root administrator with total platform control |
| **Student Roster Sample** | `24012900001` | *Set during registration* | Verified student roll from `cslist.json` (AADITYA RAJPUT) |

> 💡 **Tip:** Change default superuser passwords immediately after initial deployment via the Superuser Console or database console.

---

## 📋 Student Roster Management

To update the student roster when a new academic session begins:
1. Place the updated Excel sheet as `cslist.xlsx` in the project root.
2. Run the converter:
   ```bash
   python cslist.py
   ```
3. The script sanitizes roll numbers, extracts student names, and generates an updated `cslist.json` without any server downtime.
4. Restart the service to refresh the cached roster:
   ```bash
   systemctl restart noteslib
   ```

---

## 🔧 Service Management Cheat Sheet

```bash
# Check if application is running
systemctl status noteslib

# Follow live server access and error logs
journalctl -u noteslib -f

# Restart application
systemctl restart noteslib

# Stop application
systemctl stop noteslib
```

---

## 📜 License & Copyright

Designed and developed for **Shobhit University Gangoh**.

* **Motto:** *Tejasvi Navadhitamastu* (May our learning be brilliant and effective)
* **Copyright:** &copy; 2026 Shobhit University, Gangoh. All Rights Reserved.
