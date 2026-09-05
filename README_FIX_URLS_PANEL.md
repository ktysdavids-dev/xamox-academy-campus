# Fix · Rutas del panel de contenido no conectadas (404)

## Qué pasó (mi error, no tuyo)
En una entrega anterior (Cloudflare Stream), empaqueté por accidente los archivos
de vistas y plantillas del "panel de contenido" (views.py, templates/core/admin_content.html,
templates/core/admin_lesson_form.html) porque estaban en mi carpeta de trabajo — pero
se me olvidó incluir también los cambios de core/urls.py que conectan esas vistas
a una URL real. Resultado: el código para gestionar clases/recursos SÍ estaba
desplegado y funcionando por dentro, pero no había ninguna URL que llevara hasta
él → 404 "Extraviado" al entrar a /admin-panel/contenido/.

## Qué arregla este fix
Añade las 7 rutas que faltaban en core/urls.py:
- /admin-panel/contenido/
- /admin-panel/contenido/modulo/<id>/clase/nueva/
- /admin-panel/contenido/clase/<id>/editar/
- /admin-panel/contenido/clase/<id>/publicar/
- /admin-panel/contenido/clase/<id>/eliminar/
- /admin-panel/contenido/clase/<id>/recurso/nuevo/
- /admin-panel/contenido/recurso/<id>/eliminar/

No se toca ningún otro archivo. No hay migraciones nuevas.

## Verificado (no solo "debería funcionar")
- Las 7 rutas resuelven correctamente con `reverse()`.
- GET /admin-panel/contenido/ como staff -> 200 (antes: 404).
- GET a "nueva clase" de un módulo -> 200.

## Instalación
    git checkout -b fix/rutas-panel-contenido
    git add -A
    git commit -m "Fix: reconectar rutas del panel de contenido (404 -> 200)"
    git push -u origin fix/rutas-panel-contenido
    # PR -> main -> mergear. Deploy rapido, sin migraciones.
