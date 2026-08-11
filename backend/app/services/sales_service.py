"""Application service for safe sales database transactions."""
import logging
from typing import Dict, Any
from sqlalchemy import text
from backend.app.core.database import SessionLocal

logger = logging.getLogger("enterprise_ai.sales_service")

import uuid
from datetime import date, datetime

def process_sales_transaction(
    customer: str,
    product: str,
    quantity: int,
    payment_status: str = "Completed",
    sale_date: Any = None,
    region: str = "North America",
) -> Dict[str, Any]:
    """Safe, parameterized transaction for inserting a new sales record."""
    try:
        with SessionLocal() as session:
            # Parse or default sale date
            if isinstance(sale_date, str) and sale_date.strip():
                try:
                    s_date = datetime.strptime(sale_date.strip(), "%Y-%m-%d").date()
                except ValueError:
                    try:
                        s_date = datetime.strptime(sale_date.strip(), "%d.%m.%Y").date()
                    except ValueError:
                        s_date = date.today()
            elif isinstance(sale_date, date):
                s_date = sale_date
            else:
                s_date = date.today()

            # Check for duplicate sale
            dup_query = text(
                "SELECT id FROM sales WHERE customer_name ILIKE :customer AND product_name ILIKE :product "
                "AND quantity = :quantity AND sale_date = :sale_date"
            )
            existing = session.execute(
                dup_query, 
                {"customer": customer, "product": product, "quantity": quantity, "sale_date": s_date}
            ).fetchone()
            
            if existing:
                row_query = text(
                    "SELECT transaction_id, sale_date, product_name, product_category, region, customer_name, quantity, unit_price, revenue, payment_status FROM sales WHERE id = :id"
                )
                r = session.execute(row_query, {"id": existing[0]}).fetchone()
                existing_row = {
                    "transaction_id": r[0],
                    "sale_date": str(r[1]),
                    "product_name": r[2],
                    "product_category": r[3],
                    "region": r[4],
                    "customer_name": r[5],
                    "quantity": r[6],
                    "unit_price": float(r[7]),
                    "revenue": float(r[8]),
                    "payment_status": r[9],
                }
                return {
                    "success": True,
                    "message": "Sale transaction already recorded in database.",
                    "inserted_transaction": existing_row,
                    "rows": [existing_row],
                    "row_count": 1,
                    "columns": list(existing_row.keys()),
                }
            
            # Lookup product_category, unit_price, and region from existing sales
            info_query = text("SELECT product_name, product_category, unit_price, region FROM sales WHERE product_name ILIKE :product ORDER BY id DESC LIMIT 1")
            info_row = session.execute(info_query, {"product": f"%{product}%"}).fetchone()
            
            if not info_row:
                return {
                    "success": False,
                    "error": f"Unknown product '{product}'. Transaction rejected to prevent database corruption.",
                }
            
            official_product = info_row[0]
            product_category = info_row[1]
            unit_price = float(info_row[2])
            official_region = region if region != "Global" else (info_row[3] or "North America")

            revenue = float(quantity) * unit_price
            transaction_id = f"TXN-2026-{uuid.uuid4().hex[:4].upper()}"
            
            insert_query = text(
                "INSERT INTO sales (transaction_id, sale_date, product_name, product_category, region, customer_name, quantity, unit_price, revenue, payment_status) "
                "VALUES (:txn_id, :sale_date, :product, :category, :region, :customer, :quantity, :unit_price, :revenue, :status)"
            )
            session.execute(
                insert_query,
                {
                    "txn_id": transaction_id,
                    "sale_date": s_date,
                    "product": official_product,
                    "category": product_category,
                    "region": official_region,
                    "customer": customer,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "revenue": revenue,
                    "status": payment_status
                }
            )
            session.commit()
            
            inserted_row = {
                "transaction_id": transaction_id,
                "sale_date": str(s_date),
                "customer_name": customer,
                "product_name": official_product,
                "product_category": product_category,
                "region": official_region,
                "quantity": quantity,
                "unit_price": unit_price,
                "revenue": revenue,
                "payment_status": payment_status,
            }
            
            return {
                "success": True,
                "message": f"Successfully inserted sales transaction into PostgreSQL database.",
                "inserted_transaction": inserted_row,
                "rows": [inserted_row],
                "row_count": 1,
                "columns": list(inserted_row.keys()),
            }
    except Exception as e:
        logger.error(f"Sales transaction failed: {e}")
        return {"success": False, "error": str(e)}
