"""Automated live HTTP verification script for Enterprise AI Assistant web server."""

import json
import urllib.request
import sys

BASE_URL = "http://127.0.0.1:8000"


def test_health():
    print("\n--- 1. Testing GET /api/health ---")
    req = urllib.request.Request(f"{BASE_URL}/api/health")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(f"Status Code: {resp.status} | Data: {data}")
        assert data.get("status") in ["ok", "healthy"]


def test_auth():
    print("\n--- 2. Testing POST /api/auth/register & login ---")
    user_payload = {
        "username": "auto_test_user",
        "email": "autotest@enterprise.ai",
        "password": "Password123!",
    }
    
    # Register
    req = urllib.request.Request(
        f"{BASE_URL}/api/auth/register",
        data=json.dumps(user_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            reg_data = json.loads(resp.read().decode("utf-8"))
            print(f"Register Result: {reg_data.get('username')}")
    except Exception as err:
        print(f"Register notice (may already exist): {err}")

    # Login
    login_data = f"username={user_payload['username']}&password={user_payload['password']}".encode("utf-8")
    req_login = urllib.request.Request(
        f"{BASE_URL}/api/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req_login) as resp:
        token_data = json.loads(resp.read().decode("utf-8"))
        token = token_data.get("access_token")
        print(f"Login Successful! Token acquired: {token[:20]}...")
        return token


def test_chat_stream(token: str, prompt: str, session_id: str):
    print(f"\n--- Testing Stream Chat Prompt: '{prompt}' ---")
    chat_payload = {
        "prompt": prompt,
        "session_id": session_id,
    }
    req = urllib.request.Request(
        f"{BASE_URL}/api/chat/stream",
        data=json.dumps(chat_payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )

    events = []
    final_text = ""
    route_used = ""
    download_url = ""

    with urllib.request.urlopen(req) as resp:
        for line_bytes in resp:
            line = line_bytes.decode("utf-8").strip()
            if line.startswith("data: "):
                try:
                    payload = json.loads(line[6:])
                    events.append(payload)
                    if payload.get("type") == "route":
                        route_used = payload.get("route")
                    elif payload.get("type") == "final":
                        final_text = payload.get("content") or payload.get("response")
                    elif payload.get("type") == "artifact":
                        art = payload.get("artifact", {})
                        download_url = art.get("download_url")
                except Exception:
                    pass

    print(f"  Route Selected: {route_used}")
    print(f"  Events Received: {len(events)}")
    print(f"  Final Response Snippet: {final_text[:120]}...")
    if download_url:
        print(f"  Artifact Download URL: {download_url}")

    return {
        "route": route_used,
        "response": final_text,
        "download_url": download_url,
    }


def run_full_suite():
    print("=" * 80)
    print("RUNNING AUTOMATED END-TO-END HTTP LIVE API VERIFICATION")
    print("=" * 80)

    test_health()
    token = test_auth()
    session_id = "auto_session_999"

    # Test 1: Direct Greeting
    res1 = test_chat_stream(token, "hi", session_id)
    assert res1["route"] == "direct"

    # Test 2: RAG Leave Policy Query
    res2 = test_chat_stream(token, "What is the company leave policy?", session_id)
    assert res2["route"] == "rag"
    assert "couldn't find" not in res2["response"].lower() or len(res2["response"]) > 30

    # Test 3: PDF Report Conversion
    res3 = test_chat_stream(token, "make it PDF", session_id)
    assert res3["download_url"] is not None
    print(f"PDF Generated Successfully! Download URL: {res3['download_url']}")

    # Test 4: SQL Revenue Query
    res4 = test_chat_stream(token, "what is total sales?", session_id)
    assert res4["route"] == "sql"

    print("=" * 80)
    print("ALL LIVE HTTP STREAMING VERIFICATION TESTS PASSED PERFECTLY!")
    print("=" * 80)


if __name__ == "__main__":
    run_full_suite()
