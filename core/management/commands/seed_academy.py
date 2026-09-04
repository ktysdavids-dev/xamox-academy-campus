from django.core.management.base import BaseCommand
from core.models import Course, Module
MODULES=[(1,"Fundamentos de IA","Modelos, prompting profesional, herramientas y flujos asistidos"),(2,"Agentes & Bots de IA","Voz, texto, telefonía, WhatsApp, CRM, n8n y Make"),(3,"Desarrollo con IA","Código asistido, GitHub, despliegue y publicación"),(4,"Redes + Contenido con IA","Contenido, estrategia, APIs y automatización de publicación")]
class Command(BaseCommand):
    def handle(self,*args,**options):
        course,_=Course.objects.get_or_create(slug="ia-marketing-digital",defaults={"title":"IA & Marketing Digital","description":"Programa Intensivo Xamox Academy · 48 h · 16 sesiones · 8 semanas","cover_image":"https://cdn.prod.website-files.com/68b944d4a42f90c19d14a5da/6a9af33ff4a396bb973294ed_ChatGPT%20Image%204%20sept%202026%2C%2016_59_29.webp","active":True})
        for position,title,description in MODULES: Module.objects.get_or_create(course=course,position=position,defaults={"title":title,"description":description,"published":True})
        self.stdout.write(self.style.SUCCESS("Xamox Academy inicializada"))
