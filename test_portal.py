import unittest
import os
from app import app
from database import get_db_connection

class JobPortalTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()

    def test_homepage(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'JobConnect', response.data)
        self.assertIn(b'Explore by Industry', response.data)
        self.assertIn(b'Featured Opportunities', response.data)

    def test_job_search_and_filter(self):
        response = self.client.get('/jobs')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Find Your Next Opportunity', response.data)

        # Search keyword
        response_search = self.client.get('/jobs?q=Python')
        self.assertEqual(response_search.status_code, 200)
        self.assertIn(b'Senior Full-Stack Engineer', response_search.data)

        # Filter remote
        response_remote = self.client.get('/jobs?remote=1')
        self.assertEqual(response_remote.status_code, 200)

        # Filter salary
        response_salary = self.client.get('/jobs?min_salary=150000')
        self.assertEqual(response_salary.status_code, 200)

    def test_job_detail_page(self):
        response = self.client.get('/jobs/1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Senior Full-Stack Engineer', response.data)
        self.assertIn(b'Nexus Labs', response.data)

    def test_demo_seeker_dashboard(self):
        # Demo login as seeker
        res_login = self.client.get('/demo-login/seeker', follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b'Candidate Hub', res_login.data)
        self.assertIn(b'Alex Morgan', res_login.data)
        self.assertIn(b'My Applications', res_login.data)

        # Test profile page
        res_profile = self.client.get('/seeker/profile')
        self.assertEqual(res_profile.status_code, 200)
        self.assertIn(b'Candidate Profile', res_profile.data)

    def test_demo_employer_dashboard_and_posting(self):
        # Demo login as employer
        res_login = self.client.get('/demo-login/employer', follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b'Employer Hub', res_login.data)
        self.assertIn(b'Nexus Labs', res_login.data)

        # Manage jobs page
        res_jobs = self.client.get('/employer/jobs')
        self.assertEqual(res_jobs.status_code, 200)
        self.assertIn(b'All Job Postings', res_jobs.data)

        # Candidate applications page
        res_apps = self.client.get('/employer/applications')
        self.assertEqual(res_apps.status_code, 200)
        self.assertIn(b'Candidate Pipeline', res_apps.data)

        # Post new job GET
        res_new_job = self.client.get('/employer/jobs/new')
        self.assertEqual(res_new_job.status_code, 200)
        self.assertIn(b'Post New Job', res_new_job.data)

    def test_demo_admin_dashboard(self):
        # Demo login as admin
        res_login = self.client.get('/demo-login/admin', follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b'Admin Management Center', res_login.data)
        self.assertIn(b'Platform Administration', res_login.data)
        self.assertIn(b'User Accounts', res_login.data)
        self.assertIn(b'Job Moderation', res_login.data)

    def test_resume_download(self):
        # Login and view resume
        self.client.get('/demo-login/seeker')
        res = self.client.get('/uploads/resumes/demo_alex_resume.pdf')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content_type, 'application/pdf')

if __name__ == '__main__':
    unittest.main()
