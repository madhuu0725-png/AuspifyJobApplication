import os
import sqlite3
import uuid
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, g, jsonify, send_from_directory, abort
)
from database import get_db_connection, hash_password, init_db, seed_db

app = Flask(__name__)
app.secret_key = 'jobconnect-secret-key-super-secure-production-ready'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'resumes')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database on start
init_db()
seed_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# -------------------------------------------------------------
# Authentication & Access Decorators
# -------------------------------------------------------------
def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user

@app.before_request
def load_logged_in_user():
    g.user = get_current_user()

@app.context_processor
def inject_global_data():
    conn = get_db_connection()
    categories = conn.execute("SELECT * FROM categories ORDER BY name ASC").fetchall()
    unread_notifications = 0
    company = None
    if g.user:
        unread_notifications = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
            (g.user['id'],)
        ).fetchone()[0]
        if g.user['role'] == 'employer':
            company = conn.execute("SELECT * FROM companies WHERE employer_id = ?", (g.user['id'],)).fetchone()
    conn.close()
    return {
        'current_user': g.user,
        'categories_global': categories,
        'unread_notifications': unread_notifications,
        'employer_company': company,
        'now_year': datetime.now().year
    }

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if g.user is None:
                flash('Please log in to continue.', 'warning')
                return redirect(url_for('login', next=request.url))
            if g.user['role'] not in roles:
                flash(f'Access restricted. Requires {", ".join(roles)} privileges.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# -------------------------------------------------------------
# Demo Quick Switcher (Convenient Role Switching)
# -------------------------------------------------------------
@app.route('/demo-login/<role>')
def demo_login(role):
    conn = get_db_connection()
    user = None
    if role == 'seeker':
        user = conn.execute("SELECT * FROM users WHERE email = 'seeker@jobportal.com'").fetchone()
    elif role == 'employer':
        user = conn.execute("SELECT * FROM users WHERE email = 'employer@nexus.io'").fetchone()
    elif role == 'admin':
        user = conn.execute("SELECT * FROM users WHERE email = 'admin@jobportal.com'").fetchone()
    conn.close()

    if user:
        session.clear()
        session['user_id'] = user['id']
        session['role'] = user['role']
        session['user_name'] = user['name']
        flash(f'Switched to Demo Account: {user["name"]} ({user["role"].capitalize()})', 'success')
        if role == 'seeker':
            return redirect(url_for('seeker_dashboard'))
        elif role == 'employer':
            return redirect(url_for('employer_dashboard'))
        elif role == 'admin':
            return redirect(url_for('admin_dashboard'))
    flash('Demo user not found.', 'danger')
    return redirect(url_for('index'))

# -------------------------------------------------------------
# Home & Public Pages
# -------------------------------------------------------------
@app.route('/')
def index():
    conn = get_db_connection()
    # Featured Jobs
    featured_jobs = conn.execute('''
        SELECT j.*, c.name as company_name, c.logo_icon, cat.name as category_name
        FROM jobs j
        JOIN companies c ON j.company_id = c.id
        JOIN categories cat ON j.category_id = cat.id
        WHERE j.status = 'active' AND j.is_featured = 1
        ORDER BY j.created_at DESC LIMIT 6
    ''').fetchall()

    # Recent Jobs
    recent_jobs = conn.execute('''
        SELECT j.*, c.name as company_name, c.logo_icon, cat.name as category_name
        FROM jobs j
        JOIN companies c ON j.company_id = c.id
        JOIN categories cat ON j.category_id = cat.id
        WHERE j.status = 'active'
        ORDER BY j.created_at DESC LIMIT 6
    ''').fetchall()

    # Category job counts
    category_counts = conn.execute('''
        SELECT cat.id, cat.name, cat.icon, cat.color, cat.slug, COUNT(j.id) as job_count
        FROM categories cat
        LEFT JOIN jobs j ON cat.id = j.category_id AND j.status = 'active'
        GROUP BY cat.id
        ORDER BY job_count DESC
    ''').fetchall()

    # Stats
    total_jobs = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'active'").fetchone()[0]
    total_companies = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    total_candidates = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'seeker'").fetchone()[0]
    total_applications = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]

    # Check saved jobs for current seeker
    saved_job_ids = set()
    if g.user and g.user['role'] == 'seeker':
        saved = conn.execute("SELECT job_id FROM saved_jobs WHERE seeker_id = ?", (g.user['id'],)).fetchall()
        saved_job_ids = {row['job_id'] for row in saved}

    conn.close()
    return render_template(
        'index.html',
        featured_jobs=featured_jobs,
        recent_jobs=recent_jobs,
        category_counts=category_counts,
        total_jobs=total_jobs,
        total_companies=total_companies,
        total_candidates=total_candidates,
        total_applications=total_applications,
        saved_job_ids=saved_job_ids
    )

# -------------------------------------------------------------
# Step 4: Search & Filtering Features
# -------------------------------------------------------------
@app.route('/jobs')
def job_listings():
    conn = get_db_connection()
    q = request.args.get('q', '').strip()
    category_id = request.args.get('category', '').strip()
    job_type = request.args.get('type', '').strip()
    experience = request.args.get('experience', '').strip()
    location = request.args.get('location', '').strip()
    remote_only = request.args.get('remote', '').strip()
    min_salary = request.args.get('min_salary', '').strip()
    sort_by = request.args.get('sort', 'newest').strip()

    sql = '''
        SELECT j.*, c.name as company_name, c.logo_icon, cat.name as category_name
        FROM jobs j
        JOIN companies c ON j.company_id = c.id
        JOIN categories cat ON j.category_id = cat.id
        WHERE j.status = 'active'
    '''
    params = []

    if q:
        sql += ''' AND (
            j.title LIKE ? OR 
            j.description LIKE ? OR 
            j.requirements LIKE ? OR 
            c.name LIKE ?
        )'''
        wildcard = f'%{q}%'
        params.extend([wildcard, wildcard, wildcard, wildcard])

    if category_id and category_id.isdigit():
        sql += " AND j.category_id = ?"
        params.append(int(category_id))

    if job_type:
        sql += " AND j.job_type = ?"
        params.append(job_type)

    if experience:
        sql += " AND j.experience_level = ?"
        params.append(experience)

    if location:
        sql += " AND (j.location LIKE ? OR (j.is_remote = 1 AND ? = 'remote'))"
        params.extend([f'%{location}%', location.lower()])

    if remote_only == '1':
        sql += " AND j.is_remote = 1"

    if min_salary and min_salary.isdigit():
        sql += " AND j.salary_max >= ?"
        params.append(int(min_salary))

    if sort_by == 'salary':
        sql += " ORDER BY j.salary_max DESC, j.created_at DESC"
    elif sort_by == 'popular':
        sql += " ORDER BY j.views_count DESC, j.created_at DESC"
    else:
        sql += " ORDER BY j.is_featured DESC, j.created_at DESC"

    jobs = conn.execute(sql, params).fetchall()

    categories = conn.execute("SELECT * FROM categories ORDER BY name ASC").fetchall()

    saved_job_ids = set()
    if g.user and g.user['role'] == 'seeker':
        saved = conn.execute("SELECT job_id FROM saved_jobs WHERE seeker_id = ?", (g.user['id'],)).fetchall()
        saved_job_ids = {row['job_id'] for row in saved}

    conn.close()

    return render_template(
        'jobs.html',
        jobs=jobs,
        categories=categories,
        filters={
            'q': q,
            'category': category_id,
            'type': job_type,
            'experience': experience,
            'location': location,
            'remote': remote_only,
            'min_salary': min_salary,
            'sort': sort_by
        },
        saved_job_ids=saved_job_ids,
        total_results=len(jobs)
    )

# -------------------------------------------------------------
# Job Details View
# -------------------------------------------------------------
@app.route('/jobs/<int:job_id>')
def job_detail(job_id):
    conn = get_db_connection()

    # Increment view count
    conn.execute("UPDATE jobs SET views_count = views_count + 1 WHERE id = ?", (job_id,))
    conn.commit()

    job = conn.execute('''
        SELECT j.*, c.name as company_name, c.tagline as company_tagline, 
               c.logo_icon, c.website as company_website, c.description as company_description,
               c.size as company_size, c.industry as company_industry,
               cat.name as category_name, cat.color as category_color,
               u.email as employer_email, u.name as employer_name
        FROM jobs j
        JOIN companies c ON j.company_id = c.id
        JOIN categories cat ON j.category_id = cat.id
        JOIN users u ON j.employer_id = u.id
        WHERE j.id = ?
    ''', (job_id,)).fetchone()

    if not job:
        conn.close()
        abort(404)

    # Similar jobs
    similar_jobs = conn.execute('''
        SELECT j.*, c.name as company_name, c.logo_icon, cat.name as category_name
        FROM jobs j
        JOIN companies c ON j.company_id = c.id
        JOIN categories cat ON j.category_id = cat.id
        WHERE j.category_id = ? AND j.id != ? AND j.status = 'active'
        ORDER BY j.created_at DESC LIMIT 3
    ''', (job['category_id'], job_id)).fetchall()

    # Check if seeker has applied
    has_applied = False
    existing_application = None
    is_saved = False
    if g.user and g.user['role'] == 'seeker':
        existing_application = conn.execute(
            "SELECT * FROM applications WHERE job_id = ? AND seeker_id = ?",
            (job_id, g.user['id'])
        ).fetchone()
        has_applied = existing_application is not None

        saved = conn.execute(
            "SELECT id FROM saved_jobs WHERE seeker_id = ? AND job_id = ?",
            (g.user['id'], job_id)
        ).fetchone()
        is_saved = saved is not None

    conn.close()

    return render_template(
        'job_detail.html',
        job=job,
        similar_jobs=similar_jobs,
        has_applied=has_applied,
        application=existing_application,
        is_saved=is_saved
    )

# -------------------------------------------------------------
# Step 3: Job Application Workflows
# -------------------------------------------------------------
@app.route('/jobs/<int:job_id>/apply', methods=['POST'])
@login_required
@role_required('seeker')
def apply_job(job_id):
    conn = get_db_connection()
    job = conn.execute("SELECT * FROM jobs WHERE id = ? AND status = 'active'", (job_id,)).fetchone()
    if not job:
        conn.close()
        flash('This job posting is no longer accepting applications.', 'danger')
        return redirect(url_for('job_listings'))

    # Check if already applied
    existing = conn.execute(
        "SELECT id FROM applications WHERE job_id = ? AND seeker_id = ?",
        (job_id, g.user['id'])
    ).fetchone()
    if existing:
        conn.close()
        flash('You have already applied for this position.', 'info')
        return redirect(url_for('job_detail', job_id=job_id))

    full_name = request.form.get('full_name', g.user['name']).strip()
    email = request.form.get('email', g.user['email']).strip()
    phone = request.form.get('phone', g.user['phone'] or '').strip()
    portfolio_url = request.form.get('portfolio_url', '').strip()
    cover_letter = request.form.get('cover_letter', '').strip()

    resume_source = request.form.get('resume_source', 'profile')
    resume_filename = None
    resume_original_name = None

    if resume_source == 'profile' and g.user['resume_filename']:
        resume_filename = g.user['resume_filename']
        resume_original_name = g.user['resume_original_name'] or 'Saved_Resume.pdf'
    else:
        # Check uploaded file
        file = request.files.get('resume_file')
        if file and file.filename != '' and allowed_file(file.filename):
            orig_name = secure_filename(file.filename)
            unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}_{orig_name}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            file.save(file_path)
            resume_filename = unique_name
            resume_original_name = orig_name
        elif g.user['resume_filename']:
            resume_filename = g.user['resume_filename']
            resume_original_name = g.user['resume_original_name']
        else:
            conn.close()
            flash('Please upload a resume (PDF/DOCX) or save one in your profile.', 'danger')
            return redirect(url_for('job_detail', job_id=job_id))

    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO applications (
            job_id, seeker_id, full_name, email, phone, portfolio_url,
            cover_letter, resume_filename, resume_original_name, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'applied')
    ''', (job_id, g.user['id'], full_name, email, phone, portfolio_url, cover_letter, resume_filename, resume_original_name))

    # Notify employer
    cursor.execute('''
        INSERT INTO notifications (user_id, title, message, type, link)
        VALUES (?, ?, ?, 'info', '/employer/applications')
    ''', (
        job['employer_id'],
        'New Job Application Received',
        f'{full_name} applied for "{job["title"]}".'
    ))

    conn.commit()
    conn.close()

    flash('Application submitted successfully! Track your status on your dashboard.', 'success')
    return redirect(url_for('seeker_dashboard'))

@app.route('/jobs/<int:job_id>/toggle-save', methods=['POST'])
@login_required
@role_required('seeker')
def toggle_save_job(job_id):
    conn = get_db_connection()
    existing = conn.execute(
        "SELECT id FROM saved_jobs WHERE seeker_id = ? AND job_id = ?",
        (g.user['id'], job_id)
    ).fetchone()

    if existing:
        conn.execute("DELETE FROM saved_jobs WHERE id = ?", (existing['id'],))
        is_saved = False
        message = "Job removed from saved list."
    else:
        conn.execute(
            "INSERT INTO saved_jobs (seeker_id, job_id) VALUES (?, ?)",
            (g.user['id'], job_id)
        )
        is_saved = True
        message = "Job saved to your bookmarks."

    conn.commit()
    conn.close()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'success': True, 'saved': is_saved, 'message': message})

    flash(message, 'info')
    return redirect(request.referrer or url_for('job_detail', job_id=job_id))

# -------------------------------------------------------------
# Step 1: User Dashboards - Seeker Dashboard
# -------------------------------------------------------------
@app.route('/seeker/dashboard')
@login_required
@role_required('seeker')
def seeker_dashboard():
    conn = get_db_connection()

    # User's applications
    applications = conn.execute('''
        SELECT a.*, j.title as job_title, j.job_type, j.location as job_location,
               j.is_remote, j.salary_min, j.salary_max, j.salary_currency,
               c.name as company_name, c.logo_icon
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        JOIN companies c ON j.company_id = c.id
        WHERE a.seeker_id = ?
        ORDER BY a.applied_at DESC
    ''', (g.user['id'],)).fetchall()

    # User's saved jobs
    saved_jobs = conn.execute('''
        SELECT s.saved_at, j.*, c.name as company_name, c.logo_icon, cat.name as category_name
        FROM saved_jobs s
        JOIN jobs j ON s.job_id = j.id
        JOIN companies c ON j.company_id = c.id
        JOIN categories cat ON j.category_id = cat.id
        WHERE s.seeker_id = ?
        ORDER BY s.saved_at DESC
    ''', (g.user['id'],)).fetchall()

    # Notifications
    notifications = conn.execute('''
        SELECT * FROM notifications 
        WHERE user_id = ? 
        ORDER BY created_at DESC LIMIT 10
    ''', (g.user['id'],)).fetchall()

    # Mark notifications as read
    conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (g.user['id'],))
    conn.commit()

    # Metrics
    total_applied = len(applications)
    reviewing_count = sum(1 for a in applications if a['status'] in ('reviewing', 'shortlisted'))
    interviews_count = sum(1 for a in applications if a['status'] == 'interview')
    accepted_count = sum(1 for a in applications if a['status'] == 'accepted')

    conn.close()

    return render_template(
        'seeker/dashboard.html',
        applications=applications,
        saved_jobs=saved_jobs,
        notifications=notifications,
        total_applied=total_applied,
        reviewing_count=reviewing_count,
        interviews_count=interviews_count,
        accepted_count=accepted_count
    )

@app.route('/seeker/withdraw/<int:application_id>', methods=['POST'])
@login_required
@role_required('seeker')
def withdraw_application(application_id):
    conn = get_db_connection()
    app_record = conn.execute(
        "SELECT * FROM applications WHERE id = ? AND seeker_id = ?",
        (application_id, g.user['id'])
    ).fetchone()

    if not app_record:
        conn.close()
        flash('Application not found.', 'danger')
        return redirect(url_for('seeker_dashboard'))

    conn.execute("DELETE FROM applications WHERE id = ?", (application_id,))
    conn.commit()
    conn.close()

    flash('Application successfully withdrawn.', 'info')
    return redirect(url_for('seeker_dashboard'))

@app.route('/seeker/profile', methods=['GET', 'POST'])
@login_required
@role_required('seeker')
def seeker_profile():
    conn = get_db_connection()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        title = request.form.get('title', '').strip()
        phone = request.form.get('phone', '').strip()
        location = request.form.get('location', '').strip()
        bio = request.form.get('bio', '').strip()

        resume_filename = g.user['resume_filename']
        resume_original_name = g.user['resume_original_name']

        file = request.files.get('resume_file')
        if file and file.filename != '' and allowed_file(file.filename):
            orig_name = secure_filename(file.filename)
            unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}_{orig_name}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
            resume_filename = unique_name
            resume_original_name = orig_name

        conn.execute('''
            UPDATE users
            SET name = ?, title = ?, phone = ?, location = ?, bio = ?,
                resume_filename = ?, resume_original_name = ?
            WHERE id = ?
        ''', (name, title, phone, location, bio, resume_filename, resume_original_name, g.user['id']))
        conn.commit()
        conn.close()

        flash('Your profile and resume have been updated!', 'success')
        return redirect(url_for('seeker_profile'))

    user = conn.execute("SELECT * FROM users WHERE id = ?", (g.user['id'],)).fetchone()
    conn.close()
    return render_template('seeker/profile.html', user=user)

# -------------------------------------------------------------
# Step 1 & 2: Employer Dashboard & Job Posting Functionality
# -------------------------------------------------------------
@app.route('/employer/dashboard')
@login_required
@role_required('employer')
def employer_dashboard():
    conn = get_db_connection()
    company = conn.execute("SELECT * FROM companies WHERE employer_id = ?", (g.user['id'],)).fetchone()

    # Employer jobs with application count
    jobs = conn.execute('''
        SELECT j.*, cat.name as category_name,
               COUNT(a.id) as applicant_count,
               SUM(CASE WHEN a.status = 'interview' THEN 1 ELSE 0 END) as interview_count
        FROM jobs j
        JOIN categories cat ON j.category_id = cat.id
        LEFT JOIN applications a ON j.id = a.job_id
        WHERE j.employer_id = ?
        GROUP BY j.id
        ORDER BY j.created_at DESC
    ''', (g.user['id'],)).fetchall()

    # Recent candidates across all jobs
    recent_candidates = conn.execute('''
        SELECT a.*, j.title as job_title, u.avatar as seeker_avatar
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        JOIN users u ON a.seeker_id = u.id
        WHERE j.employer_id = ?
        ORDER BY a.applied_at DESC
        LIMIT 6
    ''', (g.user['id'],)).fetchall()

    # Metrics
    total_jobs = len(jobs)
    active_jobs = sum(1 for j in jobs if j['status'] == 'active')
    total_applicants = sum(j['applicant_count'] for j in jobs)
    candidates_in_interview = sum(j['interview_count'] for j in jobs)

    conn.close()

    return render_template(
        'employer/dashboard.html',
        company=company,
        jobs=jobs,
        recent_candidates=recent_candidates,
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        total_applicants=total_applicants,
        candidates_in_interview=candidates_in_interview
    )

@app.route('/employer/jobs')
@login_required
@role_required('employer')
def employer_manage_jobs():
    conn = get_db_connection()
    jobs = conn.execute('''
        SELECT j.*, cat.name as category_name,
               COUNT(a.id) as applicant_count
        FROM jobs j
        JOIN categories cat ON j.category_id = cat.id
        LEFT JOIN applications a ON j.id = a.job_id
        WHERE j.employer_id = ?
        GROUP BY j.id
        ORDER BY j.created_at DESC
    ''', (g.user['id'],)).fetchall()
    conn.close()
    return render_template('employer/manage_jobs.html', jobs=jobs)

@app.route('/employer/jobs/new', methods=['GET', 'POST'])
@login_required
@role_required('employer')
def employer_create_job():
    conn = get_db_connection()
    company = conn.execute("SELECT * FROM companies WHERE employer_id = ?", (g.user['id'],)).fetchone()
    if not company:
        # Auto create default company if missing
        conn.execute("INSERT INTO companies (employer_id, name) VALUES (?, ?)", (g.user['id'], f"{g.user['name']}'s Company"))
        conn.commit()
        company = conn.execute("SELECT * FROM companies WHERE employer_id = ?", (g.user['id'],)).fetchone()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category_id = request.form.get('category_id')
        job_type = request.form.get('job_type')
        experience_level = request.form.get('experience_level')
        location = request.form.get('location', '').strip()
        is_remote = 1 if request.form.get('is_remote') == 'on' else 0
        salary_min = request.form.get('salary_min') or None
        salary_max = request.form.get('salary_max') or None
        salary_currency = request.form.get('salary_currency', 'USD')
        description = request.form.get('description', '').strip()
        requirements = request.form.get('requirements', '').strip()
        responsibilities = request.form.get('responsibilities', '').strip()
        benefits = request.form.get('benefits', '').strip()
        status = request.form.get('status', 'active')
        is_featured = 1 if request.form.get('is_featured') == 'on' else 0
        deadline = request.form.get('deadline') or None

        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO jobs (
                employer_id, company_id, title, category_id, job_type, experience_level,
                location, is_remote, salary_min, salary_max, salary_currency,
                description, requirements, responsibilities, benefits,
                status, is_featured, deadline
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            g.user['id'], company['id'], title, category_id, job_type, experience_level,
            location, is_remote, salary_min, salary_max, salary_currency,
            description, requirements, responsibilities, benefits,
            status, is_featured, deadline
        ))
        conn.commit()
        conn.close()

        flash('Job posting published successfully!', 'success')
        return redirect(url_for('employer_dashboard'))

    categories = conn.execute("SELECT * FROM categories ORDER BY name ASC").fetchall()
    conn.close()
    return render_template('employer/post_job.html', categories=categories, job=None, action_title="Post New Job")

@app.route('/employer/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('employer')
def employer_edit_job(job_id):
    conn = get_db_connection()
    job = conn.execute("SELECT * FROM jobs WHERE id = ? AND employer_id = ?", (job_id, g.user['id'])).fetchone()
    if not job:
        conn.close()
        flash('Job not found or permission denied.', 'danger')
        return redirect(url_for('employer_dashboard'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category_id = request.form.get('category_id')
        job_type = request.form.get('job_type')
        experience_level = request.form.get('experience_level')
        location = request.form.get('location', '').strip()
        is_remote = 1 if request.form.get('is_remote') == 'on' else 0
        salary_min = request.form.get('salary_min') or None
        salary_max = request.form.get('salary_max') or None
        salary_currency = request.form.get('salary_currency', 'USD')
        description = request.form.get('description', '').strip()
        requirements = request.form.get('requirements', '').strip()
        responsibilities = request.form.get('responsibilities', '').strip()
        benefits = request.form.get('benefits', '').strip()
        status = request.form.get('status', 'active')
        is_featured = 1 if request.form.get('is_featured') == 'on' else 0
        deadline = request.form.get('deadline') or None

        conn.execute('''
            UPDATE jobs SET
                title = ?, category_id = ?, job_type = ?, experience_level = ?,
                location = ?, is_remote = ?, salary_min = ?, salary_max = ?,
                salary_currency = ?, description = ?, requirements = ?,
                responsibilities = ?, benefits = ?, status = ?, is_featured = ?, deadline = ?
            WHERE id = ? AND employer_id = ?
        ''', (
            title, category_id, job_type, experience_level,
            location, is_remote, salary_min, salary_max,
            salary_currency, description, requirements,
            responsibilities, benefits, status, is_featured, deadline,
            job_id, g.user['id']
        ))
        conn.commit()
        conn.close()

        flash('Job posting updated successfully.', 'success')
        return redirect(url_for('employer_dashboard'))

    categories = conn.execute("SELECT * FROM categories ORDER BY name ASC").fetchall()
    conn.close()
    return render_template('employer/post_job.html', categories=categories, job=job, action_title="Edit Job Posting")

@app.route('/employer/jobs/<int:job_id>/toggle-status', methods=['POST'])
@login_required
@role_required('employer')
def employer_toggle_job_status(job_id):
    conn = get_db_connection()
    job = conn.execute("SELECT status FROM jobs WHERE id = ? AND employer_id = ?", (job_id, g.user['id'])).fetchone()
    if job:
        new_status = 'closed' if job['status'] == 'active' else 'active'
        conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (new_status, job_id))
        conn.commit()
        flash(f'Job status changed to {new_status.capitalize()}.', 'info')
    conn.close()
    return redirect(request.referrer or url_for('employer_manage_jobs'))

@app.route('/employer/jobs/<int:job_id>/delete', methods=['POST'])
@login_required
@role_required('employer')
def employer_delete_job(job_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM jobs WHERE id = ? AND employer_id = ?", (job_id, g.user['id']))
    conn.commit()
    conn.close()
    flash('Job posting deleted.', 'info')
    return redirect(request.referrer or url_for('employer_manage_jobs'))

# -------------------------------------------------------------
# Employer Candidate & Applications Management
# -------------------------------------------------------------
@app.route('/employer/applications')
@login_required
@role_required('employer')
def employer_applications():
    conn = get_db_connection()
    filter_job_id = request.args.get('job_id', '')
    filter_status = request.args.get('status', '')

    # Employer jobs for dropdown filter
    employer_jobs = conn.execute(
        "SELECT id, title FROM jobs WHERE employer_id = ? ORDER BY title ASC",
        (g.user['id'],)
    ).fetchall()

    sql = '''
        SELECT a.*, j.title as job_title, j.location as job_location,
               u.avatar as seeker_avatar, u.title as seeker_headline
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        JOIN users u ON a.seeker_id = u.id
        WHERE j.employer_id = ?
    '''
    params = [g.user['id']]

    if filter_job_id and filter_job_id.isdigit():
        sql += " AND a.job_id = ?"
        params.append(int(filter_job_id))

    if filter_status:
        sql += " AND a.status = ?"
        params.append(filter_status)

    sql += " ORDER BY a.applied_at DESC"
    applications = conn.execute(sql, params).fetchall()

    conn.close()
    return render_template(
        'employer/applications.html',
        applications=applications,
        employer_jobs=employer_jobs,
        filter_job_id=filter_job_id,
        filter_status=filter_status
    )

@app.route('/employer/applications/<int:app_id>/status', methods=['POST'])
@login_required
@role_required('employer')
def update_application_status(app_id):
    new_status = request.form.get('status')
    employer_notes = request.form.get('employer_notes', '').strip()

    valid_statuses = ('applied', 'reviewing', 'shortlisted', 'interview', 'rejected', 'accepted')
    if new_status not in valid_statuses:
        flash('Invalid status provided.', 'danger')
        return redirect(url_for('employer_applications'))

    conn = get_db_connection()
    app_record = conn.execute('''
        SELECT a.*, j.title as job_title, c.name as company_name
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        JOIN companies c ON j.company_id = c.id
        WHERE a.id = ? AND j.employer_id = ?
    ''', (app_id, g.user['id'])).fetchone()

    if not app_record:
        conn.close()
        flash('Application not found or unauthorized.', 'danger')
        return redirect(url_for('employer_applications'))

    conn.execute('''
        UPDATE applications
        SET status = ?, employer_notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (new_status, employer_notes, app_id))

    # Send notification to Job Seeker
    conn.execute('''
        INSERT INTO notifications (user_id, title, message, type, link)
        VALUES (?, ?, ?, ?, '/seeker/dashboard')
    ''', (
        app_record['seeker_id'],
        f'Application Status: {new_status.capitalize()}',
        f"{app_record['company_name']} updated your application status for \"{app_record['job_title']}\" to {new_status.capitalize()}.",
        'success' if new_status in ('shortlisted', 'interview', 'accepted') else 'info'
    ))

    conn.commit()
    conn.close()

    flash(f"Candidate status updated to '{new_status.capitalize()}'. Seeker notified!", 'success')
    return redirect(request.referrer or url_for('employer_applications'))

@app.route('/employer/company-profile', methods=['GET', 'POST'])
@login_required
@role_required('employer')
def employer_company_profile():
    conn = get_db_connection()
    company = conn.execute("SELECT * FROM companies WHERE employer_id = ?", (g.user['id'],)).fetchone()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        tagline = request.form.get('tagline', '').strip()
        logo_icon = request.form.get('logo_icon', 'building-2')
        website = request.form.get('website', '').strip()
        industry = request.form.get('industry', '').strip()
        location = request.form.get('location', '').strip()
        size = request.form.get('size', '').strip()
        description = request.form.get('description', '').strip()

        if company:
            conn.execute('''
                UPDATE companies SET
                    name = ?, tagline = ?, logo_icon = ?, website = ?,
                    industry = ?, location = ?, size = ?, description = ?
                WHERE employer_id = ?
            ''', (name, tagline, logo_icon, website, industry, location, size, description, g.user['id']))
        else:
            conn.execute('''
                INSERT INTO companies (employer_id, name, tagline, logo_icon, website, industry, location, size, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (g.user['id'], name, tagline, logo_icon, website, industry, location, size, description))

        conn.commit()
        conn.close()
        flash('Company profile updated successfully.', 'success')
        return redirect(url_for('employer_company_profile'))

    conn.close()
    return render_template('employer/company_profile.html', company=company)

# -------------------------------------------------------------
# Step 5: Admin Management Features
# -------------------------------------------------------------
@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    conn = get_db_connection()

    # Platform KPIs
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_seekers = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'seeker'").fetchone()[0]
    total_employers = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'employer'").fetchone()[0]
    total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    active_jobs = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'active'").fetchone()[0]
    total_applications = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    successful_hires = conn.execute("SELECT COUNT(*) FROM applications WHERE status = 'accepted'").fetchone()[0]

    # Users List
    users = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()

    # Jobs List
    jobs = conn.execute('''
        SELECT j.*, c.name as company_name, cat.name as category_name, u.name as employer_name,
               (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.id) as app_count
        FROM jobs j
        JOIN companies c ON j.company_id = c.id
        JOIN categories cat ON j.category_id = cat.id
        JOIN users u ON j.employer_id = u.id
        ORDER BY j.created_at DESC
    ''').fetchall()

    # Categories List
    categories = conn.execute('''
        SELECT cat.*, COUNT(j.id) as job_count
        FROM categories cat
        LEFT JOIN jobs j ON cat.id = j.category_id
        GROUP BY cat.id
        ORDER BY cat.name ASC
    ''').fetchall()

    # Applications List
    applications = conn.execute('''
        SELECT a.*, j.title as job_title, c.name as company_name
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        JOIN companies c ON j.company_id = c.id
        ORDER BY a.applied_at DESC LIMIT 20
    ''').fetchall()

    conn.close()

    return render_template(
        'admin/dashboard.html',
        stats={
            'total_users': total_users,
            'total_seekers': total_seekers,
            'total_employers': total_employers,
            'total_jobs': total_jobs,
            'active_jobs': active_jobs,
            'total_applications': total_applications,
            'successful_hires': successful_hires
        },
        users=users,
        jobs=jobs,
        categories=categories,
        applications=applications
    )

@app.route('/admin/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@role_required('admin')
def admin_toggle_user_status(user_id):
    if user_id == g.user['id']:
        flash('You cannot suspend your own admin account.', 'warning')
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    user = conn.execute("SELECT is_active FROM users WHERE id = ?", (user_id,)).fetchone()
    if user:
        new_status = 0 if user['is_active'] == 1 else 1
        conn.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_status, user_id))
        conn.commit()
        flash(f"User account {'suspended' if new_status == 0 else 'activated'}.", 'info')
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_user(user_id):
    if user_id == g.user['id']:
        flash('You cannot delete your own admin account.', 'danger')
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash('User deleted successfully.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/jobs/<int:job_id>/toggle-feature', methods=['POST'])
@login_required
@role_required('admin')
def admin_toggle_job_feature(job_id):
    conn = get_db_connection()
    job = conn.execute("SELECT is_featured FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if job:
        new_val = 0 if job['is_featured'] == 1 else 1
        conn.execute("UPDATE jobs SET is_featured = ? WHERE id = ?", (new_val, job_id))
        conn.commit()
        flash(f"Job {'unfeatured' if new_val == 0 else 'featured on home page'}.", 'success')
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/jobs/<int:job_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_job(job_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()
    flash('Job posting deleted by admin.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/categories/new', methods=['POST'])
@login_required
@role_required('admin')
def admin_create_category():
    name = request.form.get('name', '').strip()
    icon = request.form.get('icon', 'briefcase').strip()
    color = request.form.get('color', '#4f46e5').strip()
    slug = name.lower().replace(' ', '-').replace('&', 'and')

    if not name:
        flash('Category name is required.', 'danger')
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO categories (name, icon, color, slug) VALUES (?, ?, ?, ?)",
            (name, icon, color, slug)
        )
        conn.commit()
        flash(f'Category "{name}" created.', 'success')
    except sqlite3.IntegrityError:
        flash(f'Category "{name}" already exists.', 'warning')
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/categories/<int:cat_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_category(cat_id):
    conn = get_db_connection()
    job_count = conn.execute("SELECT COUNT(*) FROM jobs WHERE category_id = ?", (cat_id,)).fetchone()[0]
    if job_count > 0:
        conn.close()
        flash(f'Cannot delete category: {job_count} active jobs are currently associated with it.', 'danger')
        return redirect(url_for('admin_dashboard'))

    conn.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()
    flash('Category deleted successfully.', 'info')
    return redirect(url_for('admin_dashboard'))

# -------------------------------------------------------------
# File Viewing & Downloads
# -------------------------------------------------------------
@app.route('/uploads/resumes/<filename>')
@login_required
def view_resume(filename):
    safe_name = secure_filename(filename)
    return send_from_directory(app.config['UPLOAD_FOLDER'], safe_name)

# -------------------------------------------------------------
# Auth (Login, Register, Logout)
# -------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and user['password_hash'] == hash_password(password):
            if user['is_active'] != 1:
                flash('Your account has been deactivated. Please contact support.', 'danger')
                return render_template('auth/login.html')

            session.clear()
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['user_name'] = user['name']

            flash(f'Welcome back, {user["name"]}!', 'success')
            next_url = request.args.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)

            if user['role'] == 'seeker':
                return redirect(url_for('seeker_dashboard'))
            elif user['role'] == 'employer':
                return redirect(url_for('employer_dashboard'))
            elif user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password. Please verify your credentials.', 'danger')

    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if g.user:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'seeker')
        company_name = request.form.get('company_name', '').strip()

        if role not in ('seeker', 'employer'):
            role = 'seeker'

        if not name or not email or not password:
            flash('Please complete all required fields.', 'danger')
            return render_template('auth/register.html')

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (name, email, password_hash, role)
                VALUES (?, ?, ?, ?)
            ''', (name, email, hash_password(password), role))
            user_id = cursor.lastrowid

            if role == 'employer':
                c_name = company_name if company_name else f"{name}'s Ventures"
                cursor.execute('''
                    INSERT INTO companies (employer_id, name, tagline, industry, location, description)
                    VALUES (?, ?, 'Innovative Solutions for Modern Teams', 'Technology', 'Remote / Hybrid', 'Pioneering modern products and fostering inclusive teams.')
                ''', (user_id, c_name))

            conn.commit()
            conn.close()

            session.clear()
            session['user_id'] = user_id
            session['role'] = role
            session['user_name'] = name

            flash('Welcome! Your account has been registered successfully.', 'success')
            if role == 'employer':
                return redirect(url_for('employer_dashboard'))
            return redirect(url_for('seeker_dashboard'))
        except sqlite3.IntegrityError:
            conn.close()
            flash('An account with this email address already exists.', 'danger')

    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out safely.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5080))
    print(f"Starting Job Portal on http://127.0.0.1:{port} ...")
    app.run(debug=True, host='127.0.0.1', port=port)
