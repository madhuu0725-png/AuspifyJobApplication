# JobConnect — Modern Enterprise Job Portal

A full-featured, responsive web platform connecting job seekers with visionary employers, featuring live application tracking, candidate pipeline management, rich multi-parameter search & filtering, and a comprehensive administration center.

---

## 🌟 Key Features

### 1. User Dashboards
- **Candidate Hub (`/seeker/dashboard`)**:
  - Application progress tracker with visual 5-stage milestone stepper (`Applied` → `Reviewing` → `Shortlisted` → `Interview` → `Accepted`).
  - Employer feedback and interview notes displayed directly in the candidate tracker.
  - Bookmarked / Saved jobs tab with quick apply actions.
  - Real-time activity notifications stream (application stage changes, alerts).
  - Candidate profile & resume manager (`/seeker/profile`).
- **Employer Hub (`/employer/dashboard`)**:
  - Overview metrics: Active jobs, Total applicants, Candidates in interview, All-time postings.
  - Live job postings management (`/employer/jobs`): edit, close/reopen, delete.
  - Candidate pipeline management (`/employer/applications`): filter by job or stage, preview candidate resumes, update status, and write candidate interview notes.
  - Company branding & profile manager (`/employer/company-profile`).
- **Admin Management Center (`/admin/dashboard`)**:
  - Platform KPIs: Total users (seekers vs employers), active jobs, total applications, confirmed hires.
  - User accounts governance: activate or suspend accounts, delete accounts.
  - Job moderation: mark as featured, toggle status, remove listings.
  - Taxonomy & Categories manager: add new industry categories with custom icons and accent colors.
  - Global applications audit stream.

### 2. Job Posting Functionality
- Employers can post detailed job openings (`/employer/jobs/new`) with:
  - Role title, industry category, job type (`Full-time`, `Part-time`, `Remote`, `Contract`, `Internship`).
  - Experience level (`Entry Level`, `Mid Level`, `Senior Level`, `Lead / Staff`).
  - Location and remote-eligible toggle.
  - Salary range (min - max) and currency.
  - Application deadline and publishing status (`Active`, `Draft`, `Closed`).
  - Formatted description, bulleted requirements, responsibilities, and benefits.

### 3. Job Application Workflows
- Comprehensive job details page (`/jobs/<id>`) with company profile, salary highlights, and similar opportunities.
- **1-Click Apply Modal**:
  - Automatically loads candidate's saved resume or allows uploading a new PDF/DOCX resume.
  - Cover note to hiring manager, portfolio / GitHub URL, contact details.
  - Prevents duplicate applications and sends real-time notifications to the employer.
- **Candidate Pipeline for Employers**:
  - Status updates (`Applied`, `Reviewing`, `Shortlisted`, `Interview`, `Accepted`, `Rejected`).
  - Secure resume viewing (`/uploads/resumes/<filename>`).
  - Candidate feedback / interview notes.
  - Candidates receive instant notification updates in their hub.

### 4. Search and Filtering Features
- Full catalog search (`/jobs`):
  - Keyword search across titles, descriptions, requirements, and company names.
  - Industry categories filter.
  - Job type radio filter.
  - Experience level filter.
  - Remote-only filter toggle.
  - Minimum annual salary filter ($60k+, $100k+, $140k+, $180k+).
  - Multi-criteria sorting: `Newest First`, `Highest Salary`, `Most Popular`.
  - Save / bookmark jobs with instant AJAX toggle.

### 5. Admin Management Features
- System-wide user moderation (Seekers, Employers, Admins).
- Moderation of all job postings and home page featured placements.
- Dynamic category creation and maintenance.
- Global application oversight.

---

## 🚀 Quick Demo Accounts

A single-click **Demo Role Switcher bar** is available at the very top of every page for instant evaluation:

| Role | Demo Account | Email | Password |
|---|---|---|---|
| **Candidate** | Alex Morgan (Senior Full-Stack) | `seeker@jobportal.com` | `seeker123` |
| **Employer** | Sarah Jenkins (Nexus Labs) | `employer@nexus.io` | `employer123` |
| **Admin** | System Administrator | `admin@jobportal.com` | `admin123` |

---

## 💻 Tech Stack
- **Backend**: Python 3.13, Flask 3.1, SQLite 3
- **Frontend**: Vanilla CSS Design System (`style.css`), Vanilla JavaScript (`main.js`), Lucide Vector Icons
- **Typography**: Google Fonts (*Plus Jakarta Sans*, *Outfit*)
- **Document Handling**: ReportLab for realistic demo PDF resumes

---

## 🏃‍♂️ How to Run Locally

1. **Install dependencies** (if not already installed):
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize database & demo resumes**:
   ```bash
   python database.py
   python generate_sample_resumes.py
   ```

3. **Start the application**:
   ```bash
   python app.py
   ```
   Open your browser and navigate to:
   ```
   http://127.0.0.1:5080
   ```

4. **Run Test Suites**:
   ```bash
   python test_portal.py
   python verify_all_workflows.py
   ```
