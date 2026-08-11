import sys
from pathlib import Path
from sqlalchemy import text

project_dir = Path(__file__).resolve().parents[2]
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from backend.app.core.database import engine

def main():
    with engine.connect() as conn:
        res = conn.execute(text("SELECT transaction_id, sale_date, product_name, quantity, unit_price, revenue, payment_status FROM sales WHERE customer_name ILIKE '%Vortex%';")).fetchall()
        print(f"Total Vortex Dynamics records: {len(res)}")
        for r in res:
            print(f"- {r[0]} | Date: {r[1]} | Product: {r[2]} | Qty: {r[3]} | Unit Price: ${r[4]} | Total: ${r[5]} | Status: {r[6]}")

if __name__ == "__main__":
    main()
