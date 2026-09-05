# Entrega · Vídeo largo (3h) vía Cloudflare Stream — Xamox Academy Campus

## Por qué este cambio
Railway corre este servicio con UN solo worker de Gunicorn. Subir/reproducir
grabaciones de 3h directamente como archivo en el Campus:
- Bloquearía ese worker mientras se sirve el vídeo (el webhook de Stripe no
  podría responder mientras tanto).
- Llenaría el volumen de Railway rápido (varios GB por clase x 16 clases).
- No soporta bien el "seek" (saltar en el vídeo) a esa escala.

Cloudflare Stream resuelve las tres cosas: la subida y la reproducción van
DIRECTAS entre el navegador y Cloudflare, nunca pasan por tu servidor. Solo
le pedimos a Cloudflare, por API, un "token" de reproducción firmado y de
caducidad corta (4h) cuando un alumno matriculado abre la clase.

## Coste real estimado (con datos de precios 2026 verificados)
- Almacenamiento: $5 / 1.000 minutos guardados al mes.
- Entrega: $1 / 1.000 minutos vistos.
- Con 16 clases x 3h = 48h = 2.880 min guardados -> ~14,40 $/mes de storage
  mientras el curso está activo (puedes borrar los vídeos al terminar).
- Con 1-2 alumnos viendo cada clase una vez -> unos 3-6 $ más de entrega.
- Total aproximado: 15-20 $/mes durante el curso. Muy por debajo de cualquier
  alternativa seria para vídeo largo protegido.

## Qué incluye esta entrega
NUEVO:
- core/migrations/0003_lesson_cf_stream_uid.py

MODIFICADOS:
- core/models.py       (+ Lesson.cf_stream_uid)
- core/services.py     (+ get_stream_iframe_src: pide token firmado a Cloudflare)
- core/views.py        (lesson_detail ahora prioriza Cloudflare Stream)
- core/forms.py         (+ campo cf_stream_uid, límite de 300MB en subida directa,
                         validación: se requiere Stream UID, URL o archivo)
- config/settings.py    (+ CF_ACCOUNT_ID, CF_STREAM_API_TOKEN)
- requirements.txt      (+ requests, pineado explícitamente)
- .env.example          (documentadas las nuevas variables)
- templates/core/admin_lesson_form.html  (recuadro explicando el flujo)
- templates/core/admin_content.html      (el listado ahora indica "vídeo en Cloudflare Stream")
- templates/core/lesson_detail.html      (reproduce vía iframe firmado si hay Stream UID)
- static/css/app.css    (+ estilo .stream-callout)

## Verificado con tests reales (Django test client + mocks)
- Crear clase SOLO con cf_stream_uid (sin video_url/video_file)         OK
- Subir archivo de 301 MB directo -> RECHAZADO con mensaje claro         OK
- Alumno matriculado abre la clase -> se llama a la API de Cloudflare
  con el Bearer token correcto -> se monta el iframe con el token        OK
- Cloudflare cae/falla -> la página no rompe, muestra aviso controlado    OK

## Instalación
    git checkout -b feature/cloudflare-stream
    git add -A
    git commit -m "Vídeo largo (3h) via Cloudflare Stream en vez de archivo directo"
    git push -u origin feature/cloudflare-stream
    # PR feature/cloudflare-stream -> main, revisar y mergear
    # Railway despliega y aplica la migración 0003 sola (en tu startCommand)

## Configuración en Railway (variables nuevas)
    CF_ACCOUNT_ID=<tu Account ID de Cloudflare>
    CF_STREAM_API_TOKEN=<token con permiso Stream:Edit>

## Cómo conseguir esos dos valores
1. Crea cuenta en cloudflare.com (o usa una que ya tengas).
2. En el dashboard, activa "Stream" (tiene un coste base, ver aviso de
   precios arriba). Aparece en el menú lateral.
3. El "Account ID" se ve en la barra lateral derecha del dashboard, en
   cualquier página del dominio/cuenta.
4. Ve a "My Profile" (arriba a la derecha) -> "API Tokens" -> "Create Token"
   -> plantilla o permiso personalizado con "Stream:Edit" -> Crear -> copiar
   el token (solo se ve una vez).
5. Pon ambos valores en Railway y redeploy.

## Cómo subir una grabación de 3h (flujo para cada clase)
1. Entra al dashboard de Cloudflare -> Stream -> "Upload a video".
2. Arrastra el archivo de la grabación (aguanta archivos grandes, es
   resumable — si se corta la subida, continúa sola).
3. Marca la opción "Require signed URLs" = activada (para que solo se
   pueda ver con el token que genera nuestro Campus, no con el enlace
   público).
4. Cuando termine de procesar, copia el "Video UID" que te muestra.
5. En el Campus -> Panel de administración -> Gestionar clases -> esa
   clase -> pega el UID en "ID de vídeo en Cloudflare Stream" -> guardar.
6. Publica la clase cuando esté lista.

## Cuándo SÍ usar la subida directa (video_file, máx. 300MB)
Solo para clips cortos complementarios (ej. un resumen de 5 minutos), nunca
para la grabación completa de una sesión de 3 horas.
