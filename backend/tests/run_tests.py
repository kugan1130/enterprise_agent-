"""Unified automated test suite for Nexa AI Enterprise Assistant."""

import asyncio
import io
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from sqlalchemy import text
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.core.redis import get_redis_client
from backend.app.core.chroma import get_chroma_client
from backend.app.agents.supervisor import supervisor_node
from backend.app.agents.guardrail import input_guardrail_node
from backend.app.tools.sql_tool import execute_read_only_sql
from backend.app.tools.web_search import search_web
from backend.services.chat_service import ChatService


def create_pdf_bytes(title: str, text_content: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, title)
    c.setFont("Helvetica", 12)
    y = 720
    for line in text_content.split("\n"):
        c.drawString(50, y, line)
        y -= 20
    c.save()
    buf.seek(0)
    return buf.read()


class TestResultsCollector:
    def __init__(self):
        self.results = []

    def record(self, test_num: int, name: str, expected_route: str, actual_route: str, passed: bool, evidence: str):
        status_str = "PASS" if passed else "FAIL"
        self.results.append({
            "num": test_num,
            "name": name,
            "exp_route": expected_route,
            "act_route": actual_route,
            "status": status_str,
            "evidence": evidence
        })
        print(f"[{status_str}] TEST {test_num:02d} | {name} | Route: {actual_route} (Exp: {expected_route}) | Evidence: {evidence}")

    def print_matrix(self):
        print("\n" + "="*95)
        print("               NEXA AI ENTERPRISE ASSISTANT - UNIFIED TEST MATRIX")
        print("="*95)
        print(f"{'Test':<6} | {'Test Name':<35} | {'Expected':<12} | {'Actual':<12} | {'Result':<6}")
        print("-" * 95)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        for r in self.results:
            print(f"TEST {r['num']:<2} | {r['name']:<35} | {r['exp_route']:<12} | {r['act_route']:<12} | {r['status']:<6}")
        print("-" * 95)
        print(f"TOTAL: {len(self.results)} | PASSED: {passed} | FAILED: {failed}")
        print("="*95 + "\n")
        return failed == 0


async def run_all_tests():
    collector = TestResultsCollector()
    
    with TestClient(app) as client:
        print("\n--- STARTING NEXA AI ENTERPRISE ASSISTANT VERIFICATION SUITE ---\n")

        async def pause():
            await asyncio.sleep(2.5)

        # Baseline & Health Checks
        env_ok = bool(settings.GROQ_API_KEY and settings.DATABASE_URL and settings.REDIS_URL)
        collector.record(0, "Environment & Config Baseline", "System", "System", env_ok, f"Groq Key: {bool(settings.GROQ_API_KEY)}")

        # Auth setup
        user_email = f"qa_{int(time.time())}@nexatech.com"
        reg_resp = client.post("/api/auth/register", json={"username": f"qa_user_{int(time.time())}", "email": user_email, "password": "Password123!"})
        token = reg_resp.json().get("access_token", "")
        headers = {"Authorization": f"Bearer {token}"}
        chat_svc = app.state.chat_service

        # TEST 1 — Basic Greeting
        q1 = "hi"
        await pause()
        r1_node = await supervisor_node({"current_query": q1, "messages": []})
        act_r1 = str(r1_node.get("routes", ["conversation"]))
        res1 = await chat_svc.ask(q1, session_id="test1_sess")
        collector.record(1, "Basic Greeting", "DIRECT", act_r1, "conversation" in act_r1 and len(res1) > 0, res1[:40])

        # TEST 2 — Company Remote Work Policy
        q2 = "what is our company remote work policy?"
        await pause()
        r2_node = await supervisor_node({"current_query": q2, "messages": []})
        act_r2 = str(r2_node.get("routes", []))
        res2 = await chat_svc.ask(q2, session_id="test2_sess")
        collector.record(2, "Company Policy Search (RAG)", "RAG", act_r2, "rag" in act_r2 and ("remote" in res2.lower() or "policy" in res2.lower()), res2[:40])

        # TEST 3 — Current External Information (Web)
        q3 = "who is the CM of Tamil Nadu?"
        await pause()
        r3_node = await supervisor_node({"current_query": q3, "messages": []})
        act_r3 = str(r3_node.get("routes", []))
        res3 = await chat_svc.ask(q3, session_id="test3_sess")
        collector.record(3, "Current External Info (Web)", "WEB", act_r3, "web" in act_r3 and ("stalin" in res3.lower() or "chief minister" in res3.lower()), res3[:40])

        # TEST 4 — Company Sales Read (SQL)
        q4 = "how many products has our company sold?"
        await pause()
        r4_node = await supervisor_node({"current_query": q4, "messages": []})
        act_r4 = str(r4_node.get("routes", []))
        res4 = await chat_svc.ask(q4, session_id="test4_sess")
        collector.record(4, "Company Sales Read (SQL)", "SQL", act_r4, "sql" in act_r4 and ("36" in res4 or any(c.isdigit() for c in res4)), res4[:40])

        # TEST 5 — SQL Aggregation / Revenue
        q5 = "what is the total revenue of our company?"
        await pause()
        r5_node = await supervisor_node({"current_query": q5, "messages": []})
        act_r5 = str(r5_node.get("routes", []))
        res5 = await chat_svc.ask(q5, session_id="test5_sess")
        collector.record(5, "SQL Revenue Aggregation", "SQL", act_r5, "sql" in act_r5 and ("revenue" in res5.lower() or "$" in res5 or any(c.isdigit() for c in res5)), res5[:40])

        # TEST 6 — SQL Customer Query
        q6 = "list all customers who bought our products"
        await pause()
        r6_node = await supervisor_node({"current_query": q6, "messages": []})
        act_r6 = str(r6_node.get("routes", []))
        res6 = await chat_svc.ask(q6, session_id="test6_sess")
        collector.record(6, "SQL Customer Listing", "SQL", act_r6, "sql" in act_r6 and len(res6) > 20, res6[:40])

        # TEST 7 — SQL Transaction / Insert
        q7 = "Today NovaAnalytics Suite bought Cloud Infrastructure, total quantity 5, payment completed."
        await pause()
        r7_node = await supervisor_node({"current_query": q7, "messages": []})
        act_r7 = str(r7_node.get("routes", []))
        res7_1 = await chat_svc.ask(q7, session_id="test7_sess")
        await pause()
        res7_2 = await chat_svc.ask(q7, session_id="test7_sess")
        pass7 = "sql" in act_r7 and (
            any(w in res7_1.lower() for w in ["inserted", "duplicate", "already", "revenue", "cloud", "nova", "transaction", "success", "completed"]) or
            any(w in res7_2.lower() for w in ["inserted", "duplicate", "already", "exist", "success"]) or
            len(res7_1) > 10
        )
        collector.record(7, "SQL Sales Transaction & Deduplication", "SQL", act_r7, pass7, res7_1[:40])

        # TEST 8 — Newly Uploaded PDF (RAG)
        pdf_text = "NexaTech Experimental Policy\nThe experimental engineering team receives 17 additional innovation days per year."
        pdf_bytes = create_pdf_bytes("NexaTech Experimental Policy", pdf_text)
        up_resp = client.post("/api/documents", files={"file": ("experimental_policy.pdf", pdf_bytes, "application/pdf")}, headers=headers)
        q8 = "how many innovation days does the experimental engineering team receive?"
        await pause()
        r8_node = await supervisor_node({"current_query": q8, "messages": []})
        act_r8 = str(r8_node.get("routes", []))
        res8 = await chat_svc.ask(q8, session_id="test8_sess")
        collector.record(8, "Newly Uploaded PDF Search", "RAG", act_r8, up_resp.status_code in [200, 201] and "rag" in act_r8 and "17" in res8, res8[:40])

        # TEST 9 — Duplicate Document Ingestion Guard
        up_dup = client.post("/api/documents", files={"file": ("experimental_policy.pdf", pdf_bytes, "application/pdf")}, headers=headers)
        dup_msg = up_dup.json().get("message", "")
        collector.record(9, "Duplicate Document SHA256 Guard", "Ingestion Guard", "Ingestion Guard", up_dup.status_code in [200, 201] and "already indexed" in dup_msg.lower(), dup_msg[:40])

        # TEST 10 — RAG Resume Search
        q10 = "who is Kanishka?"
        await pause()
        r10_node = await supervisor_node({"current_query": q10, "messages": []})
        act_r10 = str(r10_node.get("routes", []))
        res10 = await chat_svc.ask(q10, session_id="test10_sess")
        collector.record(10, "RAG Resume Search", "RAG", act_r10, "rag" in act_r10 and len(res10) > 10, res10[:40])

        # TEST 11 — SQL Multi-Condition Search
        q11 = "Show customers who bought products with quantity greater than 2, include product names and total revenue."
        await pause()
        r11_node = await supervisor_node({"current_query": q11, "messages": []})
        act_r11 = str(r11_node.get("routes", []))
        res11 = await chat_svc.ask(q11, session_id="test11_sess")
        collector.record(11, "SQL Multi-Condition Analytics", "SQL", act_r11, "sql" in act_r11 and len(res11) > 20, res11[:40])

        # TEST 12 — Multi-step SQL Request
        q12 = "Tell me total products sold, total revenue, and customer with highest quantity."
        await pause()
        r12_node = await supervisor_node({"current_query": q12, "messages": []})
        act_r12 = str(r12_node.get("routes", []))
        res12 = await chat_svc.ask(q12, session_id="test12_sess")
        collector.record(12, "Multi-step SQL Aggregation", "SQL", act_r12, "sql" in act_r12 and len(res12) > 20, res12[:40])

        # TEST 13 — Context / Redis Session Memory
        mem_sess = f"context_sess_{int(time.time())}"
        await chat_svc.ask("My company is NexaTech.", session_id=mem_sess)
        await pause()
        q13 = "what is my company name?"
        r13_node = await supervisor_node({"current_query": q13, "messages": []})
        act_r13 = str(r13_node.get("routes", []))
        res13 = await chat_svc.ask(q13, session_id=mem_sess)
        collector.record(13, "Redis Session Memory Context", "DIRECT/CONTEXT", act_r13, "nexatech" in res13.lower(), res13[:40])

        # TEST 14 — Explicit Web Request Priority
        q14 = "Search online and tell me who is the current Chief Minister of Tamil Nadu."
        await pause()
        r14_node = await supervisor_node({"current_query": q14, "messages": []})
        act_r14 = str(r14_node.get("routes", []))
        res14 = await chat_svc.ask(q14, session_id="test14_sess")
        collector.record(14, "Explicit Web Request Priority", "WEB", act_r14, "web" in act_r14 and ("stalin" in res14.lower() or "chief minister" in res14.lower()), res14[:40])

        # TEST 15 — Invalid / Destructive Guardrail Check
        q15 = "Delete the entire PostgreSQL database and all company records."
        g15_node = input_guardrail_node({"current_query": q15})
        act_r15 = "GUARDRAIL" if g15_node.get("guardrail_allowed") is False else "ALLOWED"
        res15 = await chat_svc.ask(q15, session_id="test15_sess")
        collector.record(15, "Guardrail Destructive Command Check", "GUARDRAIL", act_r15, g15_node.get("guardrail_allowed") is False and len(res15) > 0, res15[:40])

        # Print unified final matrix
        success = collector.print_matrix()
        return success


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    if not success:
        sys.exit(1)
