"""
Blackcat Payment Gateway Client
Official API documentation: https://docs.blackcatoficial.com/
"""
import os
import json
import time
import uuid
import re
import urllib.request
import urllib.parse
import urllib.error

class BlackcatError(Exception):
    def __init__(self, message, status_code=500, error_detail=None, raw_body=""):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_detail = error_detail or {}
        self.raw_body = raw_body

class BlackcatClient:
    def __init__(self, api_key, base_url="https://api.blackcatoficial.com/api"):
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "https://api.blackcatoficial.com/api").rstrip("/")

    def _get_headers(self):
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    @staticmethod
    def clean_digits(val):
        return re.sub(r'\D', '', str(val or ''))

    def create_sale(self, amount_cents, title="Contribuição Sementes do Amanhã",
                    customer_name=None, customer_email=None, customer_phone=None,
                    customer_document=None, document_type="cpf",
                    external_ref=None, postback_url=None,
                    expires_in_days=1, utms=None):
        """
        Creates a new sale via POST /sales/create-sale
        Amounts are strictly integer cents (e.g. 3342 for R$ 33,42).
        """
        start_time = time.time()
        cents = int(amount_cents)

        name = (customer_name or "").strip()
        if len(name) < 3:
            name = "Apoiador Solidário"

        email = (customer_email or "").strip()
        if not email or "@" not in email:
            email = "doador@ajude-vakinha.com"

        phone = self.clean_digits(customer_phone)
        if len(phone) < 10:
            phone = "11998765432"

        doc_number = self.clean_digits(customer_document)
        if len(doc_number) not in [11, 14]:
            doc_number = "11144477735"

        ext_ref = external_ref or f"DONATION-{uuid.uuid4().hex[:12].upper()}"
        cb_url = postback_url or "https://ajude-vakinha.vercel.app/api/payments/webhook"

        payload = {
            "amount": cents,
            "currency": "BRL",
            "paymentMethod": "pix",
            "items": [
                {
                    "title": title or "Contribuição Sementes do Amanhã",
                    "unitPrice": cents,
                    "quantity": 1,
                    "tangible": False
                }
            ],
            "customer": {
                "name": name,
                "email": email,
                "phone": phone,
                "document": {
                    "number": doc_number,
                    "type": document_type.lower() if document_type else "cpf"
                }
            },
            "pix": {
                "expiresInDays": max(1, int(expires_in_days or 1))
            },
            "postbackUrl": cb_url,
            "metadata": "Doação Vaquinha - Sementes do Amanhã",
            "externalRef": ext_ref
        }

        # Inject UTM parameters if available
        if utms and isinstance(utms, dict):
            for utm_k in ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"]:
                val = utms.get(utm_k)
                if val:
                    payload[utm_k] = str(val).strip()

        url = f"{self.base_url}/sales/create-sale"
        req_body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=req_body, headers=self._get_headers(), method="POST")

        print(f"[Blackcat POST /sales/create-sale] ext_ref={ext_ref} amount_cents={cents}", flush=True)

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                elapsed_ms = round((time.time() - start_time) * 1000)
                raw_bytes = resp.read()
                data = json.loads(raw_bytes.decode("utf-8")) if raw_bytes else {}
                print(f"[Blackcat Success] HTTP {resp.status} in {elapsed_ms}ms tx_id={data.get('data', {}).get('transactionId')}", flush=True)

                sale_data = data.get("data", {})
                pay_data = sale_data.get("paymentData", {})

                qr_code_b64 = pay_data.get("qrCodeBase64", "")
                copy_paste = pay_data.get("copyPaste", "") or pay_data.get("qrCode", "")

                return {
                    "success": True,
                    "transactionId": sale_data.get("transactionId"),
                    "status": sale_data.get("status", "PENDING"),
                    "amount": sale_data.get("amount", cents),
                    "netAmount": sale_data.get("netAmount"),
                    "fees": sale_data.get("fees"),
                    "invoiceUrl": sale_data.get("invoiceUrl"),
                    "createdAt": sale_data.get("createdAt"),
                    "qrCodeBase64": qr_code_b64,
                    "qrCode": pay_data.get("qrCode", ""),
                    "copyPaste": copy_paste,
                    "expiresAt": pay_data.get("expiresAt", ""),
                    "raw": data
                }

        except urllib.error.HTTPError as e:
            elapsed_ms = round((time.time() - start_time) * 1000)
            err_body = ""
            try:
                err_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            print(f"[Blackcat HTTP Error {e.code}] in {elapsed_ms}ms: {err_body[:250]}", flush=True)

            msg = "Não foi possível gerar o Pix agora. Confira os dados e tente novamente."
            err_detail = None
            try:
                err_json = json.loads(err_body)
                msg = err_json.get("message") or err_json.get("error") or msg
                err_detail = err_json
            except Exception:
                pass

            err = BlackcatError(msg, status_code=e.code, error_detail=err_detail, raw_body=err_body)
            err.elapsed_ms = elapsed_ms
            raise err

        except Exception as e:
            elapsed_ms = round((time.time() - start_time) * 1000)
            print(f"[Blackcat Unexpected Error] in {elapsed_ms}ms: {type(e).__name__} {e}", flush=True)
            raise BlackcatError(
                "Não foi possível conectar ao gateway Blackcat. Tente novamente em instantes.",
                status_code=502,
                error_detail={"exception": str(e)}
            )

    def get_status(self, transaction_id):
        """
        Queries status via GET /sales/{transactionId}/status
        """
        tx_id = urllib.parse.quote(str(transaction_id or '').strip())
        url = f"{self.base_url}/sales/{tx_id}/status"
        req = urllib.request.Request(url, headers=self._get_headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                res_body = resp.read().decode("utf-8")
                data = json.loads(res_body) if res_body else {}
                sale_data = data.get("data", {})
                st = str(sale_data.get("status", "PENDING")).upper()
                is_paid = (st == "PAID")
                amt = int(sale_data.get("amount", 0))
                return {
                    "success": True,
                    "status": "paid" if is_paid else ("cancelled" if st in ["CANCELLED", "REFUNDED"] else "pending"),
                    "raw_status": st,
                    "transactionId": sale_data.get("transactionId", transaction_id),
                    "amount_cents": amt,
                    "netAmount": sale_data.get("netAmount"),
                    "fees": sale_data.get("fees"),
                    "paidAt": sale_data.get("paidAt"),
                    "endToEndId": sale_data.get("endToEndId"),
                    "raw": data
                }
        except urllib.error.HTTPError as e:
            return {"success": False, "status_code": e.code, "error": "HTTP Error"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_seller_info(self):
        """
        Queries seller details via GET /sales/seller
        """
        url = f"{self.base_url}/sales/seller"
        req = urllib.request.Request(url, headers=self._get_headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                res_body = resp.read().decode("utf-8")
                return json.loads(res_body) if res_body else {}
        except urllib.error.HTTPError as e:
            return {"success": False, "status_code": e.code}
        except Exception as e:
            return {"success": False, "error": str(e)}
