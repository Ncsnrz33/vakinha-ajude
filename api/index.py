"""
Vercel Serverless Function entrypoint for Vakinha Blackcat API.
Official API Documentation: https://docs.blackcatoficial.com/
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
from blackcat import BlackcatClient, BlackcatError

BLACKCAT_API_KEY = os.environ.get("BLACKCAT_API_KEY", "")
BLACKCAT_PUBLIC_KEY = os.environ.get("BLACKCAT_PUBLIC_KEY", "")
BLACKCAT_SPLIT_CODE = os.environ.get("BLACKCAT_SPLIT_CODE", "")
BLACKCAT_API_URL = os.environ.get("BLACKCAT_API_URL", "https://api.blackcatoficial.com/api")

blackcat_client = BlackcatClient(
    api_key=BLACKCAT_API_KEY,
    base_url=BLACKCAT_API_URL
)

class handler(BaseHTTPRequestHandler):
    def _send_json(self, status_code, data):
        body_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
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
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
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
                    return self._send_json(400, {"success": False, "message": "Tipo de contribuição inválido."})

                if pay_type == "thank_you_video":
                    amount_cents = 899
                elif pay_type == "goal_completion":
                    client_amount = float(body.get("amount", 33.42))
                    amount_cents = round(min(1000.0, max(1.0, client_amount)) * 100)
                else:  # donation
                    client_amount = float(body.get("amount", 25.00))
                    amount_cents = round(client_amount * 100)
                    if amount_cents < 100 or amount_cents > 100000:
                        return self._send_json(400, {"success": False, "message": "Valor de doação deve ser entre R$ 1,00 e R$ 1.000,00."})

                # Extract customer info
                cust = body.get("customer") or {}
                payer_name = str(cust.get("name") or body.get("payerName") or body.get("name") or "Apoiador Solidário").strip()
                payer_doc = str(cust.get("cpf") or cust.get("document") or body.get("payerDocument") or body.get("cpf") or "11144477735").strip()
                payer_email = str(cust.get("email") or body.get("payerEmail") or body.get("email") or "doador@ajude-vakinha.com").strip()
                payer_phone = str(cust.get("phone") or body.get("payerPhone") or body.get("phone") or "11998765432").strip()

                utms = body.get("utms") or body.get("utm") or {}

                desc_map = {
                    "donation": "Contribuição Sementes do Amanhã",
                    "goal_completion": "Complemento da Meta Sementes do Amanhã",
                    "thank_you_video": "Vídeo Especial de Agradecimento"
                }

                res = blackcat_client.create_sale(
                    amount_cents=amount_cents,
                    title=desc_map.get(pay_type, "Contribuição Sementes do Amanhã"),
                    customer_name=payer_name,
                    customer_email=payer_email,
                    customer_phone=payer_phone,
                    customer_document=payer_doc,
                    document_type="cpf",
                    postback_url="https://ajude-vakinha.vercel.app/api/payments/webhook",
                    utms=utms
                )

                tx_id = str(res["transactionId"])
                db_record = {
                    "provider_payment_id": tx_id,
                    "external_ref": res.get("raw", {}).get("data", {}).get("externalRef"),
                    "gateway": "blackcat",
                    "type": pay_type,
                    "amount_cents": amount_cents,
                    "net_amount_cents": res.get("netAmount"),
                    "fee_cents": res.get("fees"),
                    "status": "pending",
                    "payer_name": payer_name,
                    "payer_document": payer_doc,
                    "qr_copy_paste": res.get("copyPaste"),
                    "qr_image_url": res.get("qrCodeBase64"),
                    "qr_base64": res.get("qrCodeBase64")
                }
                create_payment(db_record)

                amount_reais = round(amount_cents / 100.0, 2)
                p_info = {
                    "id": tx_id,
                    "status": "pending",
                    "value": amount_reais,
                    "amount_cents": amount_cents,
                    "type": pay_type,
                    "pixCopyPaste": res.get("copyPaste"),
                    "qrImageUrl": res.get("qrCodeBase64"),
                    "qrBase64": res.get("qrCodeBase64"),
                    "qr_code_text": res.get("copyPaste"),
                    "qr_code_base64": res.get("qrCodeBase64"),
                    "qr_code_image_url": res.get("qrCodeBase64")
                }
                response_data = {
                    "success": True,
                    "transactionId": tx_id,
                    "id": tx_id,
                    "status": "PENDING",
                    "amount": amount_reais,
                    "amount_cents": amount_cents,
                    "qrCodeBase64": res.get("qrCodeBase64"),
                    "copyPaste": res.get("copyPaste"),
                    "expiresAt": res.get("expiresAt"),
                    "payment": p_info
                }
                return self._send_json(201, response_data)

            except BlackcatError as e:
                print(f"[Vercel Blackcat Error HTTP {e.status_code}] msg={e.message}", flush=True)
                return self._send_json(e.status_code if e.status_code in [400, 401, 403, 404, 422, 429] else 500, {
                    "success": False,
                    "message": "Não foi possível gerar o Pix agora. Confira os dados e tente novamente." if e.status_code != 401 else "Credenciais do gateway inválidas.",
                    "error": e.message,
                    "gateway": "blackcat"
                })
            except Exception as e:
                print(f"[Vercel Generate Error] {type(e).__name__}: {e}", flush=True)
                return self._send_json(500, {
                    "success": False,
                    "message": "Não foi possível gerar o Pix agora. Tente novamente em alguns instantes.",
                    "gateway": "blackcat"
                })

        # -------------------------------------------------------------
        # Route 2: Webhook Blackcat (POST /api/payments/webhook)
        # -------------------------------------------------------------
        elif path in ["/api/payments/webhook", "/api/webhooks/blackcat"]:
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw_body = self.rfile.read(length).decode("utf-8")
                hook = json.loads(raw_body) if raw_body else {}

                tx_id = hook.get("transactionId") or hook.get("id")
                event = hook.get("event") or self.headers.get("X-Webhook-Event", "")
                status = str(hook.get("status", "")).upper()
                print(f"[Vercel Blackcat Webhook] event={event} tx_id={tx_id} status={status}", flush=True)

                if not tx_id:
                    return self._send_json(400, {"success": False, "message": "transactionId missing"})

                payment = get_payment_by_provider_id(tx_id)
                if not payment:
                    return self._send_json(404, {"success": False, "message": "Transaction not found in db"})

                if payment["status"] == "paid":
                    return self._send_json(200, {"success": True, "message": "Already paid (idempotent)"})

                # Server-to-server verification with Blackcat API Key (Section Webhook Security)
                verified = blackcat_client.get_status(tx_id)
                if verified.get("success") and verified.get("status") == "paid":
                    fee_cents = verified.get("fees") or 0
                    net_cents = verified.get("netAmount") or (payment["amount_cents"] - fee_cents)
                    e2e = verified.get("endToEndId")
                    paid_at = verified.get("paidAt")
                    mark_payment_as_paid(tx_id, fee_cents=fee_cents, net_amount_cents=net_cents, end_to_end_id=e2e, paid_at=paid_at)
                    print(f"[Vercel Webhook Verified] Payment {tx_id} confirmed as paid", flush=True)

                return self._send_json(200, {"success": True})

            except Exception as e:
                print(f"[Vercel Webhook Error] {e}", flush=True)
                return self._send_json(500, {"success": False, "message": "Webhook processing error"})

        else:
            return self._send_json(404, {"error": "Not Found", "path": path})

    def do_GET(self):
        clean_path = self.get_clean_path()
        parsed_url = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed_url.query)

        # Health & Gateway Status check
        if clean_path in ["/api", "/api/health", "/api/version"]:
            return self._send_json(200, {
                "status": "ok",
                "service": "vakinha-blackcat-api",
                "environment": "vercel-serverless",
                "gateway": "blackcat",
                "has_api_key": bool(blackcat_client.api_key),
                "gateway_url": blackcat_client.base_url
            })

        # Route: Payment Status Polling (GET /api/payments/<id>/status or GET /api/payments/pix/status?transactionId=...)
        pid = None
        m = re.match(r"^/api/payments/(?P<pid>[^/]+)/status$", clean_path)
        if m:
            pid = m.group("pid")
        elif clean_path in ["/api/payments/pix/status", "/api/payments/status"]:
            pid = qs.get("transactionId", [None])[0] or qs.get("id", [None])[0]

        if pid:
            payment = get_payment_by_provider_id(pid)

            if not payment:
                try:
                    remote_res = blackcat_client.get_status(pid)
                    if remote_res.get("success"):
                        amt_cents = remote_res.get("amount_cents", 0)
                        remote_st = remote_res.get("status", "pending")
                        create_payment({
                            "provider_payment_id": pid,
                            "type": "donation",
                            "amount_cents": amt_cents,
                            "status": remote_st,
                            "paid_at": remote_res.get("paidAt"),
                            "end_to_end_id": remote_res.get("endToEndId"),
                            "gateway": "blackcat"
                        })
                        payment = get_payment_by_provider_id(pid)
                except Exception as e:
                    print(f"[Vercel Status Check Error] {e}", flush=True)

            if not payment:
                return self._send_json(404, {"success": False, "message": "Payment not found"})

            if payment["status"] == "pending":
                try:
                    remote_res = blackcat_client.get_status(pid)
                    if remote_res.get("success") and remote_res.get("status") == "paid":
                        fee_cents = remote_res.get("fees") or 0
                        net_cents = remote_res.get("netAmount") or (payment["amount_cents"] - fee_cents)
                        e2e = remote_res.get("endToEndId")
                        paid_at = remote_res.get("paidAt")
                        mark_payment_as_paid(pid, fee_cents=fee_cents, net_amount_cents=net_cents, end_to_end_id=e2e, paid_at=paid_at)
                        payment = get_payment_by_provider_id(pid)
                except Exception as e:
                    print(f"[Vercel Poll Status Error] {e}", flush=True)

            amount_reais = round(payment["amount_cents"] / 100.0, 2)
            return self._send_json(200, {
                "id": payment["provider_payment_id"],
                "transactionId": payment["provider_payment_id"],
                "status": payment["status"],
                "amount_cents": payment["amount_cents"],
                "value": amount_reais,
                "amount": amount_reais,
                "type": payment["type"],
                "paid_at": payment["paid_at"]
            })

        return self._send_json(404, {"error": "Not Found", "path": clean_path})
