import sqlite3
import os
import hashlib
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jobportal.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('seeker', 'employer', 'admin')),
        title TEXT,
        bio TEXT,
        phone TEXT,
        location TEXT,
        avatar TEXT,
        resume_filename TEXT,
        resume_original_name TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ''')

    # Companies Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employer_id INTEGER UNIQUE NOT NULL,
        name TEXT NOT NULL,
        tagline TEXT,
        logo_icon TEXT DEFAULT 'building-2',
        website TEXT,
        industry TEXT,
        location TEXT,
        size TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employer_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')

    # Categories Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        icon TEXT NOT NULL,
        color TEXT DEFAULT '#4f46e5',
        slug TEXT UNIQUE NOT NULL
    );
    ''')

    # Jobs Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employer_id INTEGER NOT NULL,
        company_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        category_id INTEGER NOT NULL,
        job_type TEXT NOT NULL CHECK(job_type IN ('Full-time', 'Part-time', 'Remote', 'Contract', 'Internship')),
        experience_level TEXT NOT NULL CHECK(experience_level IN ('Entry Level', 'Mid Level', 'Senior Level', 'Lead / Staff')),
        location TEXT NOT NULL,
        is_remote INTEGER DEFAULT 0,
        salary_min INTEGER,
        salary_max INTEGER,
        salary_currency TEXT DEFAULT 'USD',
        description TEXT NOT NULL,
        requirements TEXT NOT NULL,
        responsibilities TEXT,
        benefits TEXT,
        status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'closed', 'draft')),
        is_featured INTEGER DEFAULT 0,
        views_count INTEGER DEFAULT 0,
        deadline DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employer_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT
    );
    ''')

    # Applications Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        seeker_id INTEGER NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT,
        portfolio_url TEXT,
        cover_letter TEXT,
        resume_filename TEXT NOT NULL,
        resume_original_name TEXT,
        status TEXT NOT NULL DEFAULT 'applied' CHECK(status IN ('applied', 'reviewing', 'shortlisted', 'interview', 'rejected', 'accepted')),
        employer_notes TEXT,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
        FOREIGN KEY (seeker_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(job_id, seeker_id)
    );
    ''')

    # Saved Jobs Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS saved_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seeker_id INTEGER NOT NULL,
        job_id INTEGER NOT NULL,
        saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (seeker_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
        UNIQUE(seeker_id, job_id)
    );
    ''')

    # Notifications Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        type TEXT DEFAULT 'info',
        link TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')

    conn.commit()
    conn.close()

def seed_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if already seeded
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    now = datetime.now()

    # 1. Seed Users (1 Admin, 3 Employers, 3 Job Seekers)
    users_data = [
        # Admin
        ('System Administrator', 'admin@jobportal.com', hash_password('admin123'), 'admin', 'Platform Director', 'Overseeing platform operations and security.', '+1 (555) 010-0001', 'San Francisco, CA', 'admin.jpg', None, None, 1),
        # Employers
        ('Sarah Jenkins', 'employer@nexus.io', hash_password('employer123'), 'employer', 'Head of People & Talent', 'Building extraordinary engineering & product teams at Nexus Labs.', '+1 (555) 012-3456', 'San Francisco, CA', 'emp1.jpg', None, None, 1),
        ('Marcus Vance', 'marcus@auratech.com', hash_password('employer123'), 'employer', 'VP of Engineering', 'Hiring exceptional talent across cloud systems and AI.', '+1 (555) 014-7890', 'New York, NY', 'emp2.jpg', None, None, 1),
        ('Elena Rostova', 'elena@novadesign.co', hash_password('employer123'), 'employer', 'Design Principal', 'Crafting user experiences for global fintech leaders.', '+1 (555) 016-2345', 'Austin, TX', 'emp3.jpg', None, None, 1),
        # Seekers
        ('Alex Morgan', 'seeker@jobportal.com', hash_password('seeker123'), 'seeker', 'Senior Full-Stack Engineer', '7+ years crafting scalable web services, React, Python, and cloud architectures.', '+1 (555) 018-9999', 'Seattle, WA', 'seeker1.jpg', 'demo_alex_resume.pdf', 'Alex_Morgan_Resume.pdf', 1),
        ('Priya Sharma', 'priya@example.com', hash_password('seeker123'), 'seeker', 'Product & UX Designer', 'Passionate about human-centered design, design systems, and mobile interfaces.', '+1 (555) 019-4444', 'San Francisco, CA', 'seeker2.jpg', 'demo_priya_resume.pdf', 'Priya_Sharma_Resume.pdf', 1),
        ('David Kim', 'david@example.com', hash_password('seeker123'), 'seeker', 'DevOps & Cloud Architect', 'Kubernetes, Terraform, AWS solutions architect with CI/CD optimization expertise.', '+1 (555) 020-5555', 'Boston, MA', 'seeker3.jpg', 'demo_david_resume.pdf', 'David_Kim_Resume.pdf', 1),
    ]

    cursor.executemany('''
        INSERT INTO users (name, email, password_hash, role, title, bio, phone, location, avatar, resume_filename, resume_original_name, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', users_data)

    # 2. Seed Companies for Employers
    companies_data = [
        (2, 'Nexus Labs', 'Next-Gen Cloud and AI Infrastructure', 'cloud', 'https://nexuslabs.example', 'Technology & AI', 'San Francisco, CA', '50-200 employees', 'Nexus Labs builds enterprise orchestration and high-performance machine learning APIs relied upon by Fortune 500 innovators.'),
        (3, 'Aura Systems', 'Securing Digital Frontiers Worldwide', 'shield-check', 'https://aurasystems.example', 'Cybersecurity', 'New York, NY', '200-500 employees', 'Aura Systems delivers mission-critical cyber defense, zero-trust cloud architecture, and real-time observability software.'),
        (4, 'Nova Design Studio', 'Award-Winning Digital Product Agency', 'palette', 'https://novadesign.example', 'Design & Creative', 'Austin, TX', '20-50 employees', 'Nova is a human-first design studio pioneering digital branding, interactive mobile experiences, and modern product design systems.')
    ]

    cursor.executemany('''
        INSERT INTO companies (employer_id, name, tagline, logo_icon, website, industry, location, size, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', companies_data)

    # 3. Seed Categories
    categories_data = [
        ('Software Engineering', 'code', '#3b82f6', 'software-engineering'),
        ('UI/UX Design', 'pen-tool', '#ec4899', 'ui-ux-design'),
        ('DevOps & Cloud', 'server', '#8b5cf6', 'devops-cloud'),
        ('Data & Machine Learning', 'cpu', '#10b981', 'data-ml'),
        ('Product Management', 'layers', '#f59e0b', 'product-management'),
        ('Marketing & Sales', 'trending-up', '#06b6d4', 'marketing-sales')
    ]

    cursor.executemany('''
        INSERT INTO categories (name, icon, color, slug)
        VALUES (?, ?, ?, ?)
    ''', categories_data)

    # 4. Seed Jobs
    deadline_date = (now + timedelta(days=30)).strftime('%Y-%m-%d')
    jobs_data = [
        (
            2, 1, 'Senior Full-Stack Engineer (React & Python)', 1, 'Full-time', 'Senior Level', 'San Francisco, CA', 1, 140000, 185000, 'USD',
            'We are searching for a high-impact Senior Full-Stack Engineer to architect core web products and scalable backend services. You will join our collaborative team delivering state-of-the-art developer tooling.',
            '• 5+ years building production web applications in Python (Flask/FastAPI/Django) and modern React/TypeScript.\n• Strong understanding of relational databases (PostgreSQL/SQLite) and query optimization.\n• Experience with RESTful APIs, microservices, and asynchronous event streams.\n• Proven ability to mentor junior engineers and participate in architecture discussions.',
            '• Design, implement, and maintain customer-facing application features.\n• Partner closely with Product and UX teams to define roadmap deliverables.\n• Write clean, testable code accompanied by automated test suites.',
            '• Comprehensive health, dental, and vision insurance\n• 401(k) retirement match up to 5%\n• Unlimited PTO and flexible remote hours\n• Annual $3,000 learning & conference budget',
            'active', 1, 342, deadline_date
        ),
        (
            2, 1, 'Lead AI / Machine Learning Engineer', 4, 'Full-time', 'Lead / Staff', 'San Francisco, CA', 1, 180000, 230000, 'USD',
            'Lead our core AI initiative building automated inference pipelines and generative models. You will spearhead algorithmic performance and scalable model deployment across millions of requests.',
            '• M.S. or Ph.D. in Computer Science, AI, or equivalent industry experience.\n• 6+ years deploying machine learning models into high-scale production systems.\n• Deep proficiency with PyTorch, TensorFlow, vector search, and LLM fine-tuning.\n• Excellent communication skills to align technical strategy with executive stakeholders.',
            '• Own model architecture, training loops, evaluation harnesses, and production latency optimization.\n• Collaborate with backend engineers to integrate scalable inference microservices.\n• Guide the AI technology roadmap and evaluate emerging papers and techniques.',
            '• Competitive equity package (Stock options)\n• Comprehensive health and wellness coverage\n• Home office setup stipend ($2,500)\n• Annual wellness and gym reimbursement',
            'active', 1, 510, deadline_date
        ),
        (
            3, 2, 'Senior Cloud Security Architect', 3, 'Full-time', 'Senior Level', 'New York, NY', 0, 160000, 205000, 'USD',
            'Aura Systems seeks a Cloud Security Architect to harden multi-cloud environments (AWS & GCP), enforce zero-trust security postures, and safeguard global infrastructure.',
            '• 5+ years experience in cloud infrastructure security and cloud compliance frameworks (SOC2, ISO 27001).\n• Expert-level hands-on skills with Terraform, AWS IAM, GuardDuty, and Kubernetes network policies.\n• Security certifications such as CISSP, AWS Certified Security, or CCSP strongly preferred.',
            '• Architect secure cloud foundations and automate vulnerability scanning across CI/CD.\n• Conduct proactive threat modeling and security reviews of proposed application architectures.\n• Lead incident response exercises and conduct post-incident root-cause analyses.',
            '• 100% employer-covered premium health plans\n• Generous parental leave (16 weeks paid)\n• Commuter transit benefits and catered lunches\n• Top-tier hardware package (M3 Max MacBook Pro)',
            'active', 1, 289, deadline_date
        ),
        (
            3, 2, 'DevOps & Site Reliability Engineer', 3, 'Full-time', 'Mid Level', 'Remote, US', 1, 120000, 155000, 'USD',
            'Join our 24/7 reliability crew ensuring 99.99% uptime across Kubernetes clusters and distributed database shards. Ideal for engineers passionate about infrastructure-as-code.',
            '• 3+ years experience managing Kubernetes clusters in production environments.\n• Solid knowledge of Prometheus, Grafana, Datadog observability tools, and Linux internals.\n• Proficiency in Python, Bash, or Go for scripting and automation.',
            '• Maintain cluster reliability, auto-scaling mechanisms, and disaster recovery plans.\n• Streamline developer release pipelines with GitHub Actions and ArgoCD.\n• Participate in a compensated on-call rotation with blameless post-mortem culture.',
            '• 100% remote flexibility across US timezones\n• Health, dental, and vision insurance\n• Flexible paid time off and quarterly mental health recharge days\n• Annual tech equipment budget',
            'active', 0, 195, deadline_date
        ),
        (
            4, 3, 'Lead Product Designer (Design Systems)', 2, 'Full-time', 'Lead / Staff', 'Austin, TX', 1, 135000, 175000, 'USD',
            'Nova is looking for a Lead Product Designer to guide our multi-brand design system and craft bespoke digital experiences for world-class fintech and e-commerce clients.',
            '• 6+ years designing web and native mobile digital applications.\n• Master-level expertise in Figma (auto-layout, components, tokens, variables) and prototyping.\n• Outstanding portfolio demonstrating clean typography, micro-interactions, and systematic thinking.\n• Strong aptitude for collaborating with frontend engineers to ensure design fidelity.',
            '• Unify and evolve our company-wide design system across web and mobile platforms.\n• Lead user research interviews, synthesize insights, and run design sprints.\n• Mentor junior designers and represent design rationale to executive clients.',
            '• Flexible hybrid or fully remote workplace\n• 401(k) matching\n• Unlimited creative exploration days\n• Medical, dental, vision coverage with HSA option',
            'active', 1, 412, deadline_date
        ),
        (
            4, 3, 'Junior UI / Visual Designer', 2, 'Full-time', 'Entry Level', 'Austin, TX', 0, 65000, 85000, 'USD',
            'Exciting opportunity for an enthusiastic visual designer eager to launch their career in a vibrant, award-winning agency setting with dedicated mentorship.',
            '• Degree in Graphic Design, HCI, Digital Media, or equivalent bootcamp/self-taught portfolio.\n• Proficiency in Figma, Adobe Illustrator, and Photoshop.\n• Strong eye for typography, visual hierarchy, iconography, and responsive layouts.\n• Eagerness to learn, accept feedback, and iterate rapidly.',
            '• Create marketing assets, landing pages, and interactive UI components.\n• Support senior designers in preparing production design tokens and client presentations.\n• Assist in creating animations and graphic elements for web applications.',
            '• Full health and dental benefits\n• 1-on-1 mentorship program with Senior Art Directors\n• Modern office in downtown Austin with snacks & coffee\n• Paid educational workshops and conferences',
            'active', 0, 178, deadline_date
        ),
        (
            2, 1, 'Senior Technical Product Manager', 5, 'Full-time', 'Senior Level', 'San Francisco, CA', 1, 150000, 195000, 'USD',
            'Looking for an analytical and empathetic Product Manager to drive roadmap execution for our next-generation developer platform and developer cloud APIs.',
            '• 4+ years of product management experience in B2B SaaS or technical infrastructure.\n• Demonstrated success translating technical complexities into customer value.\n• Strong quantitative skills: SQL, product analytics (Mixpanel/Amplitude), A/B testing.\n• Engineering background or CS degree is a big plus.',
            '• Lead sprint planning, grooming, and roadmap prioritization with engineering leads.\n• Conduct customer discovery sessions and analyze platform telemetry.\n• Define product specs and success metrics for major feature releases.',
            '• Comprehensive health coverage & equity options\n• $1,000 annual home office allowance\n• Quarterly team retreats\n• Generous 401(k) match',
            'active', 0, 220, deadline_date
        ),
        (
            3, 2, 'Content & Growth Marketing Manager', 6, 'Full-time', 'Mid Level', 'New York, NY', 1, 95000, 125000, 'USD',
            'Scale our customer acquisition engine and developer marketing initiatives. You will produce high-converting content, lead search optimization, and direct product launches.',
            '• 3+ years experience in B2B tech marketing or growth demand generation.\n• Proven ability to create compelling articles, whitepapers, case studies, and email campaigns.\n• Familiarity with SEO tools (Ahrefs/Semrush) and marketing analytics.\n• Excellent copywriting and storytelling ability.',
            '• Author technical blog posts, customer case studies, and product announcements.\n• Manage paid campaigns across LinkedIn, Google Ads, and developer communities.\n• Collaborate with sales to produce enablement materials and collateral.',
            '• Generous health benefits and wellness plan\n• Remote flexibility\n• Annual bonus incentive structure\n• 401(k) with company match',
            'active', 0, 140, deadline_date
        ),
        (
            2, 1, 'Software Engineering Intern (Summer 2026)', 1, 'Internship', 'Entry Level', 'San Francisco, CA', 1, 45000, 60000, 'USD',
            'Join our engineering team for an immersive 12-week paid summer internship program with dedicated 1:1 mentorship from Staff Engineers.',
            '• Currently enrolled in a Computer Science, Software Engineering, or related degree program.\n• Solid understanding of data structures, algorithms, and object-oriented programming.\n• Coursework or personal projects in Python, JavaScript, or C++.\n• High curiosity, enthusiasm, and desire to solve real-world problems.',
            '• Build and deploy a core product feature from start to finish.\n• Participate in code reviews, daily standups, and team retrospectives.\n• Present final project deliverables to the entire engineering organization.',
            '• Competitive hourly compensation ($45-$55/hr equivalent)\n• Housing stipend or corporate housing assistance\n• Mentorship events and executive roundtables\n• Potential for full-time return offer upon graduation',
            'active', 0, 620, deadline_date
        )
    ]

    cursor.executemany('''
        INSERT INTO jobs (
            employer_id, company_id, title, category_id, job_type, experience_level,
            location, is_remote, salary_min, salary_max, salary_currency, description,
            requirements, responsibilities, benefits, status, is_featured, views_count, deadline
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', jobs_data)

    # 5. Seed Initial Applications
    # Seeker 5 (Alex Morgan - Senior Full Stack) applied to Job 1 (Senior Full-Stack Engineer) and Job 4 (DevOps)
    # Seeker 6 (Priya Sharma - UX) applied to Job 5 (Lead Product Designer)
    # Seeker 7 (David Kim - DevOps) applied to Job 3 (Senior Cloud Security Architect)
    applications_data = [
        (
            1, 5, 'Alex Morgan', 'seeker@jobportal.com', '+1 (555) 018-9999', 'https://github.com/alexmorgan-dev',
            'Dear Hiring Team,\n\nI am thrilled to apply for the Senior Full-Stack Engineer role at Nexus Labs. With 7+ years building resilient web services using Python, modern JavaScript, and distributed architectures, I am eager to contribute to your core developer platform.\n\nLooking forward to speaking soon!',
            'demo_alex_resume.pdf', 'Alex_Morgan_Resume.pdf', 'interview', 'Outstanding portfolio and strong GitHub presence. Scheduled technical round on Friday.',
            (now - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S'), (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        ),
        (
            4, 5, 'Alex Morgan', 'seeker@jobportal.com', '+1 (555) 018-9999', 'https://github.com/alexmorgan-dev',
            'Hello,\n\nI am applying for the DevOps & Site Reliability Engineer role. In my previous position, I maintained multi-cluster Kubernetes deployments and managed GitHub Actions pipelines reducing build times by 40%.\n\nThank you for your consideration.',
            'demo_alex_resume.pdf', 'Alex_Morgan_Resume.pdf', 'reviewing', 'Reviewing background with infrastructure team.',
            (now - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'), (now - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')
        ),
        (
            5, 6, 'Priya Sharma', 'priya@example.com', '+1 (555) 019-4444', 'https://priyasharma.design',
            'Hi Nova Design team,\n\nI have spent the last 6 years leading design systems and crafting micro-interactions for digital products. Your recent case studies resonate strongly with my approach to design craft.',
            'demo_priya_resume.pdf', 'Priya_Sharma_Resume.pdf', 'shortlisted', 'High-quality Figma case studies. Shortlisted for portfolio review.',
            (now - timedelta(days=4)).strftime('%Y-%m-%d %H:%M:%S'), (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        ),
        (
            3, 7, 'David Kim', 'david@example.com', '+1 (555) 020-5555', 'https://davidkim-cloud.dev',
            'Dear Aura Systems,\n\nI have extensive experience with zero-trust architectures, Terraform orchestration, and automated cloud compliance on AWS. I would love to contribute to your security posture.',
            'demo_david_resume.pdf', 'David_Kim_Resume.pdf', 'applied', None,
            (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'), (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        )
    ]

    cursor.executemany('''
        INSERT INTO applications (
            job_id, seeker_id, full_name, email, phone, portfolio_url,
            cover_letter, resume_filename, resume_original_name, status, employer_notes,
            applied_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', applications_data)

    # 6. Seed Saved Jobs for Seeker 5
    cursor.execute('''
        INSERT INTO saved_jobs (seeker_id, job_id, saved_at) VALUES (5, 2, ?)
    ''', ((now - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S'),))
    cursor.execute('''
        INSERT INTO saved_jobs (seeker_id, job_id, saved_at) VALUES (5, 5, ?)
    ''', ((now - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),))

    # 7. Seed Notifications
    notifications_data = [
        (5, 'Application Status Updated', 'Nexus Labs updated your application status for "Senior Full-Stack Engineer" to Interview!', 'success', '/seeker/dashboard', 0),
        (5, 'New Matching Job', 'A new job matching your preferences "Lead AI / Machine Learning Engineer" was posted by Nexus Labs.', 'info', '/jobs/2', 0),
        (2, 'New Candidate Application', 'Alex Morgan submitted an application for "Senior Full-Stack Engineer".', 'info', '/employer/applications', 0),
        (1, 'System Health Check', 'Job portal running smoothly. All services operational.', 'info', '/admin/dashboard', 0)
    ]

    cursor.executemany('''
        INSERT INTO notifications (user_id, title, message, type, link, is_read)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', notifications_data)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    seed_db()
    print("Database initialized and seeded successfully!")
