# Plan de Pruebas para InteractIA

Este documento describe el plan de pruebas para el agente InteractIA, cubriendo sus funcionalidades principales y la verificación a través de los logs. El objetivo es asegurar que todas las funciones operan correctamente y que el sistema maneja adecuadamente los diferentes escenarios.

## Fases del Plan de Pruebas

### Fase 1: Configuración y Funcionalidad Básica

1.  **Configuración del Entorno:**
    *   **Objetivo:** Verificar que todas las dependencias están instaladas y que la conexión a MongoDB es exitosa.
    *   **Pasos:**
        *   Instalar dependencias (`pip install -r requirements.txt` si aplica).
        *   Asegurar que MongoDB esté en ejecución y accesible.
        *   Verificar la configuración de `MONGO_URI` en `config.py`.
    *   **Verificación (Logs):** Buscar mensajes de "Memoria conectada a MongoDB." y ausencia de errores de conexión.

2.  **Inicialización del Agente:**
    *   **Objetivo:** Confirmar que la clase `Agente` se inicializa correctamente.
    *   **Pasos:**
        *   Instanciar la clase `Agente` con un `ModelProvider` simulado o real.
    *   **Verificación (Logs):** Buscar "Inicializando Agente..." y confirmación de la configuración del modelo.

3.  **Interacción Básica de Chat:**
    *   **Objetivo:** Probar un ciclo `run_cycle` simple y verificar que el agente responde y registra la interacción.
    *   **Pasos:**
        *   Llamar a `agente.run_cycle("Hola, ¿cómo estás?", "sesion_prueba_1")`.
    *   **Verificación (Logs):**
        *   Buscar "--- Iniciando ciclo para mensaje: 'Hola, ¿cómo estás?' ---".
        *   Verificar que se registra la decisión del LLM y el resultado de la acción.
        *   Confirmar que el mensaje se guarda en la memoria.

### Fase 2: Pruebas de Acciones Principales

1.  **Acciones Primitivas (Controlador):**
    *   **Objetivo:** Verificar la ejecución correcta de cada acción de bajo nivel.
    *   **Pasos (para cada acción):**
        *   Solicitar al agente que ejecute la acción con argumentos válidos.
        *   Observar el comportamiento en pantalla (si es posible) y los logs.
    *   **Acciones a Probar:**
        *   `mover_raton(x, y, duracion)`
        *   `escribir(texto, intervalo)`
        *   `clic(x, y, boton)`
        *   `presionar_tecla(tecla)`
        *   `scroll(clics)`
        *   `esperar(segundos)`
    *   **Verificación (Logs):** Buscar "Ejecutando acción primitiva: [nombre_accion] con args: [args]" y "Resultado de la acción [nombre_accion]: [resultado]".

2.  **Acciones Compuestas (Orquestador):**
    *   **Objetivo:** Verificar la secuencia de acciones para tareas más complejas.
    *   **Pasos (para cada acción):**
        *   Solicitar al agente que ejecute la acción con argumentos válidos.
        *   Observar el comportamiento en pantalla y los logs.
    *   **Acciones a Probar:**
        *   `navegar_a_url(url)`: Probar con una URL válida.
        *   `buscar_en_google(termino_busqueda)`: Probar con un término de búsqueda.
    *   **Verificación (Logs):** Buscar "Ejecutando acción compuesta: [nombre_accion] con args: [args]" y "Resultado de la acción [nombre_accion]: [resultado]".

3.  **Acciones Internas:**
    *   **Objetivo:** Asegurar que las acciones internas del agente funcionan y actualizan el contexto.
    *   **Pasos (para cada acción):**
        *   Solicitar al agente que ejecute la acción.
    *   **Acciones a Probar:**
        *   `responder_chat(mensaje)`: Verificar que el mensaje se envía al comunicador.
        *   `analizar_pantalla()`: Verificar que `vision_analysis` se actualiza.
        *   `consultar_base_conocimiento(termino_busqueda)`: Verificar que `kb_info` se actualiza.
        *   `finalizar_tarea(mensaje_final)`: Verificar que la tarea se marca como finalizada.
    *   **Verificación (Logs):** Buscar mensajes específicos de cada acción interna y confirmación de actualizaciones de contexto.

### Fase 3: Gestión de Memoria y Contexto

1.  **Historial de Chat:**
    *   **Objetivo:** Confirmar que los mensajes se guardan y recuperan correctamente de MongoDB.
    *   **Pasos:**
        *   Realizar varias interacciones con el agente.
        *   Recuperar el historial de chat directamente de la base de datos o mediante una función de depuración.
    *   **Verificación (Logs):** Buscar "Recuperando historial de chat para la sesión..." y "Guardando mensaje...".

2.  **Actualizaciones de Contexto:**
    *   **Objetivo:** Asegurar que `vision_analysis` y `kb_info` se actualizan después de las acciones correspondientes.
    *   **Pasos:**
        *   Ejecutar `analizar_pantalla()` y `consultar_base_conocimiento()`.
        *   Verificar los valores de `self.vision_analysis` y `self.kb_info` en el agente.
    *   **Verificación (Logs):** Buscar mensajes de actualización de contexto.

3.  **Interacción con el LLM:**
    *   **Objetivo:** Verificar que el LLM recibe el prompt correcto y que sus decisiones se parsean adecuadamente.
    *   **Pasos:**
        *   Realizar una interacción y revisar el prompt enviado al LLM.
        *   Revisar la respuesta bruta del LLM y el JSON parseado.
    *   **Verificación (Logs):** Buscar "Enviando petición al modelo de IA...", "Respuesta BRUTA del modelo:", y "Contenido de json_str antes de parsear:".

### Fase 4: Manejo de Errores y Casos Extremos

1.  **Acciones Inválidas:**
    *   **Objetivo:** Probar cómo el agente maneja solicitudes de acciones no existentes.
    *   **Pasos:**
        *   Solicitar al agente que ejecute una acción con un nombre inventado.
    *   **Verificación (Logs):** Buscar "Acción primitiva desconocida:" o un mensaje de error similar.

2.  **Errores de Conexión a MongoDB:**
    *   **Objetivo:** Simular problemas de conexión a MongoDB y observar el comportamiento del agente.
    *   **Pasos:**
        *   Detener el servicio de MongoDB (o modificar `MONGO_URI` a uno inválido).
        *   Intentar inicializar el agente o guardar/recuperar mensajes.
    *   **Verificación (Logs):** Buscar "ERROR al inicializar MongoDBChatMemory:" o "Error al guardar mensaje:".

3.  **Errores en la Respuesta del LLM:**
    *   **Objetivo:** Simular respuestas vacías o mal formadas del LLM.
    *   **Pasos:**
        *   (Requiere modificación temporal del `ModelProvider` para simular estos errores).
        *   Ejecutar un ciclo del agente.
    *   **Verificación (Logs):** Buscar "Error al decodificar JSON:" o "La respuesta del modelo está vacía.".

---
**Actualizaciones:**
*   [Fecha]: [Descripción de la actualización]
