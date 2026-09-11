# NotesLib — Shobhit University Gangoh

<div align="center">

![Platform](https://img.shields.io/badge/Platform-Android%20%7C%20Web%20%7C%20Linux-blue?logo=android&logoColor=white)
![Kotlin](https://img.shields.io/badge/Kotlin-1.9%2B-purple?logo=kotlin&logoColor=white)
![Jetpack Compose](https://img.shields.io/badge/UI-Jetpack%20Compose%20%7C%20Material%203-4285F4?logo=jetpackcompose&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0%2B-black?logo=flask&logoColor=white)
![Database](https://img.shields.io/badge/Database-SQLite%20(WAL%20Mode)-003B57?logo=sqlite&logoColor=white)
![Gradle](https://img.shields.io/badge/Build-Gradle%208.2-02303A?logo=gradle&logoColor=white)
![Deployment](https://img.shields.io/badge/Deployment-ClearOS%207%20%7C%20CentOS%207-orange?logo=linux&logoColor=white)
![License](https://img.shields.io/badge/License-Academic%20Use-lightgrey)

**A complete, modern digital academic repository and notes-sharing ecosystem for Shobhit University Gangoh.**

*Featuring native Android applications for Students and Faculty Administrators built with Jetpack Compose, a full-featured Flask web platform, role-based access control, unit-wise curriculum distribution, and an automated student verification roster.*

---

[Key Highlights](#-key-highlights) • [Repository Structure](#-repository-structure) • [Mobile Apps (Android)](#-mobile-apps-android) • [Web Platform & Backend](#-web-platform--backend) • [Setup & Installation](#-setup--installation) • [API & Architecture](#-api--architecture) • [Default Credentials](#-default-credentials) • [Deployment](#-production-deployment-clearos--centos)

---

</div>

## 📖 Overview

**NotesLib** is an integrated academic resource system designed to replace fragmented cloud storage links with a structured, classroom-isolated learning portal. The ecosystem consists of:

1. **Native Android Applications:**
   * **NotesLib - Student**: Curriculum-locked notes explorer, unit filters (All, 1–5), instant search, personal favourites/bookmarks, and in-app PDF viewing.
   * **NotesLib - Admin**: Faculty portal with note upload wizard (subject dropdowns & custom units), pending student approval desk, student roster management, and view analytics.
2. **Web Portal & REST Backend:**
   * Server-side rendered web portal with a responsive glassmorphic UI.
   * Centralized REST API engine powering both mobile clients with persistent session handling.
   * Embedded high-concurrency SQLite database with Write-Ahead Logging (WAL).
   * Automated student roster verification against 1,063+ university records (`cslist.json`).

---

## 🚀 Key Highlights

### 👨‍🎓 1. Student Features
* **Roster-Verified Signup:** Self-registration strictly validated against official student roll numbers (`cslist.json`).
* **Classroom Isolation:** Students only access notes specifically approved for their Course, Branch, and Semester.
* **Unit Filtering & Search:** Filter resources by **All Units** or **Units 1 to 5**, coupled with live title/topic search.
* **Persistent Favourites:** One-tap bookmarking to quickly revisit important exam notes.
* **In-App PDF Viewer:** Streamlined preview and download with tracked read counters.
* **Persistent Session:** Automatic silent background re-authentication via disk-backed cookie storage.

### 🛡️ 2. Faculty Administrator Features
* **Subject-Locked Note Uploads:** Subject dropdown menus strictly populated with subjects under the admin's assigned semester (prevents typographical errors).
* **Flexible Unit Categorization:** Full support for standard curriculum units (1–5) plus an **"Others"** category for syllabi, question banks, or assignment briefs.
* **Student Verification Desk:** Review, approve, or reject new student registrations in real time.
* **Classroom Roster Control:** Monitor enrolled students, view activity status, and issue password resets.
* **Live Engagement Metrics:** Track view counts, download statistics, and top study resources.

### 🎨 3. Design & Android Native Experience
* **100% Jetpack Compose & Material 3:** Modern, fluid animations, bottom navigation bars, and glassmorphism-inspired cards.
* **Aspect-Ratio Preserved Logo:** University brand header with mathematically exact 3.69:1 ratio.
* **Custom Adaptive Launcher Icon:** Official Shobhit University gold crest centered on signature `#063D2B` academic green, optimized with a 58% safe zone to prevent clipping across Pixel, Samsung OneUI, and MIUI launchers.

---

## 📂 Repository Structure

```text
noteslib/
│
├── 📱 ANDROID APPLICATIONS
│   ├── NotesLib - Student/        # Standalone Android Studio project for Student App
│   ├── NotesLib - Admin/          # Standalone Android Studio project for Admin App
│   ├── android/                   # Unified multi-flavor Gradle project (studentDebug, adminDebug)
│   ├── appicon.png                # Official app icon asset (#063D2B green crest)
│   └── app.logo.png               # Official transparent university crest asset
│
├── 🌐 FLASK BACKEND & WEB PORTAL
│   ├── app.py                     # Core Flask application (REST API & Web routes)
│   ├── db.py                      # SQLite database manager (WAL mode, timeouts, helpers)
│   ├── db_setup.py                # Schema initialization & superuser seeder
│   ├── cslist.json                # Pre-parsed student roster (1,063 records)
│   ├── cslist.xlsx                # Master student roster spreadsheet
│   ├── cslist.py                  # XLSX -> JSON roster converter utility
│   ├── migrate_mysql_to_sqlite.py # Legacy MySQL/MariaDB to SQLite migration tool
│   ├── wsgi.py                    # Gunicorn production WSGI entrypoint
│   ├── requirements.txt           # Python dependency manifest
│   ├── notes_library.db           # SQLite database file
│   │
│   ├── static/                    # Web static assets (CSS, JS, images)
│   │   └── css/style.css          # Responsive glassmorphic stylesheet (320px to 4K)
│   ├── templates/                 # Server-side HTML templates (Jinja2)
│   │   ├── base.html              # Layout shell with responsive navbar
│   │   ├── login.html             # Split-card unified login & registration
│   │   ├── student.html           # Student web dashboard
│   │   ├── admin.html             # Faculty web dashboard
│   │   └── superuser.html         # Superuser control panel
│   └── uploads/                   # Local storage directory for uploaded PDF notes
│
└── 🚀 CONFIGURATION & DEPLOYMENT
    ├── .gitignore                 # Comprehensive Git ignore rules (builds, caches, SDKs)
    ├── deploy_clearos.sh          # Automated 1-command deployment script for ClearOS/CentOS
    ├── noteslib.service           # Systemd daemon service configuration
    └── README.md                  # Project documentation
