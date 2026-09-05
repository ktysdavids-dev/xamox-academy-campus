from django.core.management.base import BaseCommand
from core.models import AnswerOption, Challenge, Module, Question


QUESTIONS = [
    ("Fundamentos", "single", "¿Qué describe mejor un modelo de lenguaje grande (LLM)?", [
        ("Una base de datos con respuestas pregrabadas", False),
        ("Un modelo que genera lenguaje prediciendo secuencias a partir de patrones aprendidos", True),
        ("Un buscador que siempre consulta Internet antes de responder", False),
        ("Un sistema que únicamente resume documentos", False),
    ], "Un LLM genera texto a partir de patrones aprendidos y probabilidades; no es simplemente una base de datos ni un buscador."),
    ("Fundamentos", "single", "¿Qué relación representa mejor IA, Machine Learning y Deep Learning?", [
        ("Son exactamente lo mismo", False),
        ("Deep Learning contiene a la IA", False),
        ("La IA es el campo amplio; Machine Learning es un subconjunto y Deep Learning un subconjunto de ML", True),
        ("Machine Learning solo sirve para imágenes", False),
    ], "La IA es el concepto más amplio. ML aprende patrones de datos y Deep Learning utiliza redes neuronales profundas dentro de ML."),
    ("Modelos", "true_false", "Un modelo de IA puede generar una respuesta convincente y, aun así, equivocarse.", [("Verdadero", True), ("Falso", False)], "La fluidez de una respuesta no demuestra que sea cierta. La información crítica debe verificarse."),
    ("Modelos", "single", "¿Qué es un token en el contexto de un LLM?", [
        ("Una contraseña para acceder al modelo", False),
        ("Una unidad en la que el modelo divide y procesa texto", True),
        ("Una fuente de Internet", False),
        ("Un tipo de imagen generada", False),
    ], "Los modelos procesan texto en unidades llamadas tokens, que pueden ser palabras completas, fragmentos o signos."),
    ("Modelos", "single", "¿Qué es la ventana de contexto?", [
        ("El número máximo de usuarios de una IA", False),
        ("La cantidad de información que el modelo puede tener disponible en una interacción", True),
        ("La velocidad de conexión", False),
        ("El número de imágenes que genera", False),
    ], "La ventana de contexto delimita cuánta información puede considerar el modelo en una interacción."),
    ("Prompting", "single", "¿Cuál de estos prompts ofrece más control sobre el resultado?", [
        ("Hazme una campaña", False),
        ("Escribe algo para Instagram", False),
        ("Actúa como estratega de performance, define objetivo, público, oferta, tono, formato y criterios de calidad", True),
        ("Dame ideas buenas", False),
    ], "Un prompt estructurado reduce ambigüedad porque define rol, objetivo, contexto, condiciones, formato y criterios."),
    ("Prompting", "single", "En el framework ROCCFC, ¿qué elemento explica la situación y los datos relevantes?", [
        ("Rol", False), ("Objetivo", False), ("Contexto", True), ("Formato", False)
    ], "El contexto aporta al modelo la información necesaria para resolver la tarea con precisión."),
    ("Prompting", "true_false", "Un prompt extremadamente largo es siempre mejor que uno breve.", [("Verdadero", False), ("Falso", True)], "La calidad depende de relevancia, estructura y claridad, no de longitud. Más texto irrelevante también puede degradar el resultado."),
    ("Prompting", "single", "¿Qué técnica consiste en mostrar al modelo varios ejemplos antes de pedir una nueva respuesta?", [
        ("Few-shot prompting", True), ("Tokenización", False), ("Temperatura cero", False), ("Fine-tuning automático", False)
    ], "Few-shot prompting proporciona ejemplos para que el modelo infiera el patrón deseado."),
    ("Validación", "single", "La IA te entrega una cifra financiera concreta sin fuente. ¿Cuál es la mejor acción?", [
        ("Publicarla porque parece precisa", False),
        ("Pedirle que la escriba con más seguridad", False),
        ("Verificarla en fuentes fiables antes de utilizarla", True),
        ("Cambiar el tono de la respuesta", False),
    ], "Las cifras críticas requieren contraste con fuentes fiables. Una respuesta precisa en apariencia puede ser incorrecta."),
    ("Validación", "single", "¿Qué es una alucinación de IA?", [
        ("Una animación generada por IA", False),
        ("Información generada que parece plausible pero es falsa o no está respaldada", True),
        ("Una respuesta muy creativa", False),
        ("Un fallo de Internet", False),
    ], "Una alucinación ocurre cuando el modelo produce información no respaldada y la presenta como plausible."),
    ("Herramientas", "single", "¿Cuál es el mejor criterio para elegir una herramienta de IA?", [
        ("Que sea la más viral", False),
        ("Que tenga más funciones aunque no las uses", False),
        ("Que resuelva el problema concreto con calidad, coste, privacidad e integración adecuados", True),
        ("Que tenga el logo más conocido", False),
    ], "La herramienta debe seleccionarse por ajuste al problema, fiabilidad, coste, privacidad e integraciones."),
    ("Workflows", "single", "¿Cuál es la diferencia principal entre un prompt aislado y un workflow?", [
        ("Un workflow conecta varias etapas, entradas, decisiones y acciones", True),
        ("Un prompt aislado siempre usa más IA", False),
        ("No existe diferencia", False),
        ("Un workflow solo sirve para vídeo", False),
    ], "Un workflow convierte una tarea puntual en un proceso con etapas conectadas y potencialmente automatizables."),
    ("Workflows", "single", "¿Qué significa human-in-the-loop?", [
        ("Eliminar por completo la intervención humana", False),
        ("Mantener supervisión o aprobación humana en puntos críticos del proceso", True),
        ("Entrenar personalmente un modelo desde cero", False),
        ("Trabajar sin automatizaciones", False),
    ], "Human-in-the-loop mantiene control humano donde existen riesgos, decisiones sensibles o necesidad de validación."),
    ("Seguridad", "true_false", "Es buena práctica pegar datos personales o secretos empresariales en cualquier herramienta de IA sin revisar su política de datos.", [("Verdadero", False), ("Falso", True)], "Antes de compartir información sensible hay que revisar políticas de privacidad, configuración y necesidad real del dato."),
    ("Multimodalidad", "single", "Necesitas analizar un PDF con texto, tablas e imágenes. ¿Qué capacidad priorizarías?", [
        ("Generación de audio", False), ("Capacidad multimodal y contexto suficiente", True), ("Solo velocidad", False), ("Generación de vídeo", False)
    ], "Para documentos mixtos importan la multimodalidad, la comprensión documental y una ventana de contexto adecuada."),
    ("Productividad", "single", "¿Qué estrategia suele ser mejor para una tarea compleja?", [
        ("Resolver todo con una instrucción vaga", False),
        ("Descomponer el trabajo en investigación, producción, revisión y validación", True),
        ("Repetir el mismo prompt hasta acertar", False),
        ("Evitar definir formato", False),
    ], "Descomponer tareas complejas mejora control, trazabilidad y calidad."),
    ("Criterio profesional", "true_false", "La IA debe sustituir el criterio profesional en decisiones jurídicas, médicas, fiscales o financieras críticas.", [("Verdadero", False), ("Falso", True)], "La IA puede asistir, pero las decisiones de alto impacto requieren fuentes fiables y profesionales cualificados cuando corresponda."),
    ("Prompting", "single", "¿Para qué sirve definir el formato de salida en un prompt?", [
        ("Para aumentar el precio del modelo", False),
        ("Para indicar cómo debe estructurarse la respuesta: tabla, JSON, lista, informe, etc.", True),
        ("Para activar Internet", False),
        ("Para cambiar el idioma del sistema operativo", False),
    ], "Definir formato convierte una respuesta genérica en una salida directamente utilizable por personas o sistemas."),
    ("Workflows", "single", "Un formulario recibe un lead. ¿Cuál sería un workflow razonable?", [
        ("Formulario → IA analiza → clasifica → CRM → respuesta/seguimiento", True),
        ("Formulario → borrar datos → terminar", False),
        ("Formulario → generar imagen → terminar", False),
        ("Formulario → cambiar contraseña → CRM", False),
    ], "El valor está en conectar entrada, análisis, clasificación, registro y siguiente acción."),
]


class Command(BaseCommand):
    help = "Crea la V1 de Xamox Challenge para el Módulo 1"

    def handle(self, *args, **options):
        module = Module.objects.select_related("course").filter(course__slug="ia-marketing-digital", position=1).first()
        if not module:
            self.stderr.write("No existe el Módulo 1. Ejecuta primero seed_academy.")
            return

        configs = [
            (1, "Reto 1 · Fundamentos", "Comprueba que dominas IA, ML, LLM, tokens y contexto.", "practice", 5, 70, 3, 40),
            (2, "Reto 2 · Prompting profesional", "Aprende a distinguir instrucciones vagas de prompts profesionales.", "practice", 5, 70, 3, 50),
            (3, "Reto 3 · Detective de alucinaciones", "Entrena validación, pensamiento crítico y seguridad.", "practice", 5, 70, 3, 50),
            (4, "Reto 4 · Workflows", "Pasa de prompts aislados a procesos de trabajo con IA.", "practice", 5, 70, 3, 60),
            (5, "Examen final · Módulo 1", "Evaluación global de Fundamentos de Inteligencia Artificial.", "exam", 20, 70, 3, 100),
        ]
        challenges = {}
        for position, title, description, kind, count, pass_percent, max_attempts, xp in configs:
            obj, _ = Challenge.objects.update_or_create(
                module=module,
                slug=f"m1-{position}",
                defaults={"title": title, "description": description, "challenge_type": kind, "position": position,
                          "question_count": count, "pass_percent": pass_percent, "max_attempts": max_attempts,
                          "xp_reward": xp, "published": True},
            )
            challenges[position] = obj

        Question.objects.filter(module=module, category__in=[q[0] for q in QUESTIONS]).delete()
        for index, (category, qtype, prompt, options_list, explanation) in enumerate(QUESTIONS, start=1):
            q = Question.objects.create(module=module, category=category, question_type=qtype, prompt=prompt,
                                        explanation=explanation, difficulty="medium", points=10, active=True)
            for pos, (text, correct) in enumerate(options_list, start=1):
                AnswerOption.objects.create(question=q, text=text, is_correct=correct, position=pos)
            q.challenges.add(challenges[5])
            if category in {"Fundamentos", "Modelos", "Multimodalidad"}: q.challenges.add(challenges[1])
            if category in {"Prompting", "Productividad"}: q.challenges.add(challenges[2])
            if category in {"Validación", "Seguridad", "Criterio profesional"}: q.challenges.add(challenges[3])
            if category in {"Workflows", "Herramientas"}: q.challenges.add(challenges[4])

        self.stdout.write(self.style.SUCCESS(f"Xamox Challenge M1 creado: {len(QUESTIONS)} preguntas y {len(configs)} retos"))
