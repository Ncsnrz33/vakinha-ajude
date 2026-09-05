"""
Database access layer for Vakinha SigiloPay integration using SQLite.
All monetary values are stored strictly in integer cents (e.g. R$ 25,00 -> 2500).
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
    """Initializes the database schema with cent-level accounting."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payments';")
        exists = cursor.fetchone()

        if exists:
            cursor.execute("PRAGMA table_info(payments);")
            columns = [row["name"] for row in cursor.fetchall()]
            if "amount_cents" not in columns:
                cursor.execute("DROP TABLE payments;")
                exists = None

        if not exists:
            cursor.execute("""
                CREATE TABLE payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider_payment_id TEXT NOT NULL UNIQUE,
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
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_provider_id ON payments(provider_payment_id);")

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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(payment_dict["provider_payment_id"]),
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

def mark_payment_as_paid(provider_payment_id, fee_cents=None, net_amount_cents=None):
    """
    Atomically marks a payment as paid using integer cents. Idempotent.
    """
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if fee_cents is not None and net_amount_cents is not None:
            cursor.execute("""
                UPDATE payments
                SET status = 'paid',
                    fee_cents = ?,
                    net_amount_cents = ?,
                    paid_at = COALESCE(paid_at, ?)
                WHERE provider_payment_id = ? AND status != 'paid'
            """, (int(fee_cents), int(net_amount_cents), now_str, str(provider_payment_id)))
        else:
            cursor.execute("""
                UPDATE payments
                SET status = 'paid',
                    paid_at = COALESCE(paid_at, ?)
                WHERE provider_payment_id = ? AND status != 'paid'
            """, (now_str, str(provider_payment_id)))
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
