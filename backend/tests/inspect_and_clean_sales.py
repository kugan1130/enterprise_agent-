import sys
from pathlib import Path
from sqlalchemy import text

project_dir = Path(__file__).resolve().parents[2]
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from backend.app.core.database import engine, SessionLocal

def inspect_and_clean():
    with SessionLocal() as session:
        # 1. Fetch all rows
        res = session.execute(text("SELECT id, transaction_id, product_name, product_category, region, customer_name, quantity, unit_price, revenue, payment_status, created_at FROM sales ORDER BY id;")).fetchall()
        print(f"--- ALL SALES ROWS BEFORE CLEANUP ({len(res)} total) ---")
        for r in res:
            print(r)
        
        # 2. Identify dirty/junk rows (TXN-NEW%, Unknown category, Global region, or query-text product names)
        session.execute(text("""
            DELETE FROM sales 
            WHERE transaction_id LIKE 'TXN-NEW%' 
               OR product_category = 'Unknown' 
               OR region = 'Global'
               OR product_name LIKE 'products%' 
               OR customer_name LIKE 'Show customers%';
        """))
        session.commit()

        # 3. Fetch after cleanup
        res_clean = session.execute(text("SELECT id, transaction_id, product_name, product_category, region, customer_name, quantity, unit_price, revenue, payment_status FROM sales ORDER BY id;")).fetchall()
        print(f"\n--- CLEAN SALES ROWS AFTER PURGE ({len(res_clean)} total) ---")
        for r in res_clean:
            print(r)

if __name__ == "__main__":
    inspect_and_clean()
