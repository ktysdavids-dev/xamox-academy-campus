# Entrega · Eliminar alumnos + progreso + asistencia manual — Xamox Academy Campus

## Qué incluye
1. Botón "Eliminar alumno" (con confirmación) en su ficha. Borra su cuenta,
   matrículas y progreso; NO borra su historial de compras en Stripe/Purchase
   (queda intacto para tu contabilidad).
2. Ficha de alumno rediseñada: matrículas de curso completo, módulos sueltos,
   y una tabla por cada clase con: ¿la completó?, ¿cuándo abrió el vídeo por
   última vez? (dato que ya se registraba, ahora visible).
3. Asistencia en directo MANUAL (checkbox + minutos conectado) por clase y
   alumno. Es un registro que tú rellenas a mano tras cada sesión — funciona
   con Zoom, Meet o cualquier otra plataforma, sin depender de una API.

## Por qué la asistencia es manual por ahora
Zoom y Meet funcionan muy distinto por API:
- Zoom: webhooks con "entró/salió de la reunión" y duración exacta — fácil
  de automatizar.
- Google Meet: requiere permisos de administrador de Google Workspace y es
  más limitado (no todos los planes lo permiten).
Como aún no has decidido cuál usarás, monté el campo manual para que puedas
llevar el control YA, y en cuanto elijas plataforma lo conectamos automático
sin tocar el resto del sistema (el campo attended_live/attended_minutes ya
existe, solo cambiaría quién lo rellena: tú o un webhook).

## Verificado con tests reales
- Ficha de alumno muestra correctamente qué clases abrió y cuáles no        OK
- Marcar asistencia con minutos se guarda bien                             OK
- Un alumno normal NO puede marcar asistencia de nadie (403)                OK
- Eliminar alumno borra en cascada (matrículas, progreso) sin tocar Purchase OK
- Un alumno normal NO puede eliminar a otro alumno (403)                    OK

## Archivos
NUEVO:
- core/migrations/0005_lessonprogress_attended_live_and_more.py

MODIFICADOS:
- core/models.py    (+ LessonProgress.attended_live, attended_minutes)
- core/services.py  (+ get_student_accessible_lessons)
- core/views.py     (admin_student_detail reescrito; + admin_student_delete,
                      admin_mark_attendance)
- core/urls.py      (+ 2 rutas nuevas)
- templates/core/admin_student_detail.html (reescrita completa)
- static/css/app.css (+ .attend-form)

## Instalación
    git checkout -b feature/gestion-alumnos
    git add -A
    git commit -m "Eliminar alumnos, progreso detallado y asistencia manual"
    git push -u origin feature/gestion-alumnos
    # PR -> main -> mergear. Railway aplica la migracion 0005 sola.
