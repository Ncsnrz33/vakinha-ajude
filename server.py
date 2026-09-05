"""
Vakinha - HTTP Server & Blackcat Official Payment Gateway Integration
Official API Documentation: https://docs.blackcatoficial.com/
"""
import http.server
import os
import sys
import json
import re
import urllib.parse
import time
from database import (
    init_db,
    create_payment,
    get_payment_by_provider_id,
    mark_payment_as_paid,
    list_payments
)
from blackcat import BlackcatClient, BlackcatError

DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# --- Load Environment Variables (.env) ---
def load_env():
    env_file = os.path.join(DIRECTORY, ".env")
    env_vars = {}
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()
    return env_vars

ENV = load_env()

def get_env_var(key, default=""):
    return os.environ.get(key) or ENV.get(key) or default

BLACKCAT_API_KEY = get_env_var("BLACKCAT_API_KEY", "")
BLACKCAT_PUBLIC_KEY = get_env_var("BLACKCAT_PUBLIC_KEY", "")
BLACKCAT_SPLIT_CODE = get_env_var("BLACKCAT_SPLIT_CODE", "")
BLACKCAT_API_URL = get_env_var("BLACKCAT_API_URL", "https://api.blackcatoficial.com/api")
PORT = int(get_env_var("PORT", "3000"))

blackcat_client = BlackcatClient(
    api_key=BLACKCAT_API_KEY,
    base_url=BLACKCAT_API_URL
)

# --- Custom Request Handler ---
class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def _send_json(self, status_code, data):
        body_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body_bytes)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
        self.end_headers()

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")

        # Route 1: Create Pix Payment
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

                # Generate Pix via Blackcat Client
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
                print(f"[Blackcat Create Sale Error HTTP {e.status_code}] msg={e.message}", flush=True)
                return self._send_json(e.status_code if e.status_code in [400, 401, 403, 404, 422, 429] else 500, {
                    "success": False,
                    "message": "Não foi possível gerar o Pix agora. Confira os dados e tente novamente." if e.status_code != 401 else "Credenciais do gateway inválidas.",
                    "error": e.message,
                    "gateway": "blackcat"
                })
            except Exception as e:
                print(f"[Create Pix Error] {type(e).__name__}: {e}", flush=True)
                return self._send_json(500, {
                    "success": False,
                    "message": "Não foi possível gerar o Pix agora. Tente novamente em alguns instantes.",
                    "gateway": "blackcat"
                })

        # Route 2: Webhook Blackcat (POST /api/payments/webhook)
        elif path in ["/api/payments/webhook", "/api/webhooks/blackcat"]:
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw_body = self.rfile.read(length).decode("utf-8")
                hook = json.loads(raw_body) if raw_body else {}

                tx_id = hook.get("transactionId") or hook.get("id")
                event = hook.get("event") or self.headers.get("X-Webhook-Event", "")
                status = str(hook.get("status", "")).upper()
                print(f"[Blackcat Webhook Received] event={event} tx_id={tx_id} status={status}", flush=True)

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
                    print(f"[Blackcat Webhook Verified] Payment {tx_id} confirmed as paid", flush=True)

                return self._send_json(200, {"success": True})

            except Exception as e:
                print(f"[Blackcat Webhook Error] {e}", flush=True)
                return self._send_json(500, {"success": False, "message": "Webhook error"})

        else:
            return self._send_json(404, {"error": "Not Found"})

    def do_GET(self):
        clean_path = self.path.split("?")[0].rstrip("/")
        parsed_url = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed_url.query)

        # Health & Gateway Status
        if clean_path in ["/api", "/api/health", "/api/version"]:
            return self._send_json(200, {
                "status": "ok",
                "service": "vakinha-blackcat-api",
                "gateway": "blackcat",
                "environment": "production" if os.environ.get("VERCEL") else "local",
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
                # Query Blackcat directly if not in local cache
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

            if not payment:
                return self._send_json(404, {"success": False, "message": "Payment not found"})

            # If pending, check with Blackcat
            if payment["status"] == "pending":
                remote_res = blackcat_client.get_status(pid)
                if remote_res.get("success") and remote_res.get("status") == "paid":
                    fee_cents = remote_res.get("fees") or 0
                    net_cents = remote_res.get("netAmount") or (payment["amount_cents"] - fee_cents)
                    e2e = remote_res.get("endToEndId")
                    paid_at = remote_res.get("paidAt")
                    mark_payment_as_paid(pid, fee_cents=fee_cents, net_amount_cents=net_cents, end_to_end_id=e2e, paid_at=paid_at)
                    payment = get_payment_by_provider_id(pid)
                    print(f"[Blackcat Status Poll] Payment {pid} confirmed as paid", flush=True)

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

        # Static File Serving
        return super().do_GET()

def run_server(port=PORT):
    init_db()
    handler = Handler
    http.server.ThreadingHTTPServer.allow_reuse_address = False
    try:
        with http.server.ThreadingHTTPServer(("0.0.0.0", port), handler) as httpd:
            print("=" * 60, flush=True)
            print(f" Vakinha Blackcat Server rodando com sucesso!", flush=True)
            print(f" URL Local: http://localhost:{port}", flush=True)
            print(f" Gateway Ativo: Blackcat ({blackcat_client.base_url})", flush=True)
            print("=" * 60, flush=True)
            httpd.serve_forever()
    except OSError as e:
        if port == 3000:
            print(f"Porta 3000 em uso, tentando porta 5173...")
            run_server(5173)
        else:
            print(f"Erro ao iniciar servidor na porta {port}: {e}")
            sys.stdout.flush()

if __name__ == "__main__":
    run_server()
