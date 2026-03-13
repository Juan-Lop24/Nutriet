"""
Backend de email de Django que usa la API de Resend.
Reemplaza SMTP sin cambiar nada en las vistas —
send_mail() sigue funcionando exactamente igual.
"""
import resend
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings


class ResendEmailBackend(BaseEmailBackend):

    def open(self):
        resend.api_key = getattr(settings, "RESEND_API_KEY", "")

    def close(self):
        pass

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        self.open()
        sent = 0

        for message in email_messages:
            try:
                to = message.to or []
                if not to:
                    continue

                # Preferir HTML si existe, si no texto plano
                body_html = None
                body_text = message.body

                for content, mimetype in getattr(message, "alternatives", []):
                    if mimetype == "text/html":
                        body_html = content
                        break

                params: resend.Emails.SendParams = {
                    "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
                    "to": to,
                    "subject": message.subject,
                }

                if body_html:
                    params["html"] = body_html
                    if body_text:
                        params["text"] = body_text
                else:
                    params["text"] = body_text

                if message.cc:
                    params["cc"] = message.cc
                if message.bcc:
                    params["bcc"] = message.bcc

                resend.Emails.send(params)
                sent += 1

            except Exception as e:
                if not self.fail_silently:
                    raise e

        return sent