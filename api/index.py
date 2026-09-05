"""
Vercel Serverless Function entrypoint for Vakinha SigiloPay API.
Official API Documentation: https://app.sigilopay.com.br/docs
"""
import sys
import os
import json
import re
import urllib.parse
from http.server import BaseHTTPRequestHandler

# Add root directory to sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from database import (
    init_db,
    create_payment,
    get_payment_by_provider_id,
    mark_payment_as_paid,
    list_payments
)
from sigilopay import SigiloPayClient, SigiloPayError

SIGILOPAY_CLIENT_ID = os.environ.get("SIGILOPAY_CLIENT_ID", "")
SIGILOPAY_CLIENT_SECRET = os.environ.get("SIGILOPAY_CLIENT_SECRET", "")
SIGILOPAY_API_URL = os.environ.get("SIGILOPAY_API_URL", "https://app.sigilopay.com.br/api/v1")

sigilopay_client = SigiloPayClient(
    public_key=SIGILOPAY_CLIENT_ID,
    secret_key=SIGILOPAY_CLIENT_SECRET,
    base_url=SIGILOPAY_API_URL
)

class handler(BaseHTTPRequestHandler):
    def _send_json(self, status_code, data):
        body_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body_bytes)

    def get_clean_path(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if "__path__" in qs:
            return qs["__path__"][0].rstrip("/")
        if "x-matched-path" in self.headers:
            return self.headers["x-matched-path"].split("?")[0].rstrip("/")
        if "x-forwarded-uri" in self.headers:
            return self.headers["x-forwarded-uri"].split("?")[0].rstrip("/")
        return parsed.path.rstrip("/")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_POST(self):
        path = self.get_clean_path()

        # -------------------------------------------------------------
        # Route 1: Create Pix Payment
        # -------------------------------------------------------------
        if path == "/api/payments/pix":
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw_body = self.rfile.read(length).decode("utf-8")
                body = json.loads(raw_body) if raw_body else {}

                pay_type = body.get("type", "donation")
                if pay_type not in ["donation", "goal_completion", "thank_you_video"]:
                    return self._send_json(400, {"success": False, "message": "Tipo de pagamento inválido."})

                if pay_type == "thank_you_video":
                    amount_reais = 8.99
                elif pay_type == "goal_completion":
                    client_amount = float(body.get("amount", 33.42))
                    amount_reais = round(min(1000.0, max(1.0, client_amount)), 2)
                else:  # donation
                    client_amount = float(body.get("amount", 25.00))
                    amount_reais = round(client_amount, 2)
                    if amount_reais < 1.0 or amount_reais > 1000.0:
                        return self._send_json(400, {"success": False, "message": "Valor de doação deve ser entre R$ 1,00 e R$ 1.000,00."})

                amount_cents = round(amount_reais * 100)
                payer_doc = str(body.get("payerDocument", body.get("payer_document", "111.444.777-35"))).strip()
                payer_name = str(body.get("payerName", body.get("payer_name", "Apoiador Solidário"))).strip()
                payer_email = str(body.get("payerEmail", body.get("payer_email", "doador@ajude-vakinha.com"))).strip()
                payer_phone = str(body.get("payerPhone", body.get("payer_phone", "(11) 99876-5432"))).strip()

                desc_map = {
                    "donation": "Doação Vaquinha Sementes do Amanhã",
                    "goal_completion": "Complemento da Meta Sementes do Amanhã",
                    "thank_you_video": "Vídeo Especial de Agradecimento"
                }

                pix_data = sigilopay_client.generate_pix(
                    amount_reais=amount_reais,
                    pay_type=pay_type,
                    description=desc_map.get(pay_type, "Doação Vaquinha"),
                    payer_name=payer_name,
                    payer_document=payer_doc,
                    payer_email=payer_email,
                    payer_phone=payer_phone
                )

                fee_reais = float(pix_data.get("fee_reais", 0.99))
                fee_cents = round(fee_reais * 100)
                net_cents = amount_cents - fee_cents

                db_record = {
                    "provider_payment_id": str(pix_data["id"]),
                    "type": pay_type,
                    "amount_cents": amount_cents,
                    "net_amount_cents": net_cents,
                    "fee_cents": fee_cents,
                    "status": "pending",
                    "payer_name": payer_name,
                    "payer_document": payer_doc,
                    "qr_copy_paste": pix_data.get("pixCopyPaste"),
                    "qr_image_url": pix_data.get("qrImageUrl"),
                    "qr_base64": pix_data.get("qrBase64", "")
                }
                create_payment(db_record)

                p_info = {
                    "id": pix_data["id"],
                    "status": "pending",
                    "value": amount_reais,
                    "amount_cents": amount_cents,
                    "type": pay_type,
                    "pixCopyPaste": db_record["qr_copy_paste"],
                    "qrImageUrl": db_record["qr_image_url"],
                    "qrBase64": db_record["qr_base64"],
                    "qr_code_text": db_record["qr_copy_paste"],
                    "qr_code_base64": db_record["qr_base64"],
                    "qr_code_image_url": db_record["qr_image_url"]
                }
                response_data = {
                    "success": True,
                    "id": pix_data["id"],
                    "status": "pending",
                    "amount": amount_reais,
                    "value": amount_reais,
                    "amount_cents": amount_cents,
                    "qr_code_base64": db_record["qr_base64"],
                    "qr_code_image_url": db_record["qr_image_url"],
                    "qr_code_text": db_record["qr_copy_paste"],
                    "payment": p_info
                }
                return self._send_json(200, response_data)

            except SigiloPayError as e:
                print(f"[Vercel SigiloPay Error HTTP {e.status_code}] code={e.error_code} msg={e.message}", flush=True)
                return self._send_json(e.status_code if e.status_code in [400, 401, 403, 422] else 502, {
                    "success": False,
                    "message": e.message,
                    "error_code": e.error_code,
                    "gateway": "sigilopay",
                    "details": e.details
                })
            except Exception as e:
                print(f"[Vercel Generate Error] {type(e).__name__}: {e}", flush=True)
                return self._send_json(500, {
                    "success": False,
                    "message": "Não foi possível gerar o Pix agora. Tente novamente em alguns instantes.",
                    "gateway": "sigilopay"
                })

        # -------------------------------------------------------------
        # Route 2: Webhook SigiloPay
        # -------------------------------------------------------------
        elif path == "/api/webhooks/sigilopay":
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw_body = self.rfile.read(length).decode("utf-8")
                hook = json.loads(raw_body) if raw_body else {}

                tx_id = hook.get("id") or hook.get("transactionId") or hook.get("identifier")
                status = str(hook.get("status") or hook.get("transactionStatus") or "").upper()
                print(f"[Vercel SigiloPay Webhook] id={tx_id} status={status}", flush=True)

                if not tx_id:
                    return self._send_json(400, {"success": False, "message": "transactionId missing"})

                payment = get_payment_by_provider_id(tx_id)
                if not payment:
                    return self._send_json(404, {"success": False, "message": "Transaction not found in db"})

                if payment["status"] == "paid":
                    return self._send_json(200, {"success": True, "message": "Already paid (idempotent)"})

                if status in ["COMPLETED", "PAID", "CONFIRMED", "OK"]:
                    mark_payment_as_paid(tx_id)
                    print(f"[Vercel SigiloPay Webhook] Marked {tx_id} as paid", flush=True)

                return self._send_json(200, {"success": True})

            except Exception as e:
                print(f"[Vercel Webhook Error] {e}", flush=True)
                return self._send_json(500, {"success": False, "message": "Webhook processing error"})

        else:
            return self._send_json(404, {"error": "Not Found", "path": path})

    def do_GET(self):
        clean_path = self.get_clean_path()

        # Health & Gateway Status check
        if clean_path in ["/api", "/api/health", "/api/version"]:
            cid_prefix = sigilopay_client.public_key[:8] + "..." if sigilopay_client.public_key else "empty"
            return self._send_json(200, {
                "status": "ok",
                "service": "vakinha-sigilopay-api",
                "environment": "vercel-serverless",
                "gateway": "sigilopay",
                "client_id_prefix": cid_prefix,
                "gateway_url": sigilopay_client.base_url
            })

        # Route: Payment Status Polling (GET /api/payments/<id>/status)
        m = re.match(r"^/api/payments/(?P<pid>[^/]+)/status$", clean_path)
        if m:
            pid = m.group("pid")
            payment = get_payment_by_provider_id(pid)

            if not payment:
                try:
                    remote_res = sigilopay_client.check_status(pid)
                    if remote_res.get("success"):
                        amt_cents = remote_res.get("amount_cents", 0)
                        remote_st = remote_res.get("status", "pending")
                        create_payment({
                            "provider_payment_id": pid,
                            "type": "donation",
                            "amount_cents": amt_cents,
                            "status": remote_st,
                            "paid_at": remote_res.get("paid_at")
                        })
                        payment = get_payment_by_provider_id(pid)
                except Exception as e:
                    print(f"[Vercel Status Check Error] {e}", flush=True)

            if not payment:
                return self._send_json(404, {"success": False, "message": "Payment not found"})

            if payment["status"] == "pending":
                try:
                    remote_res = sigilopay_client.check_status(pid)
                    if remote_res.get("success") and remote_res.get("status") == "paid":
                        mark_payment_as_paid(pid)
                        payment = get_payment_by_provider_id(pid)
                except Exception as e:
                    print(f"[Vercel Poll Status Error] {e}", flush=True)

            amount_reais = round(payment["amount_cents"] / 100.0, 2)
            return self._send_json(200, {
                "id": payment["provider_payment_id"],
                "status": payment["status"],
                "amount_cents": payment["amount_cents"],
                "value": amount_reais,
                "amount": amount_reais,
                "type": payment["type"],
                "paid_at": payment["paid_at"]
            })

        return self._send_json(404, {"error": "Not Found", "path": clean_path})
