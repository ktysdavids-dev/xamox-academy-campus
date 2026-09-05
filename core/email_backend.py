"""
Backend de email para Django que envía a través de la API HTTPS de Resend
en lugar de SMTP. Se usa porque Railway bloquea los puertos SMTP salientes
(25/465/587) en los planes Free/Trial/Hobby; la API de Resend va por HTTPS
(puerto 443), que nunca se bloquea.

No cambia nada del código que ya envía emails (core/services.py sigue usando
EmailMultiAlternatives normal) — solo cambia el "transporte" final, activado
por la variable de entorno EMAIL_BACKEND=core.email_backend.ResendBackend.
"""
import logging

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger("core")


class ResendBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key = getattr(settings, "RESEND_API_KEY", "")
        if not api_key:
            if not self.fail_silently:
                raise RuntimeError("RESEND_API_KEY no está configurada en las variables de entorno")
            return 0

        import resend
        resend.api_key = api_key

        sent = 0
        for message in email_messages:
            try:
                html_body = None
                for content, mimetype in getattr(message, "alternatives", []) or []:
                    if mimetype == "text/html":
                        html_body = content
                        break

                params = {
                    "from": message.from_email,
                    "to": list(message.to),
                    "subject": message.subject,
                    "text": message.body,
                }
                if html_body:
                    params["html"] = html_body
                if message.reply_to:
                    params["reply_to"] = list(message.reply_to)
                if message.cc:
                    params["cc"] = list(message.cc)
                if message.bcc:
                    params["bcc"] = list(message.bcc)

                resend.Emails.send(params)
                sent += 1
            except Exception:
                logger.exception("Fallo enviando email vía Resend a %s", message.to)
                if not self.fail_silently:
                    raise
        return sent
