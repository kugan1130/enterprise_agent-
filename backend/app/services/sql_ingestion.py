"""Application service for safe structured data ingestion into PostgreSQL."""
import csv
import logging
import re
from pathlib import Path
from sqlalchemy import text
from backend.app.core.database import SessionLocal

logger = logging.getLogger("enterprise_ai.sql_ingestion")

def _sanitize_table_name(filename: str) -> str:
    """Sanitize filename to a valid PostgreSQL table name."""
    name = Path(filename).stem.lower()
    name = re.sub(r"[^a-z0-9_]", "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_")
    if not name or name[0].isdigit():
        name = "t_" + name
    return name

def _infer_type(value: str) -> str:
    """Infer optimal PostgreSQL column type for a given string value."""
    if not value.strip():
        return "TEXT"
    try:
        int(value)
        return "INTEGER"
    except ValueError:
        try:
            float(value)
            return "FLOAT"
        except ValueError:
            return "TEXT"

def ingest_csv_to_sql(csv_path: Path, filename: str) -> str:
    """
    Ingest a CSV file into a new PostgreSQL table.
    Returns the sanitized table name.
    """
    table_name = _sanitize_table_name(filename)
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            raise ValueError(f"CSV file {filename} is empty.")
            
        # Sanitize column names
        safe_headers = [_sanitize_table_name(h) if h.strip() else f"col_{i}" for i, h in enumerate(headers)]
        
        # Read a batch to infer types
        batch = []
        for _ in range(50):
            try:
                batch.append(next(reader))
            except StopIteration:
                break
                
    if not batch:
        raise ValueError(f"CSV file {filename} has no data rows.")
        
    # Infer types based on the batch
    column_types = []
    for col_idx in range(len(safe_headers)):
        col_type = "INTEGER"
        for row in batch:
            if col_idx < len(row):
                val_type = _infer_type(row[col_idx])
                if val_type == "TEXT":
                    col_type = "TEXT"
                    break
                elif val_type == "FLOAT" and col_type == "INTEGER":
                    col_type = "FLOAT"
        column_types.append(col_type)

    # Re-open to read all data for insertion
    with SessionLocal() as session:
        # Drop table if exists to allow re-ingestion of the same table name
        session.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
        
        # Create table with a unique primary key name to avoid conflicts with CSV columns named 'id'
        columns_def = ", ".join([f"{h} {t}" for h, t in zip(safe_headers, column_types)])
        create_stmt = f"CREATE TABLE {table_name} (_record_id SERIAL PRIMARY KEY, {columns_def})"
        session.execute(text(create_stmt))
        
        # Insert data
        insert_cols = ", ".join(safe_headers)
        placeholders = ", ".join([f":{h}" for h in safe_headers])
        insert_stmt = f"INSERT INTO {table_name} ({insert_cols}) VALUES ({placeholders})"
        
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader) # skip headers
            
            records = []
            for row in reader:
                record = {}
                for col_idx, header in enumerate(safe_headers):
                    val = row[col_idx].strip() if col_idx < len(row) else None
                    if not val:
                        record[header] = None
                    else:
                        c_type = column_types[col_idx]
                        if c_type == "INTEGER":
                            try:
                                record[header] = int(val)
                            except ValueError:
                                record[header] = None
                        elif c_type == "FLOAT":
                            try:
                                record[header] = float(val)
                            except ValueError:
                                record[header] = None
                        else:
                            record[header] = val
                records.append(record)
                
                # Batch insert
                if len(records) >= 1000:
                    session.execute(text(insert_stmt), records)
                    records = []
                    
            if records:
                session.execute(text(insert_stmt), records)
                
        session.commit()
        
    return table_name

def ingest_sql_file_to_sql(sql_path: Path, filename: str) -> str:
    """
    Parse and execute an SQL dump containing CREATE TABLE and INSERT statements.
    Returns a comma-separated string of created table names.
    """
    sql_content = sql_path.read_text(encoding="utf-8")
    
    # Simple validation: forbid destructive commands
    upper_content = sql_content.upper()
    forbidden = ["DROP DATABASE", "DELETE FROM", "UPDATE ", "ALTER TABLE"]
    for word in forbidden:
        if word in upper_content:
            raise ValueError(f"Forbidden SQL operation found in {filename}: {word}")
            
    # Extract table names that are being created
    created_tables = []
    for match in re.finditer(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z0-9_]+)", sql_content, re.IGNORECASE):
        created_tables.append(match.group(1).lower())
        
    if not created_tables:
        raise ValueError(f"No CREATE TABLE statements found in {filename}")
        
    # Remove comments that might interfere with split
    sql_without_comments = "\n".join(
        line for line in sql_content.splitlines() if not line.lstrip().startswith("--")
    )
    statements = [s.strip() for s in sql_without_comments.split(";") if s.strip()]
    
    with SessionLocal() as session:
        for stmt in statements:
            # We don't execute DROP TABLE IF EXISTS from user SQL dumps as a safety measure,
            # but if it was in the allowed list, it would run here. The instruction forbids DROP.
            if stmt.upper().startswith("DROP"):
                raise ValueError(f"DROP statement found and rejected in {filename}")
            session.execute(text(stmt))
        session.commit()
        
    return ",".join(created_tables)
