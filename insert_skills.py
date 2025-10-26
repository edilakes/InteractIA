
from knowledge_base import KnowledgeBase

habilidades_fundamentales = {
    "nombre_recurso": "habilidades_fundamentales_agente",
    "tipo_recurso": "Interno",
    "datos": {
        "descripcion": "Acciones primitivas que el agente puede ejecutar directamente sobre el sistema operativo. Son la base de todas las demás habilidades.",
        "contexto_aplicacion": ["General"],
        "acciones": [
            {
                "nombre": "clic",
                "descripcion": "Hace clic en un punto específico de la pantalla.",
                "parametros": [
                    {"nombre": "x_rel", "tipo": "float", "descripcion": "Coordenada X relativa (0.0 a 1.0)."},
                    {"nombre": "y_rel", "tipo": "float", "descripcion": "Coordenada Y relativa (0.0 a 1.0)."}
                ]
            },
            {
                "nombre": "escribir",
                "descripcion": "Escribe un texto en el campo de entrada activo.",
                "parametros": [
                    {"nombre": "texto", "tipo": "str", "descripcion": "El texto a escribir."}
                ]
            },
            {
                "nombre": "presionar_tecla",
                "descripcion": "Presiona una tecla o una combinación de teclas (ej. 'enter', 'ctrl+c').",
                "parametros": [
                    {"nombre": "tecla", "tipo": "str", "descripcion": "La tecla o combinación a presionar."}
                ]
            },
            {
                "nombre": "scroll",
                "descripcion": "Desplaza la rueda del ratón hacia arriba o hacia abajo.",
                "parametros": [
                    {"nombre": "direccion", "tipo": "str", "descripcion": "'arriba' o 'abajo'."},
                    {"nombre": "clics", "tipo": "int", "descripcion": "Número de 'clics' de la rueda."}
                ]
            },
            {
                "nombre": "arrastrar_barra",
                "descripcion": "Arrastra una barra de desplazamiento vertical.",
                "parametros": [
                    {"nombre": "direccion", "tipo": "str", "descripcion": "'arriba' o 'abajo'."},
                    {"nombre": "porcentaje", "tipo": "int", "descripcion": "Qué tanto arrastrar (0-100)."}
                ]
            },
            {
                "nombre": "cambiar_ventana",
                "descripcion": "Ejecuta Alt+Tab para cambiar de ventana.",
                "parametros": [
                    {"nombre": "tabs", "tipo": "int", "descripcion": "Número de veces que presionar Tab."}
                ]
            },
            {
                "nombre": "esperar",
                "descripcion": "Pausa la ejecución durante un número de segundos.",
                "parametros": [
                    {"nombre": "segundos", "tipo": "float", "descripcion": "Tiempo a esperar."}
                ]
            },
            {
                "nombre": "hablar",
                "descripcion": "Comunica un mensaje verbal al usuario a través de la interfaz.",
                "parametros": [
                    {"nombre": "mensaje", "tipo": "str", "descripcion": "El mensaje a mostrar al usuario."}
                ]
            },
            {
                "nombre": "pedir_aclaracion",
                "descripcion": "Hace una pregunta al usuario para obtener más información.",
                "parametros": [
                    {"nombre": "pregunta", "tipo": "str", "descripcion": "La pregunta para el usuario."}
                ]
            },
            {
                "nombre": "finalizar",
                "descripcion": "Finaliza la tarea actual y reporta el resultado.",
                "parametros": [
                    {"nombre": "razon", "tipo": "str", "descripcion": "La razón por la que la tarea ha finalizado."}
                ]
            },
            {
                "nombre": "proponer_aprendizaje",
                "descripcion": "Propone al usuario guardar una nueva habilidad aprendida.",
                "parametros": [
                    {"nombre": "nombre_habilidad", "tipo": "str", "descripcion": "Nombre propuesto para la habilidad."},
                    {"nombre": "descripcion", "tipo": "str", "descripcion": "Descripción de lo que hace la habilidad."}
                ]
            }
        ]
    }
}

kb = KnowledgeBase()
if kb.client:
    kb.aprender_habilidad(
        habilidades_fundamentales["nombre_recurso"],
        habilidades_fundamentales["tipo_recurso"],
        habilidades_fundamentales["datos"]
    )
    print("Habilidades fundamentales insertadas correctamente.")
else:
    print("No se pudo conectar a la base de datos.")
