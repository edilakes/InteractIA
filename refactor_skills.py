from knowledge_base import KnowledgeBase

def refactor_skills():
    kb = KnowledgeBase()
    if not kb.client:
        print("Error: No se pudo conectar a la base de datos.")
        return

    # 1. Implementar 'abrir_aplicacion_por_nombre'
    nombre_recurso_abrir = "accion_manejo_aplicaciones"
    datos_abrir = {
        "descripcion": "Un conjunto de acciones para gestionar aplicaciones, como abrirlas o registrarlas en la base de conocimiento.",
        "tipo": "Imperativa",
        "contexto_aplicacion": ["General"],
        "acciones": [
            {
                "nombre": "abrir_aplicacion_por_nombre",
                "descripcion": "Abre una aplicacion de escritorio (ej. 'bloc de notas') usando el menu de inicio.",
                "params": [{"nombre": "nombre_app", "tipo": "str"}],
                "secuencia_primitivas": [
                    {"accion": "presionar_tecla", "params": {"tecla": "win"}},
                    {"accion": "esperar", "params": {"segundos": 1}},
                    {"accion": "escribir", "params": {"texto": "{nombre_app}"}},
                    {"accion": "esperar", "params": {"segundos": 1}},
                    {"accion": "presionar_tecla", "params": {"tecla": "enter"}}
                ]
            },
            {
                "nombre": "registrar_nueva_aplicacion",
                "descripcion": "Enseña al agente la ubicacion de una nueva aplicacion.",
                "params": [
                    {"nombre": "nombres_populares", "tipo": "list"},
                    {"nombre": "ruta_absoluta", "tipo": "str"}
                ]
            }
        ]
    }
    kb.aprender_habilidad(nombre_recurso_abrir, "Habilidad Imperativa", datos_abrir)
    print(f"(+) Habilidad '{nombre_recurso_abrir}' refactorizada y guardada.")

    # 2. Implementar 'ejecutar_comando_consola' como una habilidad compuesta
    nombre_recurso_cmd = "ejecutar_comando_consola"
    datos_cmd = {
        "descripcion": "Ejecuta un comando en el Simbolo del Sistema (cmd.exe).",
        "tipo": "Habilidad Compuesta",
        "contexto_aplicacion": ["General"],
        "acciones": [
            {
                "nombre": "ejecutar_comando_consola",
                "descripcion": "Abre cmd, ejecuta un comando y presiona enter.",
                "params": [{"nombre": "comando", "tipo": "str"}],
                "secuencia_primitivas": [
                    # Esta es la llamada a otra habilidad compleja
                    {"accion": "abrir_aplicacion_por_nombre", "params": {"nombre_app": "cmd"}},
                    {"accion": "esperar", "params": {"segundos": 2}},
                    {"accion": "escribir", "params": {"texto": "{comando}"}},
                    {"accion": "presionar_tecla", "params": {"tecla": "enter"}}
                ]
            }
        ]
    }
    kb.aprender_habilidad(nombre_recurso_cmd, "Habilidad Compuesta", datos_cmd)
    print(f"(+) Habilidad '{nombre_recurso_cmd}' refactorizada y guardada.")

    # 3. Eliminar la habilidad redundante 'abrir_aplicacion'
    kb.olvidar_habilidad("abrir_aplicacion")

    print("\n--- Refactorización de habilidades completada ---")

if __name__ == "__main__":
    refactor_skills()