# Entrega · Flujo 2x1 post-compra — Xamox Academy Campus

## Qué incluye
Formulario post-pago (elige **promoción 2 personas** o **una sola**), invitación de la
2ª plaza por email con token de un solo uso, página de aceptación, y gestión reinvitable
desde el dashboard del comprador. El pago se valida siempre por el **webhook** (fuente de
verdad) y además se revalida contra Stripe en la página post-compra.

## Archivos
MODIFICADOS:
- core/models.py            (SeatInvitation.invited_name)
- core/services.py          (process_paid_session, ensure_access_email, invite_second_seat,
                             accept_seat_invitation, set_single_seat, seats_status)
- core/views.py             (post_purchase, accept_invitation, invite_seat, webhook refactor)
- core/forms.py             (PostPurchaseForm, InviteSeatForm, AcceptInvitationForm)
- core/urls.py              (rutas /post-compra/, /invitacion/<token>/, /campus/invitar/)
- templates/core/dashboard.html   (bloque "Tu segunda plaza")
- static/css/app.css        (estilos del panel/plaza)

NUEVOS:
- core/migrations/0002_seatinvitation_invited_name.py
- templates/core/post_compra.html
- templates/registration/accept_invitation.html
- templates/emails/seat_invitation.html
- templates/emails/seat_invitation.txt

## Instalación (descomprime este zip SOBRE la raíz del repo)
    git checkout -b feature/2x1-post-compra
    git add -A
    git commit -m "2x1: formulario post-compra, invitacion de 2a plaza y aceptacion"
    git push -u origin feature/2x1-post-compra
    # merge a main -> Railway despliega y aplica la migracion 0002 en el startCommand

## Configurar en Stripe (una vez)
Payment Link -> After payment -> "Redirect customers to your website":
    https://xamox-academy-campus-production.up.railway.app/post-compra/?session_id={CHECKOUT_SESSION_ID}
(cuando actives campus.ktysdavids.com, cambia el dominio)

## Requisitos ya presentes en Railway
- STRIPE_SECRET_KEY  (necesaria: la página post-compra la usa para revalidar el pago)
- APP_URL            (para construir los enlaces de activación/invitación)
- SMTP IONOS (hola@ktysdavids.com)

## Probar el email antes de una compra real
    python manage.py sendtestemail tu-correo@gmail.com
