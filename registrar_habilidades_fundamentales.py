from knowledge_base import KnowledgeBase

# Definición de las habilidades fundamentales del agente
datos_habilidades = {
    "descripcion": "Define las acciones atómicas y fundamentales que el agente puede ejecutar. Estas son las capacidades inherentes al 'cuerpo' del agente.",
    "acciones": [
        {
            "nombre": "pedir_aclaracion",
            "params": '{{ "pregunta": "<string>" }}',
            "descripcion": "Para hacer una pregunta al usuario si no estás seguro de cómo proceder"
        },
        {
            "nombre": "clic",
            "params": '{{ "x_rel": <float>, "y_rel": <float> }}',
            "descripcion": "IMPORTANTE: Coordenadas relativas a la pantalla, de 0.0 a 1.0"
        },
        {
            "nombre": "escribir",
            "params": '{{ "texto": "<string>" }}',
            "descripcion": "Escribe un texto en el campo activo"
        },
        {
            "nombre": "presionar_tecla",
            "params": '{{ "tecla": "<string>" }}',
            "descripcion": "Presiona una tecla o combinación de teclas (ej: \"enter\", \"win\", \"alt+f4\")"
        },
        {
            "nombre": "scroll",
            "params": '{{ "direccion": "<arriba|abajo>", "clics": <int> }}',
            "descripcion": "Hace scroll hacia arriba o hacia abajo"
        },
        {
            "nombre": "arrastrar_barra",
            "params": '{{ "direccion": "<vertical|horizontal>", "porcentaje": <int> }}',
            "descripcion": "Arrastra una barra de scroll en una dirección un porcentaje de la ventana"
        },
        {
            "nombre": "hablar",
            "params": '{{ "mensaje": "<string>" }}',
            "descripcion": "Comunica un mensaje al usuario"
        },
        {
            "nombre": "cambiar_ventana",
            "params": '{{ "tabs": <int> }}',
            "descripcion": "Cambia a otra ventana usando Alt+Tab"
        },
        {
            "nombre": "esperar",
            "params": '{{ "segundos": <float> }}',
            "descripcion": "Espera un tiempo determinado antes de la siguiente acción"
        },
        {
            "nombre": "finalizar",
            "params": '{{ "razon": "<string>" }}',
            "descripcion": "Finaliza la tarea actual si se ha completado o es imposible continuar"
        },
        {
            "nombre": "proponer_aprendizaje",
            "params": '{{ "nombre_habilidad": "<string>", "descripcion_habilidad": "<string>" }}',
            "descripcion": "Proponer guardar un nuevo procedimiento aprendido para uso futuro."
        }
    ]
}

if __name__ == "__main__":
    kb = KnowledgeBase()
    if kb.client:
        kb.aprender_habilidad(
            nombre_recurso="habilidades_fundamentales_agente",
            tipo_recurso="Agente",
            datos_habilidad=datos_habilidades
        )
        print("Habilidades fundamentales del agente guardadas en la base de conocimiento.")
    else:
        print("No se pudo conectar a MongoDB para guardar las habilidades.")
