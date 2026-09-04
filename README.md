# Xamox Academy Campus

Campus privado para alumnos de Xamox Academy, construido con Python + Django + PostgreSQL.

## Incluye
- login y roles
- panel alumno
- panel administrador
- cursos, módulos y clases
- subida de grabaciones y recursos desde Django Admin
- progreso por alumno
- matrículas
- compras Stripe y webhook base 2x1
- preparación Railway

## Local
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py makemigrations core
python manage.py migrate
python manage.py seed_academy
python manage.py createsuperuser
python manage.py runserver
```

## Admin
- Panel: `/admin-panel/`
- Django Admin: `/django-admin/`
- Webhook Stripe: `/webhooks/stripe/`
