"""
Vakinha Clone - HTTP Server & CaosPay Payment Gateway Integration
"""
import http.server
import socketserver
import os
import sys
import json
import re
import urllib.request
import urllib.parse
import urllib.error
import time
from database import (
    init_db,
    create_payment,
    get_payment_by_provider_id,
    mark_payment_as_paid,
    list_payments
)

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

CAOSPAY_API_URL = get_env_var("CAOSPAY_API_URL", "https://caospayment.shop/api/pay")
CAOSPAY_API_TOKEN = get_env_var("CAOSPAY_API_TOKEN", "cpk_0c356724f0964b1ef98bf37b2aceb56d2ff5913412b6f215")
USE_PAYMENT_MOCK = get_env_var("USE_PAYMENT_MOCK", "false").strip().lower() == "true"
PORT = int(get_env_var("PORT", "3000"))

# --- CaosPay API Client ---
class CaosPayClient:
    def __init__(self, base_url, token, use_mock=False):
        self.base_url = base_url.rstrip("/")
        self.token = token.strip()
        self.use_mock = use_mock

    def _generate_mock_qr_base64(self, code_text):
        """Generates a clean SVG QR Code data URI strictly for explicit offline mock mode."""
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
          <rect width="200" height="200" fill="#ffffff"/>
          <rect x="20" y="20" width="40" height="40" fill="#24ca68" rx="4"/>
          <rect x="26" y="26" width="28" height="28" fill="#ffffff" rx="2"/>
          <rect x="32" y="32" width="16" height="16" fill="#24ca68" rx="1"/>
          <rect x="140" y="20" width="40" height="40" fill="#24ca68" rx="4"/>
          <rect x="146" y="26" width="28" height="28" fill="#ffffff" rx="2"/>
          <rect x="152" y="32" width="16" height="16" fill="#24ca68" rx="1"/>
          <rect x="20" y="140" width="40" height="40" fill="#24ca68" rx="4"/>
          <rect x="26" y="146" width="28" height="28" fill="#ffffff" rx="2"/>
          <rect x="32" y="152" width="16" height="16" fill="#24ca68" rx="1"/>
          <g fill="#282828">
            <rect x="70" y="20" width="8" height="8"/><rect x="85" y="20" width="8" height="8"/><rect x="110" y="20" width="8" height="8"/>
            <rect x="70" y="35" width="8" height="8"/><rect x="95" y="35" width="15" height="8"/><rect x="120" y="35" width="8" height="8"/>
            <rect x="80" y="50" width="12" height="8"/><rect x="105" y="50" width="8" height="8"/>
            <rect x="20" y="70" width="15" height="8"/><rect x="45" y="70" width="8" height="8"/><rect x="60" y="70" width="20" height="8"/>
            <rect x="90" y="70" width="8" height="8"/><rect x="110" y="70" width="15" height="8"/><rect x="140" y="70" width="8" height="8"/>
            <rect x="160" y="70" width="20" height="8"/>
            <rect x="20" y="85" width="8" height="8"/><rect x="35" y="85" width="15" height="8"/><rect x="65" y="85" width="8" height="8"/>
            <rect x="85" y="85" width="30" height="8"/><rect x="125" y="85" width="10" height="8"/><rect x="145" y="85" width="8" height="8"/>
            <rect x="165" y="85" width="15" height="8"/>
            <rect x="20" y="105" width="12" height="8"/><rect x="40" y="105" width="8" height="8"/><rect x="55" y="105" width="25" height="8"/>
            <rect x="90" y="105" width="20" height="8"/><rect x="120" y="105" width="15" height="8"/><rect x="145" y="105" width="25" height="8"/>
            <rect x="20" y="120" width="8" height="8"/><rect x="35" y="120" width="12" height="8"/><rect x="60" y="120" width="8" height="8"/>
            <rect x="80" y="120" width="20" height="8"/><rect x="110" y="120" width="15" height="8"/><rect x="135" y="120" width="8" height="8"/>
            <rect x="155" y="120" width="25" height="8"/>
            <rect x="70" y="140" width="15" height="8"/><rect x="95" y="140" width="8" height="8"/><rect x="115" y="140" width="20" height="8"/>
            <rect x="145" y="140" width="10" height="8"/><rect x="165" y="140" width="15" height="8"/>
            <rect x="70" y="155" width="8" height="8"/><rect x="85" y="155" width="20" height="8"/><rect x="120" y="155" width="8" height="8"/>
            <rect x="140" y="155" width="20" height="8"/><rect x="170" y="155" width="10" height="8"/>
            <rect x="70" y="170" width="25" height="8"/><rect x="105" y="170" width="15" height="8"/><rect x="130" y="170" width="8" height="8"/>
            <rect x="150" y="170" width="30" height="8"/>
          </g>
          <circle cx="100" cy="100" r="16" fill="#24ca68"/>
          <path d="M93 100l5 5l10-10" fill="none" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>'''
        return "data:image/svg+xml;utf8," + urllib.parse.quote(svg)

    def generate(self, amount_cents, pay_type, description, payer_name=None, payer_document=None):
        """
        Calls CaosPay /api/pay/generate using real API by default.
        Only generates mock if USE_PAYMENT_MOCK is explicitly True.
        """
        start_time = time.time()
        value_reais = round(amount_cents / 100.0, 2)
        token_prefix = self.token[:8] + "..." if len(self.token) >= 8 else "empty"
        is_prod = not self.token.startswith("cpk_test_")
        token_type = "production" if is_prod else "sandbox"

        print(f"[PIX_REQUEST_START] type={pay_type} amount_cents={amount_cents} value_reais={value_reais:.2f} token_mode={token_type} token_prefix={token_prefix}", flush=True)

        # Explicit Mock Mode ONLY (never activated automatically)
        if self.use_mock:
            clean_doc = re.sub(r"[^0-9]", "", payer_document or "00000000000")
            tx_id = f"CP-{clean_doc[-4:] if len(clean_doc)>=4 else 'SBX'}{int(time.time()*1000)%10000000:07d}"
            emv_pix = f"00020126580014br.gov.bcb.pix0136{tx_id}@caospay.sandbox5204000053039865405{value_reais:.2f}5802BR5925SEMENTES DO AMANHA6009SAO PAULO62070503***6304ABCD"
            print(f"[CaosPay] payment created id={tx_id} (mock)")
            return {
                "id": tx_id,
                "status": "pending",
                "value": value_reais,
                "fee_reais": 0.99,
                "net_reais": round(value_reais - 0.99, 2),
                "pixCopyPaste": emv_pix,
                "qrImageUrl": "",
                "qrBase64": self._generate_mock_qr_base64(emv_pix)
            }

        # Real CaosPay Integration (Standard & Default behavior)
        url = f"{self.base_url}/generate"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        payload = {
            "value": value_reais,
            "description": description or "Doação Vaquinha",
            "payerName": payer_name or "Apoiador Solidário",
            "payerDocument": payer_document or "00000000000"
        }

        print(f"[UPSTREAM_CALL] url={url} method=POST value={value_reais:.2f} token_prefix={token_prefix}", flush=True)

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                elapsed_ms = round((time.time() - start_time) * 1000)
                raw_bytes = resp.read()
                data = json.loads(raw_bytes.decode("utf-8"))
                print(f"[UPSTREAM_SUCCESS] status={resp.status} elapsed_ms={elapsed_ms} id={data.get('payment', {}).get('id')}", flush=True)
                if data.get("success") and "payment" in data:
                    p = data["payment"]
                    # Automatic QR Code image fallback from copy-paste EMV payload
                    if not p.get("qr_image_url") and not p.get("qr_src") and not p.get("qr_base64"):
                        emv = p.get("qr_copy_paste") or p.get("pixCopyPaste")
                        if emv:
                            p["qr_image_url"] = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(emv)}"
                    p["_diagnostics"] = {
                        "elapsed_ms": elapsed_ms,
                        "upstream_status": resp.status,
                        "token_mode": token_type
                    }
                    return p
                else:
                    err_msg = data.get("message") or "Erro na resposta da CaosPay"
                    print(f"[UPSTREAM_BUSINESS_ERROR] status={resp.status} elapsed_ms={elapsed_ms} msg={err_msg}", flush=True)
                    err = RuntimeError(err_msg)
                    err.custom_detail = str(data)
                    err.upstream_status = resp.status
                    err.elapsed_ms = elapsed_ms
                    raise err
        except urllib.error.HTTPError as e:
            elapsed_ms = round((time.time() - start_time) * 1000)
            err_body = ""
            try:
                err_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            print(f"[UPSTREAM_HTTP_ERROR] status={e.code} elapsed_ms={elapsed_ms} reason={e.reason} body_snippet={err_body[:200]}", flush=True)
            e.custom_detail = err_body
            e.elapsed_ms = elapsed_ms
            e.upstream_url = url
            e.token_mode = token_type
            e.token_prefix = token_prefix
            raise
        except Exception as e:
            elapsed_ms = round((time.time() - start_time) * 1000)
            print(f"[UPSTREAM_UNEXPECTED_ERROR] type={type(e).__name__} elapsed_ms={elapsed_ms} error={e}", flush=True)
            e.elapsed_ms = elapsed_ms
            e.upstream_url = url
            e.token_mode = token_type
            e.token_prefix = token_prefix
            raise

    def check_status(self, transaction_id):
        """
        Calls CaosPay POST /api/pay/status.
        Only uses local mock if USE_PAYMENT_MOCK is explicitly True.
        """
        if self.use_mock:
            record = get_payment_by_provider_id(transaction_id)
            if record:
                return {
                    "success": True,
                    "status": record["status"],
                    "value_reais": round(record["amount_cents"] / 100.0, 2),
                    "paid_at": int(time.time())
                }
            return {"success": False, "status": "pending"}

        url = f"{self.base_url}/status"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        body = json.dumps({"id": transaction_id}).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("success"):
                    return data
                else:
                    print(f"[CaosPay] status verification failed id={transaction_id}")
                    return {"success": False, "status": data.get("status", "unknown")}
        except urllib.error.HTTPError as e:
            print(f"[CaosPay] status verification failed id={transaction_id} (HTTP {e.code})")
            return {"success": False, "error_code": e.code}
        except Exception as e:
            print(f"[CaosPay] status verification failed id={transaction_id}")
            return {"success": False, "error": str(e)}

    def sandbox_confirm(self, transaction_id):
        """
        Calls CaosPay POST /api/pay/sandbox/confirm.
        Does NOT alter the local database directly.
        """
        if self.use_mock:
            return {"success": True, "status": "simulated", "id": transaction_id}

        url = f"{self.base_url}/sandbox/confirm"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        body = json.dumps({"id": transaction_id}).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            print(f"[CaosPay Sandbox Confirm Error] HTTP {e.code}: {err_body}")
            return {"success": False, "error_code": e.code, "message": err_body}
        except Exception as e:
            print(f"[CaosPay Sandbox Confirm Error] {e}")
            return {"success": False, "error": str(e)}

caospay_client = CaosPayClient(CAOSPAY_API_URL, CAOSPAY_API_TOKEN, use_mock=USE_PAYMENT_MOCK)

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
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body_bytes)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")

        # Route 1: Create Pix Payment
        if path == "/api/payments/pix":
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw_body = self.rfile.read(length).decode("utf-8")
                body = json.loads(raw_body)

                pay_type = body.get("type", "donation")
                if pay_type not in ["donation", "goal_completion", "thank_you_video"]:
                    return self._send_json(400, {"success": False, "message": "Tipo de pagamento inválido."})

                # Backend validation of amounts in integer cents (Source of Truth)
                if pay_type == "thank_you_video":
                    amount_cents = 899  # R$ 8,99 strict and non-negotiable
                elif pay_type == "goal_completion":
                    # Goal completion must not exceed CaosPay ceiling of 1000.00 (100000 cents)
                    client_amount = float(body.get("amount", 33.42))
                    amount_cents = round(client_amount * 100)
                    amount_cents = min(100000, max(100, amount_cents))
                else:  # donation
                    client_amount = float(body.get("amount", 25.00))
                    amount_cents = round(client_amount * 100)
                    if amount_cents <= 0 or amount_cents > 100000:
                        return self._send_json(400, {"success": False, "message": "Valor de doação deve ser entre R$ 1,00 e R$ 1.000,00."})

                # Clean CPF/Document (digits only)
                payer_doc = re.sub(r"[^0-9]", "", str(body.get("payerDocument", body.get("payer_document", "12345678909"))))
                payer_name = str(body.get("payerName", body.get("payer_name", "Apoiador Solidário"))).strip()

                desc_map = {
                    "donation": "Doação Vaquinha Sementes do Amanhã",
                    "goal_completion": "Complemento da Meta Sementes do Amanhã",
                    "thank_you_video": "Vídeo Especial de Agradecimento"
                }

                # Generate via CaosPay Client
                pix_data = caospay_client.generate(
                    amount_cents=amount_cents,
                    pay_type=pay_type,
                    description=desc_map.get(pay_type, "Doação Vaquinha"),
                    payer_name=payer_name,
                    payer_document=payer_doc
                )

                # Persist in Database with Integer Cents
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
                    "qr_copy_paste": pix_data.get("qr_copy_paste") or pix_data.get("pixCopyPaste"),
                    "qr_image_url": pix_data.get("qr_image_url") or pix_data.get("qr_src") or pix_data.get("qrImageUrl"),
                    "qr_base64": pix_data.get("qr_base64") or pix_data.get("qrBase64")
                }
                create_payment(db_record)

                # Safe display payload for frontend
                amount_reais = round(amount_cents / 100.0, 2)
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

            except urllib.error.HTTPError as e:
                err_text = getattr(e, "custom_detail", "")
                elapsed_ms = getattr(e, "elapsed_ms", 0)
                tok_mode = getattr(e, "token_mode", "production")
                tok_prefix = getattr(e, "token_prefix", "unknown")
                upstream_url = getattr(e, "upstream_url", "https://caospayment.shop/api/pay/generate")

                print(f"[Generate Error HTTP {e.code}] Upstream CaosPay in {elapsed_ms}ms: {err_text[:200]}", flush=True)
                msg = "Não foi possível gerar o PIX agora. Tente novamente em alguns instantes."
                if e.code == 401:
                    msg = "Credenciais do provedor de pagamento inválidas ou expiradas."
                elif e.code == 400:
                    msg = "Dados inválidos para a criação do PIX. Verifique os valores informados."
                elif e.code in [502, 503, 504]:
                    msg = "O gateway de pagamento CaosPay está temporariamente instável (HTTP 502 da origem caospayment.shop). Tente novamente em instantes."
                return self._send_json(e.code if e.code in [400, 401, 403, 422] else 502, {
                    "success": False,
                    "message": msg,
                    "error_code": e.code,
                    "diagnostics": {
                        "upstream_url": upstream_url,
                        "upstream_status": e.code,
                        "upstream_time_ms": elapsed_ms,
                        "token_mode": tok_mode,
                        "token_prefix": tok_prefix,
                        "reason": str(e.reason),
                        "upstream_snippet": err_text[:120].strip()
                    }
                })
            except Exception as e:
                print(f"[Generate Error] {type(e).__name__}: {e}", flush=True)
                return self._send_json(500, {
                    "success": False,
                    "message": "Não foi possível gerar o PIX agora. Tente novamente em alguns instantes."
                })

        # Route 2: Webhook CaosPay
        elif path == "/api/webhooks/caospay":
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw_body = self.rfile.read(length).decode("utf-8")
                hook = json.loads(raw_body)

                # Process only DEPOSITO + PIX
                if hook.get("transactionType") != "DEPOSITO" or hook.get("transactionMethod") != "PIX":
                    return self._send_json(200, {"success": True, "message": "Ignored non-PIX deposit"})

                if str(hook.get("status", "")).upper() != "COMPLETO":
                    return self._send_json(200, {"success": True, "message": "Status not COMPLETO"})

                tx_id = hook.get("transactionId")
                if not tx_id:
                    return self._send_json(400, {"success": False, "message": "transactionId missing"})

                print(f"[CaosPay] webhook received id={tx_id}")

                payment = get_payment_by_provider_id(tx_id)
                if not payment:
                    print(f"[CaosPay] webhook transaction not found in db: {tx_id}")
                    return self._send_json(404, {"success": False, "message": "Transaction not found"})

                # IDEMPOTENCY CHECK: If already paid, return 200 without duplicate processing
                if payment["status"] == "paid":
                    return self._send_json(200, {"success": True, "message": "Already paid (idempotent)"})

                # SECTION 12 & 13: DO NOT TRUST WEBHOOK ALONE!
                # Always verify directly with CaosPay POST /api/pay/status
                status_res = caospay_client.check_status(tx_id)

                if not status_res.get("success"):
                    print(f"[CaosPay] status verification failed id={tx_id}")
                    return self._send_json(400, {"success": False, "message": "Failed to verify status with CaosPay"})

                remote_status = str(status_res.get("status", "")).lower()
                print(f"[CaosPay] remote status={remote_status}")

                if remote_status != "paid":
                    print(f"[CaosPay] remote status is not paid for id={tx_id}")
                    return self._send_json(400, {"success": False, "message": "Status is not paid"})

                # Value verification in cents
                remote_value_reais = float(status_res.get("value_reais", 0.0))
                received_cents = round(remote_value_reais * 100)
                expected_cents = int(payment["amount_cents"])

                if expected_cents != received_cents:
                    print(f"[CaosPay] amount mismatch id={tx_id}: expected={expected_cents}, received={received_cents}")
                    return self._send_json(400, {"success": False, "message": "Amount mismatch"})

                # Mark payment as paid in database with cent-level accounting
                fee_reais = float(hook.get("fee", 0.99))
                fee_cents = round(fee_reais * 100)
                net_cents = expected_cents - fee_cents

                mark_payment_as_paid(tx_id, fee_cents=fee_cents, net_amount_cents=net_cents)
                print(f"[CaosPay] payment confirmed id={tx_id}")

                return self._send_json(200, {"success": True, "status": "paid"})

            except Exception as e:
                print(f"[CaosPay Webhook Error] {e}")
                return self._send_json(500, {"success": False, "message": "Webhook processing error"})


        # Route 4: Test E2E Report Receiver (Developer test utility)
        elif path == "/api/test-e2e-report":
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw_body = self.rfile.read(length).decode("utf-8")
                report_path = os.path.join(DIRECTORY, "e2e_results.json")
                with open(report_path, "w", encoding="utf-8") as rf:
                    rf.write(raw_body)
                print(f"[E2E Report] Saved test report to {report_path}")
                return self._send_json(200, {"success": True})
            except Exception as e:
                return self._send_json(500, {"success": False, "error": str(e)})

        else:
            return self._send_json(404, {"error": "Not Found"})

    def do_GET(self):
        clean_path = self.path.split("?")[0].rstrip("/")

        # Health & Version check
        if clean_path in ["/api", "/api/health", "/api/version"]:
            is_prod = not caospay_client.token.startswith("cpk_test_")
            return self._send_json(200, {
                "status": "ok",
                "service": "vakinha-caospay-api",
                "environment": "local",
                "token_mode": "production" if is_prod else "sandbox",
                "token_prefix": caospay_client.token[:8] + "..." if caospay_client.token else "empty",
                "gateway_url": caospay_client.base_url
            })

        # Route: Payment Status Polling (GET /api/payments/<id>/status)
        m = re.match(r"^/api/payments/(?P<pid>[^/]+)/status$", clean_path)
        if m:
            pid = m.group("pid")
            payment = get_payment_by_provider_id(pid)
            if not payment and not USE_PAYMENT_MOCK:
                # Serverless / Stateless Fallback: query CaosPay directly if not in local cache
                try:
                    remote_res = caospay_client.check_status(pid)
                    if remote_res.get("success"):
                        remote_val = float(remote_res.get("value_reais", 0))
                        amt_cents = round(remote_val * 100)
                        remote_st = str(remote_res.get("status", "pending")).lower()
                        db_record = {
                            "provider_payment_id": pid,
                            "type": "donation",
                            "amount_cents": amt_cents,
                            "status": remote_st,
                            "paid_at": remote_res.get("paid_at")
                        }
                        create_payment(db_record)
                        payment = get_payment_by_provider_id(pid)
                except Exception as e:
                    print(f"[Fallback check error] {e}", flush=True)

            if not payment:
                return self._send_json(404, {"success": False, "message": "Payment not found"})

            # If still pending and not in mock mode, check CaosPay status actively
            # (Ensures real Sandbox status sync even when localhost has no public webhook URL)
            if payment["status"] == "pending" and not USE_PAYMENT_MOCK:
                try:
                    remote_res = caospay_client.check_status(pid)
                    if remote_res.get("success") and remote_res.get("status") == "paid":
                        remote_val = float(remote_res.get("value_reais", 0))
                        received_cents = round(remote_val * 100)
                        if received_cents == payment["amount_cents"]:
                            fee_cents = payment.get("fee_cents") or 99
                            net_cents = payment["amount_cents"] - fee_cents
                            mark_payment_as_paid(pid, fee_cents=fee_cents, net_amount_cents=net_cents)
                            payment = get_payment_by_provider_id(pid)
                            print(f"[CaosPay] payment confirmed via status polling id={pid}", flush=True)
                except Exception as e:
                    print(f"[CaosPay Status Poll Error] {e}", flush=True)

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

        # Static File Serving
        return super().do_GET()

def run_server(port=PORT):
    init_db()
    handler = Handler
    http.server.ThreadingHTTPServer.allow_reuse_address = False
    try:
        with http.server.ThreadingHTTPServer(("0.0.0.0", port), handler) as httpd:
            print("=" * 60, flush=True)
            print(f" Vakinha CaosPay Server rodando com sucesso!", flush=True)
            print(f" URL Local: http://localhost:{port}", flush=True)
            print(f" Diretório estático: {DIRECTORY}", flush=True)
            print(f" Modo Mock Ativo: {USE_PAYMENT_MOCK}", flush=True)
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
