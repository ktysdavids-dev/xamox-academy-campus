from django.core.management.base import BaseCommand
from core.models import AnswerOption, Challenge, Course, Module, Question

COURSE_SLUG = "ia-marketing-digital"

MODULE_CONTENT = {
    1: {
        "categories": ["Fundamentos", "Modelos", "Prompting", "Validación", "Workflows"],
        "objective": [
            ("Fundamentos", "¿Qué describe mejor un LLM?", ["Una base de datos de respuestas", "Un modelo que predice secuencias de tokens a partir de patrones aprendidos", "Un buscador que siempre navega Internet", "Un sistema exclusivo para resumir"], 1, "Un LLM genera lenguaje mediante predicción probabilística; no garantiza verdad ni navegación web."),
            ("Fundamentos", "¿Cuál es la relación más correcta entre IA, Machine Learning y Deep Learning?", ["Son sinónimos", "IA ⊃ Machine Learning ⊃ Deep Learning", "Deep Learning contiene toda la IA", "Machine Learning solo sirve para texto"], 1, "IA es el campo amplio; ML es un subconjunto y Deep Learning un subconjunto de ML."),
            ("Modelos", "Una respuesta muy fluida de un modelo significa que el dato es fiable.", ["Verdadero", "Falso"], 1, "Fluidez y veracidad son propiedades distintas. Los datos críticos deben verificarse."),
            ("Modelos", "¿Qué es el contexto en una interacción con un modelo?", ["Solo la última palabra", "La información disponible para generar la respuesta actual", "La memoria permanente del proveedor", "Una contraseña"], 1, "El contexto es la información que el modelo tiene disponible en esa interacción; no equivale a memoria permanente."),
            ("Prompting", "¿Qué elemento mejora más un prompt profesional?", ["Pedir 'hazlo mejor'", "Definir objetivo, contexto, restricciones, formato y criterios", "Usar muchas mayúsculas", "Añadir diez roles incompatibles"], 1, "La claridad operacional reduce ambigüedad y facilita evaluar el resultado."),
            ("Prompting", "Few-shot significa…", ["No dar ningún ejemplo", "Dar uno o varios ejemplos del comportamiento deseado", "Entrenar un modelo desde cero", "Reducir el contexto"], 1, "Few-shot aporta ejemplos dentro del contexto para orientar patrón, formato o criterio."),
            ("Validación", "Si necesitas una cifra legal o financiera actual, ¿qué enfoque es más sólido?", ["Confiar en la primera respuesta", "Pedir seguridad absoluta", "Usar fuente actual/retrieval y verificarla", "Subir la temperatura"], 2, "En información sensible o cambiante hay que usar fuentes apropiadas y comprobarlas."),
            ("Validación", "Pedir al modelo que cite fuentes garantiza que las referencias existan.", ["Verdadero", "Falso"], 1, "Un modelo puede inventar citas. La verificación externa sigue siendo necesaria."),
            ("Workflows", "¿Qué convierte un prompt aislado en un workflow profesional?", ["Que sea más largo", "Una secuencia repetible con entradas, controles, salidas y revisión", "Usar emojis", "Copiarlo en varios chats"], 1, "Un workflow define proceso, control de calidad y responsabilidad humana, no solo texto de instrucción."),
            ("Workflows", "¿Dónde conviene mantener revisión humana?", ["En ninguna tarea", "En decisiones de impacto, publicación o datos sensibles", "Solo en traducciones", "Solo cuando falla Internet"], 1, "Human-in-the-loop es clave cuando el coste del error es relevante."),
        ],
        "labs": [
            ("Prompting", "Redacta un prompt profesional para pedir a una IA un análisis de competencia de una academia online sin inventar datos.", "Debe incluir rol, objetivo, contexto, fuentes o datos disponibles, prohibición de inventar, formato de salida y criterios de calidad."),
            ("Validación", "Diseña un protocolo de 5 pasos para revisar una respuesta de IA antes de publicarla en la web de una empresa.", "Una solución sólida separa hechos/opiniones, verifica afirmaciones críticas, contrasta fuentes, revisa tono/compliance y exige aprobación humana final."),
            ("Workflows", "Diseña un workflow humano+IA para convertir una reunión en tareas accionables.", "Entrada: transcripción. IA: resumen, decisiones, responsables y fechas. Validación humana: corregir asignaciones. Salida: tareas estructuradas en la herramienta de gestión."),
        ],
    },
    2: {
        "categories": ["Agentes", "Bots", "Automatización", "Integraciones", "Seguridad"],
        "objective": [
            ("Agentes", "¿Qué diferencia mejor a un agente de un chat simple?", ["Siempre tiene avatar", "Puede seguir un objetivo y usar herramientas/acciones dentro de un flujo", "Es necesariamente autónomo al 100%", "Solo funciona por voz"], 1, "Un agente combina modelo, instrucciones, estado y herramientas; la autonomía puede ser limitada."),
            ("Agentes", "Un agente debería tener acceso ilimitado a todas las herramientas disponibles.", ["Verdadero", "Falso"], 1, "El principio de mínimo privilegio reduce errores y riesgo de acciones indebidas."),
            ("Bots", "Para un bot de atención, ¿qué información debe escalarse a una persona?", ["Nada", "Casos sensibles, excepciones y situaciones fuera de política", "Solo saludos", "Toda pregunta simple"], 1, "Un buen diseño define límites y rutas de escalado humano."),
            ("Bots", "¿Qué canal exige especial cuidado con consentimiento y políticas de mensajería?", ["WhatsApp", "Un archivo local", "Una calculadora", "Un editor de texto"], 0, "WhatsApp y otros canales de mensajería requieren respetar consentimiento, plantillas y políticas del proveedor."),
            ("Automatización", "¿Qué papel cumple un webhook?", ["Decorar una interfaz", "Notificar eventos entre sistemas mediante HTTP", "Guardar contraseñas", "Entrenar un LLM"], 1, "Un webhook permite reaccionar a eventos y encadenar sistemas."),
            ("Automatización", "¿Qué característica ayuda a que una automatización sea robusta?", ["No registrar errores", "Idempotencia, reintentos controlados y logs", "Duplicar cada acción", "Evitar validaciones"], 1, "La robustez requiere controlar repeticiones, fallos y trazabilidad."),
            ("Integraciones", "¿Qué suele identificar un recurso en una API?", ["Un endpoint/ID", "Un color", "Una contraseña compartida públicamente", "Un emoji"], 0, "Las APIs exponen recursos mediante endpoints y normalmente identificadores."),
            ("Integraciones", "¿Dónde deben almacenarse claves API?", ["En el HTML público", "En variables/secretos seguros del entorno", "En capturas de pantalla", "En el nombre del repositorio"], 1, "Los secretos no deben estar en código público ni cliente web."),
            ("Seguridad", "¿Qué es prompt injection en un sistema con herramientas?", ["Un error de CSS", "Una instrucción maliciosa que intenta alterar el comportamiento del agente", "Un tipo de base de datos", "Una compresión de texto"], 1, "El contenido no confiable puede intentar manipular instrucciones; hay que aislar datos, permisos y políticas."),
            ("Seguridad", "¿Es recomendable permitir que un bot ejecute pagos sin confirmación en un flujo sensible?", ["Sí, siempre", "No; conviene añadir autorización y controles explícitos", "Solo si responde rápido", "Da igual"], 1, "Las acciones de alto impacto requieren controles y, a menudo, confirmación humana."),
        ],
        "labs": [
            ("Bots", "Diseña el flujo de un bot de WhatsApp que cualifique un lead y reserve una llamada sin presionar al usuario.", "Debe solicitar consentimiento, recoger datos mínimos, cualificar, ofrecer horarios, crear reserva, confirmar y permitir salir o escalar a una persona."),
            ("Automatización", "Diseña un flujo Make/n8n: formulario → CRM → email → aviso interno. Incluye cómo evitar duplicados.", "Usar un identificador único del lead, buscar antes de crear, aplicar upsert/idempotencia, registrar estado y manejar reintentos."),
            ("Seguridad", "Define permisos mínimos para un agente que consulta calendario y propone reuniones.", "Lectura de disponibilidad + creación limitada de eventos; sin acceso a correo completo, facturación u otras herramientas innecesarias. Confirmación antes de enviar invitaciones sensibles."),
        ],
    },
    3: {
        "categories": ["Código IA", "GitHub", "Testing", "Cloud", "Seguridad"],
        "objective": [
            ("Código IA", "¿Cuál es un uso profesional del copiloto de código?", ["Aceptar todo sin revisar", "Generar, explicar y refactorizar con revisión y tests", "Publicar secretos", "Eliminar control de versiones"], 1, "La IA acelera desarrollo, pero la responsabilidad sobre calidad y seguridad sigue siendo humana."),
            ("Código IA", "Un fragmento de código generado por IA es seguro porque compila.", ["Verdadero", "Falso"], 1, "Compilar no demuestra seguridad, corrección lógica ni cumplimiento."),
            ("GitHub", "¿Para qué sirve una rama Git?", ["Aislar cambios antes de integrarlos", "Guardar contraseñas", "Aumentar RAM", "Sustituir una base de datos"], 0, "Las ramas permiten desarrollar y revisar cambios de forma aislada."),
            ("GitHub", "¿Qué aporta un Pull Request?", ["Revisión, discusión e integración controlada de cambios", "Más velocidad de Internet", "Un dominio web", "Una factura"], 0, "El PR es una unidad de colaboración y revisión antes de integrar código."),
            ("Testing", "¿Qué test comprueba una unidad pequeña de lógica de forma aislada?", ["Unit test", "SEO test", "DNS test", "Brand test"], 0, "Los tests unitarios validan funciones o componentes acotados."),
            ("Testing", "¿Qué debe ocurrir antes de desplegar un cambio crítico?", ["Nada", "Tests, revisión y plan de rollback", "Borrar historial Git", "Cambiar el logo"], 1, "Un pipeline seguro reduce riesgo y permite revertir."),
            ("Cloud", "¿Qué suele contener una variable de entorno?", ["Configuración dependiente del entorno y secretos", "Solo CSS", "Imágenes", "Comentarios de usuarios"], 0, "Las variables de entorno desacoplan configuración y secretos del código."),
            ("Cloud", "¿Qué es una migración de base de datos?", ["Un cambio versionado del esquema/datos", "Un backup de fotos", "Un diseño visual", "Un dominio"], 0, "Las migraciones evolucionan el esquema de forma controlada."),
            ("Seguridad", "¿Qué debe hacerse si una API key se publica por error en GitHub?", ["Ignorarlo", "Revocarla/rotarla y eliminar exposición", "Cambiar el README", "Ocultar el repositorio y mantener la misma clave"], 1, "Una clave expuesta debe considerarse comprometida y rotarse."),
            ("Seguridad", "¿Dónde debe validarse una autorización sensible?", ["Solo en JavaScript del navegador", "En servidor/backend", "En CSS", "En el nombre del botón"], 1, "La autorización real debe aplicarse en servidor; el cliente puede ser manipulado."),
        ],
        "labs": [
            ("Código IA", "Pide a una IA que implemente una nueva función en una app. Escribe el checklist que usarías antes de aceptar el código.", "Revisar requisitos, diff, dependencias, seguridad, tests, casos límite, logs, rendimiento, estilo, migraciones y rollback."),
            ("GitHub", "Diseña un flujo de trabajo GitHub para desarrollar una función sin romper producción.", "Issue/requisito → rama feature → commits pequeños → tests → PR → revisión → merge → CI/CD → monitorización y rollback."),
            ("Cloud", "Describe cómo desplegarías una app Django con PostgreSQL sin guardar secretos en Git.", "Repositorio sin secretos, variables de entorno en proveedor cloud, base PostgreSQL, migrate/collectstatic en despliegue, healthcheck, HTTPS y logs."),
        ],
    },
    4: {
        "categories": ["Contenido", "Estrategia", "Imagen y vídeo", "APIs", "Publicación"],
        "objective": [
            ("Contenido", "¿Qué debe definirse antes de generar 30 publicaciones con IA?", ["Solo la herramienta", "Objetivo, audiencia, pilares, tono y criterios", "El número de emojis", "Una contraseña"], 1, "La estrategia precede a la generación; sin criterios el volumen no garantiza calidad."),
            ("Contenido", "Automatizar contenido elimina la necesidad de revisión humana.", ["Verdadero", "Falso"], 1, "La revisión protege marca, exactitud, compliance y contexto."),
            ("Estrategia", "¿Qué métrica está más cerca de negocio que los likes?", ["Conversiones/leads cualificados", "Número de emojis", "Longitud del caption", "Cantidad de hashtags"], 0, "La métrica debe conectarse con el objetivo real de la campaña."),
            ("Estrategia", "¿Qué es un pilar de contenido?", ["Un tema recurrente alineado con audiencia y objetivo", "Un plugin", "Un tipo de archivo", "Un anuncio obligatorio"], 0, "Los pilares estructuran qué temas se trabajan de forma consistente."),
            ("Imagen y vídeo", "¿Qué mejora la consistencia visual al generar con IA?", ["Cambiar estilo en cada pieza", "Guía visual, referencias y criterios repetibles", "No revisar", "Usar texto aleatorio"], 1, "Las referencias y reglas de marca ayudan a mantener consistencia."),
            ("Imagen y vídeo", "¿Qué debe verificarse al usar una imagen generada comercialmente?", ["Nada", "Licencias/políticas, derechos, claims y posibles errores visuales", "Solo su resolución", "Solo el tamaño"], 1, "La publicación comercial requiere revisión legal, de marca y factual."),
            ("APIs", "¿Qué ventaja aporta una API de red social frente a automatizar clics del navegador?", ["Integración oficial y estructurada", "Evita cualquier política", "No necesita autenticación", "Siempre es gratuita"], 0, "Las APIs oficiales ofrecen interfaces estables y reglas explícitas, aunque tienen límites y permisos."),
            ("APIs", "¿Qué es rate limiting?", ["Límite de solicitudes en un periodo", "Un filtro de imagen", "Un formato de vídeo", "Un tipo de copy"], 0, "Las APIs limitan frecuencia/volumen y el sistema debe manejar esos límites."),
            ("Publicación", "¿Qué patrón reduce publicaciones duplicadas?", ["Reintentar sin control", "Guardar ID/estado y aplicar idempotencia", "Cambiar el título", "Publicar dos veces para confirmar"], 1, "Guardar estado e identificadores permite saber si una pieza ya fue procesada."),
            ("Publicación", "¿Qué conviene registrar en un pipeline de contenidos?", ["Estado, timestamps, canal, IDs de publicación y errores", "Solo el color", "Solo el autor", "Nada"], 0, "La trazabilidad permite operar y corregir automatizaciones a escala."),
        ],
        "labs": [
            ("Estrategia", "Diseña una semana de contenido para una academia de IA con tres pilares y un CTA medible.", "Definir audiencia/objetivo, 3 pilares, formatos por canal, mensajes, CTA con destino medible y criterio de éxito por pieza."),
            ("Contenido", "Crea un checklist para revisar una publicación generada por IA antes de programarla.", "Exactitud, tono de marca, valor real, CTA, ortografía, claims, derechos visuales, formato por canal y aprobación final."),
            ("Publicación", "Diseña un pipeline: idea → copy → imagen/vídeo → aprobación → publicación → analítica.", "Cada etapa debe tener entrada/salida, estado, responsable, almacenamiento de assets, aprobación humana, API de publicación y captura posterior de métricas."),
        ],
    },
}

GAME_SPECS = [
    (1, "Radar IA", "radar", "practice", 4, 70, 5, 45, "Entrena conceptos esenciales con feedback inmediato."),
    (2, "Ruleta Xamox", "ruleta", "practice", 5, 70, 5, 60, "Cada giro mezcla categorías para obligarte a pensar, no memorizar."),
    (3, "Reto Relámpago", "relampago", "practice", 5, 70, 5, 75, "Precisión bajo presión: 25 segundos por prueba y bonus por velocidad."),
    (4, "Laboratorio Profesional", "lab", "practice", 2, 0, 10, 80, "Resuelve casos reales y compara tu respuesta con un enfoque profesional."),
    (5, "Boss Final", "examen", "exam", 10, 70, 3, 120, "Demuestra dominio del módulo sin pistas hasta terminar."),
]


class Command(BaseCommand):
    help = "Crea/actualiza Xamox Arena para los cuatro módulos sin borrar contenido manual del admin."

    def handle(self, *args, **options):
        course = Course.objects.filter(slug=COURSE_SLUG).first()
        if not course:
            raise RuntimeError("Primero ejecuta: python manage.py seed_academy")

        total_questions = 0
        total_games = 0
        for position, content in MODULE_CONTENT.items():
            module = Module.objects.filter(course=course, position=position).first()
            if not module:
                self.stdout.write(self.style.WARNING(f"Módulo {position} no existe; se omite"))
                continue

            games = {}
            for game_position, title, suffix, game_type, count, pass_percent, attempts, xp, description in GAME_SPECS:
                slug = f"m{position}-{suffix}"
                game, _ = Challenge.objects.update_or_create(
                    module=module,
                    slug=slug,
                    defaults={
                        "title": f"{title} · Módulo {position}",
                        "description": description,
                        "challenge_type": game_type,
                        "position": game_position,
                        "question_count": count,
                        "pass_percent": pass_percent,
                        "max_attempts": attempts,
                        "xp_reward": xp,
                        "published": True,
                    },
                )
                games[suffix] = game
                total_games += 1

            objective_questions = []
            for index, (category, prompt, options_list, correct_index, explanation) in enumerate(content["objective"], start=1):
                q, _ = Question.objects.get_or_create(
                    module=module,
                    prompt=prompt,
                    defaults={
                        "category": category,
                        "question_type": "true_false" if len(options_list) == 2 and options_list == ["Verdadero", "Falso"] else "single",
                        "explanation": explanation,
                        "difficulty": "hard" if index in (7, 9, 10) else ("easy" if index <= 3 else "medium"),
                        "points": 10,
                        "active": True,
                    },
                )
                q.category = category
                q.explanation = explanation
                q.active = True
                q.save(update_fields=["category", "explanation", "active", "updated_at"])
                for opt_pos, text in enumerate(options_list, start=1):
                    opt, _ = AnswerOption.objects.get_or_create(question=q, text=text, defaults={"position": opt_pos})
                    opt.position = opt_pos
                    opt.is_correct = (opt_pos - 1 == correct_index)
                    opt.save(update_fields=["position", "is_correct", "updated_at"])
                objective_questions.append(q)
                total_questions += 1

            lab_questions = []
            for category, prompt, model_answer in content["labs"]:
                q, _ = Question.objects.get_or_create(
                    module=module,
                    prompt=prompt,
                    defaults={
                        "category": category,
                        "question_type": "text",
                        "model_answer": model_answer,
                        "explanation": "Compara estructura, criterio, controles y claridad. No busques copiar literalmente la solución.",
                        "difficulty": "hard",
                        "points": 20,
                        "active": True,
                    },
                )
                q.category = category
                q.question_type = "text"
                q.model_answer = model_answer
                q.active = True
                q.save(update_fields=["category", "question_type", "model_answer", "active", "updated_at"])
                lab_questions.append(q)
                total_questions += 1

            # Todos los objetivos alimentan Radar/Ruleta/Relámpago/Boss para que cada partida sea distinta.
            for suffix in ("radar", "ruleta", "relampago", "examen"):
                games[suffix].questions.set(objective_questions)
            games["lab"].questions.set(lab_questions)

        self.stdout.write(self.style.SUCCESS(f"Xamox Arena lista: {total_games} juegos y {total_questions} ejercicios base"))
