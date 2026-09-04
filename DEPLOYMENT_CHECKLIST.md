# Xamox Academy Campus — Railway checklist

Variables mínimas del servicio `xamox-academy-campus`:

- `DJANGO_SECRET_KEY` — valor secreto largo
- `DATABASE_URL` — referencia al servicio PostgreSQL, por ejemplo `${{Postgres--rXr.DATABASE_URL}}`
- `DJANGO_DEBUG=0`
- `APP_URL=https://xamox-academy-campus-production.up.railway.app`
- `ADMIN_USERNAME=admin`
- `ADMIN_EMAIL=info@ktysdavids.com`
- `ADMIN_PASSWORD` — contraseña privada del administrador
- `MEDIA_ROOT=/data/media` si existe volumen persistente montado en `/data`

No usar SQLite en producción Railway. El proyecto debe fallar el despliegue si Railway no dispone de `DATABASE_URL`.
