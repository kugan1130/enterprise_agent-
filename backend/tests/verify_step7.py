import os
import time
import requests
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("NexaAITest")

BASE_URL = "http://localhost:8000"
TEST_DATA_DIR = Path(__file__).parent / "test_data"
TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Create dummy test files
POLICY_PDF_PATH = TEST_DATA_DIR / "test_remote_work_policy.pdf"
SALES_CSV_PATH = TEST_DATA_DIR / "sales.csv"

if not POLICY_PDF_PATH.exists():
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(POLICY_PDF_PATH))
    c.drawString(100, 750, f"Remote Work Policy: Employees can work from home 3 days a week. {time.time()}")
    c.drawString(100, 730, "Manager approval is required for all remote days.")
    c.save()

if not SALES_CSV_PATH.exists():
    with open(SALES_CSV_PATH, "w") as f:
        f.write(f"id,product_name,quantity_sold,revenue\n1,Alpha Widget,100,5000\n2,Beta Gizmo,50,7500\n3,Gamma Module,200,{time.time()}\n")

def get_auth_token():
    url = f"{BASE_URL}/api/auth/login"
    data = {"username": "admin", "password": "adminpassword"}
    resp = requests.post(url, json=data)
    if resp.status_code == 200:
        return resp.json().get("access_token")
    
    # Try creating user if it doesn't exist
    url = f"{BASE_URL}/api/auth/register"
    data = {"username": "admin", "email": "admin@example.com", "password": "adminpassword", "role": "admin"}
    requests.post(url, json=data)
    
    url = f"{BASE_URL}/api/auth/login"
    data = {"username": "admin", "password": "adminpassword"}
    resp = requests.post(url, json=data)
    if resp.status_code == 200:
        return resp.json().get("access_token")
    logger.error(f"Failed to get auth token: {resp.text}")
    return None

def check_health():
    for i in range(10):
        try:
            resp = requests.get(f"{BASE_URL}/health")
            if resp.status_code == 200:
                logger.info("Backend is healthy: %s", resp.json())
                return True
            logger.error("Health check failed (attempt %d): %s", i+1, resp.text)
        except Exception as e:
            logger.error("Could not reach backend (attempt %d): %s", i+1, e)
        time.sleep(5)
    return False

def test_1_and_2_upload_pdf(token):
    logger.info("--- TEST 1 & 2: PDF UPLOAD & DUPLICATE ---")
    url = f"{BASE_URL}/api/documents/upload"
    headers = {"Authorization": f"Bearer {token}"}
    
    unique_name = f"test_remote_{int(time.time())}.pdf"
    
    # First Upload
    with open(POLICY_PDF_PATH, "rb") as f:
        files = {"file": (unique_name, f, "application/pdf")}
        resp = requests.post(url, headers=headers, files=files)
        logger.info("Upload 1 Response: %s", resp.json())
        assert resp.status_code in (200, 201), f"Expected success, got {resp.status_code}"
        
        doc_id = resp.json().get("document_id")
        status = resp.json().get("status")
    
    # Second Upload (Duplicate)
    with open(POLICY_PDF_PATH, "rb") as f:
        files = {"file": (unique_name, f, "application/pdf")}
        resp2 = requests.post(url, headers=headers, files=files)
        logger.info("Upload 2 Response: %s", resp2.json())
        assert resp2.status_code == 409, "Duplicate detection failed!"
        
    return doc_id

def test_chat(query, token, expected_route=None, session_id="test-session"):
    logger.info(f"--- CHAT QUERY: {query} ---")
    url = f"{BASE_URL}/api/chat"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"message": query, "session_id": session_id}
    resp = requests.post(url, headers=headers, json=payload)
    data = resp.json()
    logger.info(f"Chat Response: {data.get('response', '')[:200]}")
    time.sleep(2)
    return data

def test_4_upload_csv(token):
    logger.info("--- TEST 4: CSV STRUCTURED UPLOAD ---")
    url = f"{BASE_URL}/api/documents/upload"
    headers = {"Authorization": f"Bearer {token}"}
    unique_name = f"test_sales_{int(time.time())}.csv"
    with open(SALES_CSV_PATH, "rb") as f:
        files = {"file": (unique_name, f, "text/csv")}
        resp = requests.post(url, headers=headers, files=files)
        logger.info("Upload CSV Response: %s", resp.json())
        assert resp.status_code in (200, 201), "CSV upload failed!"

def test_10_delete(doc_id, token):
    if not doc_id:
        return
    logger.info(f"--- TEST 10: DELETE DOCUMENT {doc_id} ---")
    url = f"{BASE_URL}/api/documents/{doc_id}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.delete(url, headers=headers)
    logger.info("Delete Response: %s", resp.json())
    assert resp.status_code == 200, "Delete failed!"

def run_tests():
    if not check_health():
        logger.error("Aborting tests due to unhealthy backend.")
        return

    token = get_auth_token()
    if not token:
        return

    doc_id = test_1_and_2_upload_pdf(token)
    test_4_upload_csv(token)
    
    time.sleep(2) # Give ChromaDB / Postgres a tiny breather
    
    # Test 1 & 7: PDF Query & Memory
    test_chat("hi", token, "direct", "mem-session-1")
    test_chat("What is our remote work policy?", token, "rag", "mem-session-1")
    test_chat("What about manager approval?", token, "rag", "mem-session-1")
    
    # Test 3: SQL
    test_chat("How many products did the company sell?", token, "sql")
    
    # Test 4: CSV semantic vs numerical
    test_chat("What does the sales dataset contain?", token, "rag")
    test_chat("What is the total revenue?", token, "sql")
    
    # Test 5: Web
    test_chat("Search online for the latest LangGraph information.", token, "web")
    
    # Test 6: Multi-Agent
    test_chat("Tell me our remote work policy, calculate total revenue, and search online for the latest AI news.", token, "planner")
    
    # Test 8: SQL Write
    test_chat("NovaAnalytics bought 5 Cloud Infrastructure products and payment is completed.", token, "sql")
    
    # Test 9: Failure cases (We can just test the strict hallucination failure by asking for a fake policy)
    test_chat("What is the policy for traveling to Mars?", token, "rag")
    
    # Test 10: Delete
    test_10_delete(doc_id, token)
    
    logger.info("--- ALL TESTS COMPLETED ---")

if __name__ == "__main__":
    run_tests()
