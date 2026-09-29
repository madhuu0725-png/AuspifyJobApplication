import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

def create_resume(filename, name, title, email, phone, location, summary, skills, experience):
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'resumes')
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)

    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter

    # Header accent banner
    c.setFillColor(colors.HexColor('#1e293b'))
    c.rect(0, height - 100, width, 100, fill=1, stroke=0)

    # Name and Title
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, height - 45, name)
    c.setFont("Helvetica", 13)
    c.setFillColor(colors.HexColor('#93c5fd'))
    c.drawString(50, height - 70, title)

    # Contact line
    c.setFillColor(colors.HexColor('#cbd5e1'))
    c.setFont("Helvetica", 9)
    c.drawRightString(width - 50, height - 45, f"{email}  |  {phone}")
    c.drawRightString(width - 50, height - 65, location)

    y = height - 130

    # Summary
    c.setFillColor(colors.HexColor('#0f172a'))
    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, y, "PROFESSIONAL SUMMARY")
    y -= 5
    c.setStrokeColor(colors.HexColor('#cbd5e1'))
    c.setLineWidth(1)
    c.line(50, y, width - 50, y)
    y -= 18

    c.setFillColor(colors.HexColor('#334155'))
    c.setFont("Helvetica", 10)
    for line in summary:
        c.drawString(50, y, line)
        y -= 15

    y -= 10
    # Skills
    c.setFillColor(colors.HexColor('#0f172a'))
    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, y, "CORE COMPETENCIES")
    y -= 5
    c.line(50, y, width - 50, y)
    y -= 18

    c.setFillColor(colors.HexColor('#334155'))
    c.setFont("Helvetica", 10)
    c.drawString(50, y, " • ".join(skills[:5]))
    y -= 16
    c.drawString(50, y, " • ".join(skills[5:]))
    y -= 25

    # Experience
    c.setFillColor(colors.HexColor('#0f172a'))
    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, y, "WORK EXPERIENCE")
    y -= 5
    c.line(50, y, width - 50, y)
    y -= 20

    for exp in experience:
        c.setFillColor(colors.HexColor('#0f172a'))
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, exp['role'] + " — " + exp['company'])
        c.setFillColor(colors.HexColor('#64748b'))
        c.setFont("Helvetica-Oblique", 9)
        c.drawRightString(width - 50, y, exp['period'])
        y -= 16

        c.setFillColor(colors.HexColor('#334155'))
        c.setFont("Helvetica", 9.5)
        for bullet in exp['bullets']:
            c.drawString(65, y, f"•  {bullet}")
            y -= 14
        y -= 12

    c.save()
    print(f"Generated {filepath}")

if __name__ == '__main__':
    create_resume(
        'demo_alex_resume.pdf',
        'Alex Morgan',
        'Senior Full-Stack Engineer',
        'seeker@jobportal.com',
        '+1 (555) 018-9999',
        'Seattle, WA',
        [
            'Versatile Full-Stack Engineer with 7+ years of experience architecting high-scale web platforms.',
            'Specialized in Python (Flask/FastAPI), React, distributed microservices, and modern cloud deployment.'
        ],
        ['Python', 'TypeScript', 'React.js', 'PostgreSQL', 'Docker', 'AWS', 'GraphQL', 'Redis', 'CI/CD Pipelines', 'System Design'],
        [
            {
                'role': 'Senior Software Engineer',
                'company': 'Vanguard Cloud Solutions',
                'period': '2022 - Present',
                'bullets': [
                    'Led development of customer portal serving 120,000+ daily active users.',
                    'Reduced API latency by 45% through query optimization and Redis caching layer.',
                    'Mentored team of 4 junior and mid-level engineers in code craft and architecture.'
                ]
            },
            {
                'role': 'Full-Stack Developer',
                'company': 'Apex Interactive',
                'period': '2019 - 2022',
                'bullets': [
                    'Built responsive web interfaces and microservices using React and Python.',
                    'Implemented automated CI/CD deployment pipelines cutting release time by 60%.'
                ]
            }
        ]
    )

    create_resume(
        'demo_priya_resume.pdf',
        'Priya Sharma',
        'Product & UX Designer',
        'priya@example.com',
        '+1 (555) 019-4444',
        'San Francisco, CA',
        [
            'Human-centered Product & UX Designer with 6+ years creating intuitive digital experiences.',
            'Deep expertise in design systems, interaction patterns, user research, and cross-functional leadership.'
        ],
        ['Figma', 'Design Systems', 'User Research', 'Wireframing', 'Prototyping', 'Design Tokens', 'Usability Testing', 'HTML/CSS', 'Agile UX', 'Information Architecture'],
        [
            {
                'role': 'Lead Product Designer',
                'company': 'Starlight Fintech',
                'period': '2021 - Present',
                'bullets': [
                    'Designed mobile investment platform that grew user adoption by 85% in 18 months.',
                    'Created unified design system used across 6 engineering teams in web and mobile.'
                ]
            }
        ]
    )

    create_resume(
        'demo_david_resume.pdf',
        'David Kim',
        'DevOps & Cloud Architect',
        'david@example.com',
        '+1 (555) 020-5555',
        'Boston, MA',
        [
            'Cloud Infrastructure & DevOps Engineer specialized in Kubernetes, Terraform, and AWS.',
            'Passionate about zero-trust security postures, automated canary deployments, and 99.99% uptime.'
        ],
        ['Kubernetes', 'Terraform', 'AWS', 'Docker', 'Prometheus', 'Grafana', 'Python', 'Bash', 'GitOps', 'CI/CD'],
        [
            {
                'role': 'Senior DevOps Engineer',
                'company': 'HyperScale Networks',
                'period': '2020 - Present',
                'bullets': [
                    'Managed multi-region EKS clusters serving millions of concurrent web transactions.',
                    'Architected zero-downtime blue/green deployment strategy reducing incident rates by 70%.'
                ]
            }
        ]
    )
