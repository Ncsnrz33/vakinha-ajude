"""
Database access layer for Vakinha Blackcat integration using SQLite.
All monetary values are stored strictly in integer cents (e.g. R$ 33,42 -> 3342).
"""
import sqlite3
import os
from datetime import datetime

IS_VERCEL = os.environ.get("VERCEL") is not None or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
if IS_VERCEL:
    DB_PATH = "/tmp/payments.db" if os.name != "nt" else os.path.join(os.environ.get("TEMP", "C:\\Temp"), "payments.db")
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "payments.db")

def get_connection():
    if IS_VERCEL:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema with cent-level accounting and columns for Blackcat."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payments';")
        exists = cursor.fetchone()

        if not exists:
            cursor.execute("""
                CREATE TABLE payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider_payment_id TEXT NOT NULL UNIQUE,
                    external_ref TEXT,
                    gateway TEXT DEFAULT 'blackcat',
                    type TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    net_amount_cents INTEGER,
                    fee_cents INTEGER,
                    status TEXT NOT NULL DEFAULT 'pending',
                    payer_name TEXT,
                    payer_document TEXT,
                    qr_copy_paste TEXT,
                    qr_image_url TEXT,
                    qr_base64 TEXT,
                    paid_at DATETIME,
                    end_to_end_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_provider_id ON payments(provider_payment_id);")
        else:
            # Check existing columns and add missing ones
            cursor.execute("PRAGMA table_info(payments);")
            columns = [row["name"] for row in cursor.fetchall()]
            if "external_ref" not in columns:
                cursor.execute("ALTER TABLE payments ADD COLUMN external_ref TEXT;")
            if "gateway" not in columns:
                cursor.execute("ALTER TABLE payments ADD COLUMN gateway TEXT DEFAULT 'blackcat';")
            if "end_to_end_id" not in columns:
                cursor.execute("ALTER TABLE payments ADD COLUMN end_to_end_id TEXT;")

        conn.commit()

def create_payment(payment_dict):
    """
    Inserts a new payment record into the database using cent amounts.
    """
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO payments (
                provider_payment_id,
                external_ref,
                gateway,
                type,
                amount_cents,
                net_amount_cents,
                fee_cents,
                status,
                payer_name,
                payer_document,
                qr_copy_paste,
                qr_image_url,
                qr_base64,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(payment_dict["provider_payment_id"]),
            payment_dict.get("external_ref"),
            payment_dict.get("gateway", "blackcat"),
            str(payment_dict["type"]),
            int(payment_dict["amount_cents"]),
            int(payment_dict["net_amount_cents"]) if payment_dict.get("net_amount_cents") is not None else None,
            int(payment_dict["fee_cents"]) if payment_dict.get("fee_cents") is not None else None,
            payment_dict.get("status", "pending"),
            payment_dict.get("payer_name"),
            payment_dict.get("payer_document"),
            payment_dict.get("qr_copy_paste"),
            payment_dict.get("qr_image_url"),
            payment_dict.get("qr_base64"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        return cursor.lastrowid

def get_payment_by_provider_id(provider_payment_id):
    """
    Retrieves a payment record by its unique provider ID.
    """
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM payments WHERE provider_payment_id = ?", (str(provider_payment_id),))
        row = cursor.fetchone()
        return dict(row) if row else None

def mark_payment_as_paid(provider_payment_id, fee_cents=None, net_amount_cents=None, end_to_end_id=None, paid_at=None):
    """
    Atomically marks a payment as paid using integer cents. Idempotent.
    """
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        now_str = paid_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        updates = ["status = 'paid'", "paid_at = COALESCE(paid_at, ?)"]
        params = [now_str]
        
        if fee_cents is not None:
            updates.append("fee_cents = ?")
            params.append(int(fee_cents))
        if net_amount_cents is not None:
            updates.append("net_amount_cents = ?")
            params.append(int(net_amount_cents))
        if end_to_end_id is not None:
            updates.append("end_to_end_id = ?")
            params.append(str(end_to_end_id))
            
        params.append(str(provider_payment_id))
        sql = f"UPDATE payments SET {', '.join(updates)} WHERE provider_payment_id = ? AND status != 'paid'"
        cursor.execute(sql, tuple(params))
        conn.commit()
        return cursor.rowcount > 0

def list_payments(limit=50):
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM payments ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cursor.fetchall()]

if __name__ == "__main__":
    init_db()
    print("Database initialized at", DB_PATH)
