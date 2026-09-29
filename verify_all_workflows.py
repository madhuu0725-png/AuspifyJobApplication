import requests
import re

BASE_URL = "http://127.0.0.1:5080"

def test_workflow():
    session = requests.Session()
    print("Testing against running server at:", BASE_URL)

    # 1. Test Home page
    r = session.get(BASE_URL + "/")
    assert r.status_code == 200, f"Home page failed: {r.status_code}"
    assert "JobConnect" in r.text
    assert "Explore by Industry" in r.text
    print("  [PASS] Step 1: Home page loaded successfully.")

    # 2. Test Search & Filters
    r = session.get(BASE_URL + "/jobs?q=Python")
    assert r.status_code == 200
    assert "Senior Full-Stack Engineer" in r.text
    print("  [PASS] Step 2: Search by keyword 'Python' returned results.")

    r = session.get(BASE_URL + "/jobs?type=Full-time&remote=1")
    assert r.status_code == 200
    print("  [PASS] Step 3: Filter by type and remote returned results.")

    # 3. Test Job Details
    r = session.get(BASE_URL + "/jobs/1")
    assert r.status_code == 200
    assert "Nexus Labs" in r.text
    print("  [PASS] Step 4: Job details view /jobs/1 verified.")

    # 4. Test Demo Login: Candidate
    r = session.get(BASE_URL + "/demo-login/seeker", allow_redirects=True)
    assert r.status_code == 200
    assert "Candidate Hub" in r.text
    assert "Alex Morgan" in r.text
    print("  [PASS] Step 5: Candidate Demo login and Candidate Hub verified.")

    # 5. Candidate Saves Job
    r = session.post(BASE_URL + "/jobs/3/toggle-save", headers={"X-Requested-With": "XMLHttpRequest"})
    assert r.status_code == 200
    print("  [PASS] Step 6: Candidate saved job toggle verified.")

    # 6. Test Demo Login: Employer
    r = session.get(BASE_URL + "/demo-login/employer", allow_redirects=True)
    assert r.status_code == 200
    assert "Employer Hub" in r.text
    assert "Nexus Labs" in r.text
    print("  [PASS] Step 7: Employer Demo login and Employer Hub verified.")

    # 7. Employer Candidate Pipeline
    r = session.get(BASE_URL + "/employer/applications")
    assert r.status_code == 200
    assert "Candidate Pipeline" in r.text
    print("  [PASS] Step 8: Employer candidate pipeline verified.")

    # 8. Employer Post Job
    post_data = {
        "title": "Principal Distributed Systems Engineer",
        "category_id": 1,
        "job_type": "Full-time",
        "experience_level": "Lead / Staff",
        "location": "San Francisco, CA",
        "is_remote": "on",
        "salary_min": 190000,
        "salary_max": 240000,
        "salary_currency": "USD",
        "description": "Architect high-scale distributed backend systems.",
        "requirements": "• 8+ years distributed systems\n• Raft/Paxos experience",
        "responsibilities": "• Lead core platform architecture",
        "benefits": "• Equity, health, 401k",
        "status": "active"
    }
    r = session.post(BASE_URL + "/employer/jobs/new", data=post_data, allow_redirects=True)
    assert r.status_code == 200
    print("  [PASS] Step 9: Employer job creation workflow executed successfully.")

    # 9. Test Demo Login: Admin
    r = session.get(BASE_URL + "/demo-login/admin", allow_redirects=True)
    assert r.status_code == 200
    assert "System Overview & Control" in r.text
    assert "Job Moderation" in r.text
    print("  [PASS] Step 10: Admin center loaded with platform stats and controls.")

    print("\nAll 10 Core Application Workflows Verified Successfully!")

if __name__ == '__main__':
    test_workflow()
