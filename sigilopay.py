"""
SigiloPay Payment Gateway Client
Official API documentation: https://app.sigilopay.com.br/docs
"""
import os
import json
import time
import uuid
import re
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta

class SigiloPayError(Exception):
    def __init__(self, message, status_code=500, error_code="GATEWAY_ERROR", details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}

class SigiloPayClient:
    def __init__(self, public_key, secret_key, base_url="https://app.sigilopay.com.br/api/v1"):
        self.public_key = (public_key or "").strip()
        self.secret_key = (secret_key or "").strip()
        self.base_url = (base_url or "https://app.sigilopay.com.br/api/v1").rstrip("/")

    def _get_headers(self):
        return {
            "x-public-key": self.public_key,
            "x-secret-key": self.secret_key,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    def _format_phone(self, phone):
        digits = re.sub(r'\D', '', str(phone or ''))
        if len(digits) == 11:
            return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
        elif len(digits) == 10:
            return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
        return "(11) 99876-5432"

    def _format_document(self, doc):
        digits = re.sub(r'\D', '', str(doc or ''))
        if len(digits) == 11:
            return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
        # Standard fallback CPF with valid check digits (111.444.777-35)
        return "111.444.777-35"

    def generate_pix(self, amount_reais, pay_type="donation", description=None,
                     payer_name=None, payer_document=None, payer_email=None, payer_phone=None,
                     callback_url=None):
        """
        Creates a PIX charge using SigiloPay POST /gateway/pix/receive
        """
        start_time = time.time()
        amt = round(float(amount_reais), 2)
        
        name = (payer_name or "").strip()
        if len(name) < 3:
            name = "Apoiador Solidário"
            
        email = (payer_email or "").strip()
        if not email or "@" not in email:
            email = "doador@ajude-vakinha.com"

        phone = self._format_phone(payer_phone)
        document = self._format_document(payer_document)
        
        desc = description or ("Doação Vaquinha - Tratamento da Antonella" if pay_type == "donation" else "Apoio Vakinha Solidária")
        identifier = f"vk_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        due_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        cb_url = callback_url or "https://ajude-vakinha.vercel.app/api/webhooks/sigilopay"

        payload = {
            "identifier": identifier,
            "amount": amt,
            "client": {
                "name": name,
                "email": email,
                "phone": phone,
                "document": document
            },
            "products": [
                {
                    "id": f"prod_{pay_type}_{int(time.time())}",
                    "name": desc,
                    "quantity": 1,
                    "price": amt
                }
            ],
            "dueDate": due_date,
            "metadata": {
                "type": pay_type,
                "platform": "vakinha-solidaria"
            },
            "callbackUrl": cb_url
        }

        url = f"{self.base_url}/gateway/pix/receive"
        req_body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=req_body, headers=self._get_headers(), method="POST")

        print(f"[SigiloPay POST /gateway/pix/receive] identifier={identifier} amount=R${amt:.2f}", flush=True)

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                elapsed_ms = round((time.time() - start_time) * 1000)
                res_body = resp.read().decode("utf-8")
                data = json.loads(res_body) if res_body else {}
                print(f"[SigiloPay Success] HTTP {resp.status} in {elapsed_ms}ms tx_id={data.get('transactionId')}", flush=True)

                pix_info = data.get("pix", {})
                emv_code = pix_info.get("code", "")
                qr_img = pix_info.get("image", "")
                
                # SigiloPay documentation notes: base64 is deprecated, render QR from code
                if not qr_img and emv_code:
                    qr_img = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(emv_code)}"

                return {
                    "id": data.get("transactionId", identifier),
                    "status": "pending",
                    "value": amt,
                    "amount": amt,
                    "fee_reais": float(data.get("fee", 0.99)),
                    "pixCopyPaste": emv_code,
                    "qr_code_text": emv_code,
                    "qrImageUrl": qr_img,
                    "qr_code_image_url": qr_img,
                    "qrBase64": "",
                    "qr_code_base64": "",
                    "raw": data
                }

        except urllib.error.HTTPError as e:
            elapsed_ms = round((time.time() - start_time) * 1000)
            err_body = ""
            try:
                err_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            print(f"[SigiloPay HTTP Error {e.code}] in {elapsed_ms}ms: {err_body[:250]}", flush=True)

            error_code = "GATEWAY_HTTP_ERROR"
            msg = "Não foi possível gerar o Pix agora. Tente novamente em alguns instantes."
            details = {}

            try:
                err_json = json.loads(err_body)
                error_code = err_json.get("errorCode", error_code)
                msg = err_json.get("message", msg)
                details = err_json.get("details", {})
            except Exception:
                pass

            if e.code == 401:
                msg = "Credenciais da SigiloPay inválidas ou não autorizadas."
            elif e.code == 400:
                msg = f"Dados inválidos para criação do Pix na SigiloPay: {msg}"

            err = SigiloPayError(msg, status_code=e.code, error_code=error_code, details=details)
            err.raw_body = err_body
            err.elapsed_ms = elapsed_ms
            raise err

        except Exception as e:
            elapsed_ms = round((time.time() - start_time) * 1000)
            print(f"[SigiloPay Unexpected Error] in {elapsed_ms}ms: {type(e).__name__} {e}", flush=True)
            raise SigiloPayError(
                "Não foi possível conectar ao gateway SigiloPay. Tente novamente em alguns instantes.",
                status_code=502,
                error_code="GATEWAY_UNAVAILABLE"
            )

    def check_status(self, transaction_id):
        """
        Queries transaction status via GET /gateway/transactions?id=<transaction_id>
        """
        url = f"{self.base_url}/gateway/transactions?id={urllib.parse.quote(str(transaction_id))}"
        req = urllib.request.Request(url, headers=self._get_headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                res_body = resp.read().decode("utf-8")
                data = json.loads(res_body) if res_body else {}
                st = str(data.get("status", "PENDING")).upper()
                is_paid = st in ["COMPLETED", "PAID", "CONFIRMED", "OK"]
                amt = float(data.get("amount", 0.0))
                return {
                    "success": True,
                    "status": "paid" if is_paid else "pending",
                    "remote_status": st,
                    "value_reais": amt,
                    "amount_cents": round(amt * 100),
                    "paid_at": data.get("payedAt"),
                    "raw": data
                }
        except urllib.error.HTTPError as e:
            return {"success": False, "status_code": e.code, "error": "HTTP Error"}
        except Exception as e:
            return {"success": False, "error": str(e)}
