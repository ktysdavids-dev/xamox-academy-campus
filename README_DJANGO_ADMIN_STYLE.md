# Entrega · Rediseño del Django Admin (backoffice técnico) — Xamox Academy Campus

## Qué era el problema
Ya existía una personalización parcial (cabecera con tu logo, colores de botones)
en templates/admin/base_site.html — pero la pantalla principal (el listado de
"Grupos + Añadir/Modificar" que se veía plano) usaba la plantilla por defecto
de Django sin ningún estilo, por eso se veía descuidada.

## Qué se hizo
Nuevo templates/admin/index.html que sustituye esa pantalla por un dashboard
de tarjetas (una por app: Autenticación, Core...) con cada modelo en su fila,
botones "+ Añadir" / "Modificar" con estilo consistente al resto del Campus,
y la barra de "Acciones recientes" repintada con el mismo esquema de color
(antes tenía un problema de contraste, texto casi invisible).

## Archivo nuevo
- templates/admin/index.html

## Verificado
- GET /django-admin/ como staff -> 200, sin errores de plantilla.
- Capturado visualmente (servidor real + render), corregidos 2 bugs
  encontrados en el proceso: título invisible por contraste, y un
  encabezado "Control del Campus" duplicado.

## Recordatorio
Esta pantalla (/django-admin/) es el backoffice TÉCNICO — para el día a día
(alumnos, matrículas, clases y recursos) sigue usando /admin-panel/, que ya
tiene el diseño completo de tu marca. Este cambio solo hace que, si alguna
vez entras aquí (para algo puntual tipo Purchases o SeatInvitations que no
tienen pantalla propia todavía), no se vea descuidado.

## Instalación
    git checkout -b feature/django-admin-style
    git add -A
    git commit -m "Rediseñar dashboard de Django Admin con tarjetas de marca"
    git push -u origin feature/django-admin-style
    # PR -> main -> mergear. Sin migraciones, deploy rápido.
