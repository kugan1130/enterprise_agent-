"""Verification script to test Redis connection, session key writing, and PostgreSQL connection."""

import sys
from pathlib import Path

project_dir = Path(__file__).resolve().parents[2]
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from backend.app.core.config import settings
from backend.app.core.database import SessionLocal, engine
from backend.app.core.memory import add_conversation_turn, get_conversation_history
from backend.app.core.redis import get_redis_client
from sqlalchemy import text


def verify_all():
    print(f"--- VERIFYING CONFIGURATION ---")
    print(f"DATABASE_URL : {settings.DATABASE_URL}")
    print(f"REDIS_URL    : {settings.REDIS_URL}")

    print("\n--- VERIFYING REDIS CONNECTION ---")
    r = get_redis_client()
    if r is None:
        print("FAIL: Redis client is None!")
    else:
        try:
            ping_ok = r.ping()
            print(f"SUCCESS: Redis ping = {ping_ok}")
        except Exception as err:
            print(f"FAIL: Redis ping error: {err}")

    print("\n--- TESTING SESSION MEMORY WRITE TO REDIS ---")
    test_session = "session_test_999"
    add_conversation_turn(test_session, "Hello test question", "Hello test answer")
    history = get_conversation_history(test_session)
    print(f"Retrieved history for {test_session}: {history}")

    if r:
        keys = r.keys("chat_session:*")
        print(f"All active chat_session keys in Redis: {keys}")

    print("\n--- VERIFYING POSTGRESQL CONNECTION ---")
    try:
        with SessionLocal() as session:
            result = session.execute(text("SELECT COUNT(*) FROM sales;"))
            count = result.scalar()
            print(f"SUCCESS: Connected to PostgreSQL! 'sales' table total records: {count}")
    except Exception as err:
        print(f"PostgreSQL query notice: {err}")


if __name__ == "__main__":
    verify_all()
