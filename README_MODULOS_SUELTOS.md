# Entrega · Venta de módulos sueltos + acceso restringido — Xamox Academy Campus

## Qué resuelve
Hasta ahora el sistema solo entendía "todo o nada": una Enrollment daba acceso
al curso completo. Para vender módulos sueltos (con recargo del 35% para
empujar al bundle) hacía falta:
1. Que el webhook reconociera VARIOS productos de Stripe, no solo uno.
2. Que el acceso se pudiera limitar a un módulo concreto, sin dar el curso entero.

## Cómo funciona ahora
- El webhook ya NO filtra por Payment Link ID. En su lugar, consulta a Stripe
  qué Price ID exacto se compró y lo busca en la base de datos:
  - Si coincide con `Course.stripe_price_id` → acceso COMPLETO (como antes,
    incluye la promo 2x1).
  - Si coincide con `Module.stripe_price_id` → acceso SOLO a ese módulo
    (nuevo modelo `ModuleAccess`), sin 2x1, un asiento.
  - Si no coincide con nada → se ignora con 200 (por si hay otros productos
    de Stripe en la misma cuenta ajenos al Campus; no rompe ni reintenta).
- `course_detail`, `lesson_detail` y `protected_media` ahora comprueban:
  ¿tiene Enrollment completo? → ve todo. Si no, ¿tiene ModuleAccess a ESE
  módulo concreto? → solo ve eso. Si no tiene ninguno → 404.
- El dashboard del alumno muestra una sección "Acceso por módulo" para
  quienes compraron suelto, con un enlace para actualizar al curso completo.
- La página post-compra detecta si la compra fue "module" o "full" y muestra
  el formulario correspondiente (el 2x1 solo aparece para el curso completo).

## Verificado con tests reales (no solo revisión de código)
- Compra suelta de un módulo → SIN Enrollment completo, CON ModuleAccess    OK
- course_detail muestra SOLO el módulo comprado (por ID, no por texto)      OK
- lesson_detail: 200 en el módulo comprado, 404 en los demás                OK
- protected_media: confirmado con mock que el permiso deja pasar el
  recurso del módulo comprado y bloquea el de los demás                    OK
- Compra del CURSO COMPLETO sigue funcionando exactamente igual que antes   OK
- Comprar dos módulos sueltos distintos acumula acceso a ambos              OK
- Price ID no reconocido → error controlado, no rompe el webhook           OK
- session_id no colisiona en el simulador aunque se llame 2 veces seguidas  OK (bug encontrado y corregido en el proceso)

## Archivos
NUEVO:
- core/migrations/0004_course_stripe_price_id_module_stripe_price_id_and_more.py

MODIFICADOS:
- core/models.py     (+ Course.stripe_price_id, Module.stripe_price_id,
                       Purchase.scope, Purchase.module, + modelo ModuleAccess)
- core/services.py   (+ user_can_access_module/lesson, accessible_module_ids,
                       get_partial_access_summary, provision_module_access,
                       get_purchased_stripe_price_id; process_paid_session
                       reescrito para resolver por Price ID)
- core/views.py      (course_detail/lesson_detail/protected_media/dashboard
                       actualizados; post_purchase bifurca completo/suelto;
                       webhook ya no depende de un único Payment Link)
- core/forms.py      (+ ModuleNameForm)
- core/admin.py      (stripe_price_id visible en Course/Module, registrado
                       ModuleAccess, PurchaseAdmin mejorado con scope/módulo)
- core/management/commands/simular_compra.py (+ --modulo N, --price-id;
                       corregido bug de colisión de session_id)
- templates/core/post_compra.html  (rama module_only)
- templates/core/dashboard.html    (sección "Acceso por módulo")

## ⚠️ PASO CRÍTICO ANTES DE DESPLEGAR — no lo saltes
El webhook YA NO reconoce el pago por el Payment Link antiguo. Si despliegas
esto sin hacer lo siguiente, el CURSO COMPLETO DEJARÁ DE MATRICULAR AUTOMÁTICAMENTE:

1. En tu Stripe → Catálogo de productos → tu producto "Programa Intensivo..."
2. Copia su Price ID (empieza por `price_...`, NO el Payment Link `plink_...`
   ni el link `buy.stripe.com/...`).
3. En el Campus, entra a `/django-admin/core/course/`, abre el curso, pega
   ese Price ID en el campo `stripe_price_id`, guarda.
4. Solo entonces el webhook volverá a reconocer las compras del bundle.

## Instalación
    git checkout -b feature/modulos-sueltos
    git add -A
    git commit -m "Venta de modulos sueltos: acceso restringido + webhook multi-producto"
    git push -u origin feature/modulos-sueltos
    # PR -> main -> mergear. Railway aplica la migracion 0004 sola.
    # ⚠️ Inmediatamente después: pega el Price ID del curso completo (ver arriba)

## Cómo dar de alta cada módulo suelto en Stripe (repetir 4 veces)
1. Catálogo de productos → + Añadir producto.
2. Nombre: "Módulo 0X · <título> — Xamox Academy" (ver logos adjuntos).
3. Precio (recargo 35% ya aplicado): 305 € / 405 € / 405 € / 505 €.
4. Categoría fiscal: Servicios de formación (igual que el curso completo).
5. Guardar producto → copia su Price ID (`price_...`).
6. En el Campus → Django Admin → Modules → ese módulo → pega el Price ID
   en `stripe_price_id`, guarda.
7. Ve a "Payment Links" → crea uno para ese producto → en "After payment"
   configura Redirect a:
   https://xamox-academy-campus-production.up.railway.app/post-compra/?session_id={CHECKOUT_SESSION_ID}
8. Copia la URL del Payment Link (buy.stripe.com/...) — es la que va en el
   botón de ese módulo en la landing de Webflow.
