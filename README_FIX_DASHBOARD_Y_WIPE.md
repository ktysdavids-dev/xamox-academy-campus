# Fix · Enlaces del dashboard + borrado masivo de alumnos

## 1) Enlaces del dashboard (otro cabo suelto de la misma entrega perdida)
"+ Publicar clase" y los 4 accesos directos de abajo seguían apuntando al
Django Admin en bruto. Ahora:
- "+ Publicar clase" -> /admin-panel/contenido/ (el panel bonito)
- Acceso directo 01 "Contenido" -> /admin-panel/contenido/
- Acceso directo 02 "Alumnos" -> /admin-panel/alumnos/
- Acceso directo 03/04 (Cursos/Compras) -> se quedan en Django Admin,
  porque esas dos pantallas todavía no tienen versión propia.

## 2) Comando para borrar TODOS los alumnos de golpe
    python manage.py wipe_students            # solo TE ENSEÑA quién se borraría, no borra nada
    python manage.py wipe_students --confirm  # borra de verdad

Qué borra: cuentas de alumno, sus matrículas, accesos por módulo y progreso.
Qué NO borra: el historial de Purchase (compras de Stripe) ni tu cuenta de
admin — quedan intactos para tu contabilidad.

## Verificado con tests reales
- Sin --confirm: no borra nada, solo lista quién se borraría        OK
- Con --confirm: borra los alumnos, las Purchase siguen existiendo   OK
- El superusuario admin no se toca                                  OK

## Instalación
    git checkout -b fix/dashboard-links-y-wipe
    git add -A
    git commit -m "Fix enlaces del dashboard + comando para borrar alumnos de prueba"
    git push -u origin fix/dashboard-links-y-wipe
    # PR -> main -> mergear
