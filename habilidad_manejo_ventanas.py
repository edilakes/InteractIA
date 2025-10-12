from knowledge_base import KnowledgeBase

# Definición de la habilidad: Manejo de Ventanas en Windows
datos_habilidad = {
    "descripcion": "Cómo manejar ventanas en Windows: abrir, cerrar, maximizar, minimizar, mover, cambiar de tamaño y organizar ventanas.",
    "acciones": [
        {
            "nombre": "abrir_ventana",
            "descripcion": "Abre una aplicación o ventana específica.",
            "ejemplo": "abrir_app('notepad.exe')"
        },
        {
            "nombre": "cerrar_ventana",
            "descripcion": "Cierra la ventana activa.",
            "ejemplo": "presionar_tecla('alt+f4')"
        },
        {
            "nombre": "maximizar_ventana",
            "descripcion": "Maximiza la ventana activa.",
            "ejemplo": "presionar_tecla('win+flecha_arriba')"
        },
        {
            "nombre": "minimizar_ventana",
            "descripcion": "Minimiza la ventana activa.",
            "ejemplo": "presionar_tecla('win+flecha_abajo')"
        },
        {
            "nombre": "cambiar_ventana",
            "descripcion": "Cambia entre ventanas abiertas.",
            "ejemplo": "presionar_tecla('alt+tab')"
        },
        {
            "nombre": "organizar_ventanas",
            "descripcion": "Organiza ventanas en mosaico o lado a lado.",
            "ejemplo": "presionar_tecla('win+izquierda'), presionar_tecla('win+derecha')"
        }
    ],
    "atajos_teclado": [
        {"atajo": "Alt+Tab", "funcion": "Cambiar entre ventanas"},
        {"atajo": "Win+D", "funcion": "Mostrar escritorio"},
        {"atajo": "Win+Flecha Izquierda/Derecha", "funcion": "Ajustar ventana a un lado"},
        {"atajo": "Alt+F4", "funcion": "Cerrar ventana activa"}
    ],
    "ejemplos_practicos": [
        "Abrir Notepad, maximizarlo, escribir texto y cerrarlo.",
        "Organizar dos ventanas lado a lado usando Win+Izquierda/Derecha."
    ],
    "heuristicas": [
        "Maximizar una ventana cuando se requiere enfoque total.",
        "Usar mosaico para comparar información entre dos aplicaciones."
    ],
    "referencias": [
        "https://support.microsoft.com/es-es/windows/administrar-ventanas-en-windows-10-9c1b8b3b-5c0b-4c3b-8c5b-5c6e5c8e5c6e",
        "https://www.youtube.com/watch?v=Ejh0FDK4Q2A"
    ]
}

if __name__ == "__main__":
    kb = KnowledgeBase()
    if kb.client:
        kb.aprender_habilidad(
            nombre_recurso="manejo_ventanas_windows",
            tipo_recurso="Sistema Operativo",
            datos_habilidad=datos_habilidad
        )
        print("Habilidad 'manejo_ventanas_windows' guardada en MongoDB.")
    else:
        print("No se pudo conectar a MongoDB.")
