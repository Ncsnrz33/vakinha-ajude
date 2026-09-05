"""
Vercel Serverless Function entrypoint for Vakinha Clone CaosPay API.
Runtime: Python (BaseHTTPRequestHandler handler class).
"""
import sys
import os
import json
import re
import urllib.parse
import urllib.request
import urllib.error
import time
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
from server import caospay_client, USE_PAYMENT_MOCK

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
                    amount_cents = 899
                elif pay_type == "goal_completion":
                    client_amount = float(body.get("amount", 33.42))
                    amount_cents = round(client_amount * 100)
                    amount_cents = min(100000, max(100, amount_cents))
                else:  # donation
                    client_amount = float(body.get("amount", 25.00))
                    amount_cents = round(client_amount * 100)
                    if amount_cents <= 0 or amount_cents > 100000:
                        return self._send_json(400, {"success": False, "message": "Valor de doação deve ser entre R$ 1,00 e R$ 1.000,00."})

                payer_doc = re.sub(r"[^0-9]", "", str(body.get("payerDocument", body.get("payer_document", "12345678909"))))
                payer_name = str(body.get("payerName", body.get("payer_name", "Apoiador Solidário"))).strip()

                desc_map = {
                    "donation": "Doação Vaquinha Sementes do Amanhã",
                    "goal_completion": "Complemento da Meta Sementes do Amanhã",
                    "thank_you_video": "Vídeo Especial de Agradecimento"
                }

                pix_data = caospay_client.generate(
                    amount_cents=amount_cents,
                    pay_type=pay_type,
                    description=desc_map.get(pay_type, "Doação Vaquinha"),
                    payer_name=payer_name,
                    payer_document=payer_doc
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
                    "qr_copy_paste": pix_data.get("qr_copy_paste") or pix_data.get("pixCopyPaste"),
                    "qr_image_url": pix_data.get("qr_image_url") or pix_data.get("qr_src") or pix_data.get("qrImageUrl"),
                    "qr_base64": pix_data.get("qr_base64") or pix_data.get("qrBase64")
                }
                create_payment(db_record)

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

                print(f"[Vercel Generate Error HTTP {e.code}] Upstream CaosPay in {elapsed_ms}ms: {err_text[:200]}", flush=True)
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
                print(f"[Vercel Generate Error] {type(e).__name__}: {e}", flush=True)
                return self._send_json(500, {
                    "success": False,
                    "message": "Não foi possível gerar o PIX agora. Tente novamente em alguns instantes."
                })

        # -------------------------------------------------------------
        # Route 2: Webhook CaosPay
        # -------------------------------------------------------------
        elif path == "/api/webhooks/caospay":
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw_body = self.rfile.read(length).decode("utf-8")
                hook = json.loads(raw_body) if raw_body else {}

                if hook.get("transactionType") != "DEPOSITO" or hook.get("transactionMethod") != "PIX":
                    return self._send_json(200, {"success": True, "message": "Ignored non-PIX deposit"})

                if str(hook.get("status", "")).upper() != "COMPLETO":
                    return self._send_json(200, {"success": True, "message": "Status not COMPLETO"})

                tx_id = hook.get("transactionId")
                if not tx_id:
                    return self._send_json(400, {"success": False, "message": "transactionId missing"})

                payment = get_payment_by_provider_id(tx_id)
                if not payment:
                    status_res = caospay_client.check_status(tx_id)
                    if status_res.get("success") and str(status_res.get("status", "")).lower() == "paid":
                        remote_val = float(status_res.get("value_reais", 0.0))
                        amt_cents = round(remote_val * 100)
                        create_payment({
                            "provider_payment_id": tx_id,
                            "type": "donation",
                            "amount_cents": amt_cents,
                            "status": "pending"
                        })
                        payment = get_payment_by_provider_id(tx_id)
                    else:
                        return self._send_json(404, {"success": False, "message": "Transaction not found"})

                if payment and payment["status"] == "paid":
                    return self._send_json(200, {"success": True, "message": "Already paid (idempotent)"})

                status_res = caospay_client.check_status(tx_id)
                if not status_res.get("success"):
                    return self._send_json(400, {"success": False, "message": "Failed to verify status with CaosPay"})

                remote_status = str(status_res.get("status", "")).lower()
                if remote_status != "paid":
                    return self._send_json(400, {"success": False, "message": "Status is not paid"})

                remote_value_reais = float(status_res.get("value_reais", 0.0))
                received_cents = round(remote_value_reais * 100)
                expected_cents = int(payment["amount_cents"])

                if expected_cents != received_cents:
                    return self._send_json(400, {"success": False, "message": "Amount mismatch"})

                fee_reais = float(hook.get("fee", 0.99))
                fee_cents = round(fee_reais * 100)
                net_cents = expected_cents - fee_cents

                mark_payment_as_paid(tx_id, fee_cents=fee_cents, net_amount_cents=net_cents)
                return self._send_json(200, {"success": True, "status": "paid"})

            except Exception as e:
                print(f"[Vercel Webhook Error] {e}", flush=True)
                return self._send_json(500, {"success": False, "message": "Webhook processing error"})

        else:
            return self._send_json(404, {"error": "Not Found", "path": path})

    def do_GET(self):
        clean_path = self.get_clean_path()

        # Health & Version check
        if clean_path in ["/api", "/api/health", "/api/version"]:
            is_prod = not caospay_client.token.startswith("cpk_test_")
            return self._send_json(200, {
                "status": "ok",
                "service": "vakinha-caospay-api",
                "environment": "vercel-serverless",
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
                    print(f"[Vercel Status Check Error] {e}", flush=True)

            if not payment:
                return self._send_json(404, {"success": False, "message": "Payment not found"})

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
