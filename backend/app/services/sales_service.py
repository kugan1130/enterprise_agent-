"""Application service for safe sales database transactions."""
import logging
from typing import Dict, Any
from sqlalchemy import text
from backend.app.core.database import SessionLocal

logger = logging.getLogger("enterprise_ai.sales_service")

import uuid
from datetime import date

def process_sales_transaction(customer: str, product: str, quantity: int, payment_status: str) -> Dict[str, Any]:
    """Safe, parameterized multi-step transaction for inserting a sale."""
    try:
        with SessionLocal() as session:
            # Check for duplicate sale on the same date for the same customer/product
            today = date.today()
            dup_query = text(
                "SELECT id FROM sales WHERE customer_name = :customer AND product_name = :product "
                "AND quantity = :quantity AND sale_date = :sale_date"
            )
            existing = session.execute(
                dup_query, 
                {"customer": customer, "product": product, "quantity": quantity, "sale_date": today}
            ).fetchone()
            
            if existing:
                return {
                    "success": False, 
                    "error": "Duplicate document detected. Already indexed.",
                    "message": "Duplicate sale detected. No second sale inserted."
                }
            
            # Lookup product_category and unit_price from existing sales
            info_query = text("SELECT product_category, unit_price FROM sales WHERE product_name = :product LIMIT 1")
            info_row = session.execute(info_query, {"product": product}).fetchone()
            
            product_category = info_row[0] if info_row else "Unknown"
            unit_price = float(info_row[1]) if info_row else 1000.0  # Default if unknown

            revenue = float(quantity) * unit_price
            transaction_id = f"TXN-NEW-{uuid.uuid4().hex[:8].upper()}"
            
            insert_query = text(
                "INSERT INTO sales (transaction_id, sale_date, product_name, product_category, region, customer_name, quantity, unit_price, revenue, payment_status) "
                "VALUES (:txn_id, :sale_date, :product, :category, 'Global', :customer, :quantity, :unit_price, :revenue, :status)"
            )
            session.execute(
                insert_query,
                {
                    "txn_id": transaction_id,
                    "sale_date": today,
                    "product": product,
                    "category": product_category,
                    "customer": customer,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "revenue": revenue,
                    "status": payment_status
                }
            )
            session.commit()
            
            return {
                "success": True,
                "message": f"Successfully inserted sale. total_revenue = {revenue}",
                "unit_price": unit_price,
                "total_cost_revenue": revenue,
                "transaction_id": transaction_id
            }
    except Exception as e:
        logger.error(f"Sales transaction failed: {e}")
        return {"success": False, "error": str(e)}
