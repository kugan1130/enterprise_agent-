import sys
import os
from pathlib import Path
import json

project_dir = Path(__file__).resolve().parents[2]
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from backend.app.core.config import settings
from backend.app.core.database import SessionLocal, engine
from backend.app.core.redis import get_redis_client
from backend.app.core.chroma import get_chroma_client
from backend.app.models.user import DocumentRecord
from backend.app.rag.ingest import COLLECTION_NAME
from backend.app.tools.sql_tool import execute_sql_query
from sqlalchemy import text, inspect

def main():
    print("--- 1. POSTGRESQL RUNTIME CONNECTION ---")
    try:
        with engine.connect() as conn:
            # Note: SQLite uses different functions than Postgres. We need to handle both if we're on SQLite.
            if "sqlite" in settings.DATABASE_URL:
                print("database: sqlite (local file)")
                print(f"host: local")
                print("user: N/A")
                print("schema: main")
            else:
                res = conn.execute(text("SELECT current_database(), current_user, current_schema(), inet_server_addr(), inet_server_port();")).fetchone()
                print(f"database: {res[0]}")
                print(f"user: {res[1]}")
                print(f"schema: {res[2]}")
                print(f"host: {res[3]}")
                print(f"port: {res[4]}")
    except Exception as e:
        print(f"PostgreSQL connection failed: {e}")

    print("\n--- 2. POSTGRESQL TABLES ---")
    try:
        with engine.connect() as conn:
            inspector = inspect(conn)
            tables = inspector.get_table_names()
            print(f"tables visible to application: {tables}")
    except Exception as e:
        print(f"Failed to list tables: {e}")

    print("\n--- 3. SALES TABLE ---")
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT COUNT(*) FROM sales;")).fetchone()
            print("actual table name: sales")
            print(f"row count: {res[0]}")
            
            # Check if SQL Agent can access it
            sql_res = execute_sql_query("SELECT COUNT(*) FROM sales;")
            print(f"SQL Agent can access: {'YES' if sql_res.get('success') else 'NO'}")
    except Exception as e:
        print(f"Sales table check failed: {e}")

    print("\n--- 4. DOCUMENT RECORDS ---")
    try:
        with SessionLocal() as db:
            count = db.query(DocumentRecord).count()
            docs = db.query(DocumentRecord).all()
            print(f"total document records: {count}")
            for d in docs:
                print(f"- {d.filename} | status: {d.status} | chunks: {d.chunk_count}")
    except Exception as e:
        print(f"Document records check failed: {e}")

    print("\n--- 5. REDIS ---")
    r = get_redis_client()
    if r:
        try:
            r_info = r.connection_pool.connection_kwargs
            print(f"host: {r_info.get('host')}")
            print(f"port: {r_info.get('port')}")
            print(f"db: {r_info.get('db')}")
            print(f"PING: {r.ping()}")
            r.setex("nexa:diagnostic:123", 10, "test_value")
            print("SET: True")
            print(f"GET: {r.get('nexa:diagnostic:123') == 'test_value'}")
            print(f"TTL: {r.ttl('nexa:diagnostic:123') > 0}")
        except Exception as e:
            print(f"Redis test failed: {e}")
    else:
        print("host: None (Using In-Memory Fallback)")
        print(f"port: N/A")
        print(f"db: N/A")
        print(f"PING: N/A")
        print(f"SET: N/A")
        print(f"GET: N/A")
        print(f"TTL: N/A")

    print("\n--- 6. CHROMADB ---")
    try:
        c = get_chroma_client()
        print(f"persistent path: {settings.DATA_DIR / 'chroma'}")
        print(f"collection: {COLLECTION_NAME}")
        col = c.get_or_create_collection(COLLECTION_NAME)
        print(f"count before: {col.count()}")
    except Exception as e:
        print(f"ChromaDB check failed: {e}")

    print("\n--- 7. SQL AGENT ---")
    try:
        print(f"database connection: {settings.DATABASE_URL}")
        sql_res = execute_sql_query("SELECT COUNT(*) FROM sales;")
        print("sales table visible: YES" if sql_res.get('success') else "sales table visible: NO")
        print(f"direct SQL: YES")
        print(f"agent SQL: {'YES' if sql_res.get('success') else 'NO'}")
    except Exception as e:
        print(f"SQL agent check failed: {e}")

if __name__ == '__main__':
    main()
