# Plan de Pruebas para InteractIA

Este documento describe el plan de pruebas para el agente InteractIA, cubriendo sus funcionalidades principales y la verificación a través de los logs. El objetivo es asegurar que todas las funciones operan correctamente y que el sistema maneja adecuadamente los diferentes escenarios en un entorno lo más real posible.

## Enfoque de Pruebas: Pruebas de Integración y Revisión de Logs

A diferencia de las pruebas unitarias aisladas, este plan se centrará en ejecutar el agente en un entorno funcional (o simulado de forma realista) y verificar su comportamiento a través de los logs generados. Esto nos permitirá observar cómo interactúan los diferentes componentes del agente y cómo responde a situaciones diversas.

## Fases del Plan de Pruebas

### Fase 1: Configuración y Funcionalidad Básica

1.  **Configuración del Entorno:**
    *   **Objetivo:** Verificar que todas las dependencias están instaladas y que la conexión a MongoDB es exitosa en un entorno real.
    *   **Pasos:**
        *   Asegurar que todas las dependencias estén instaladas (`pip install -r requirements.txt`).
        *   Verificar que el servicio de MongoDB esté en ejecución y sea accesible.
        *   Confirmar que la variable de entorno `MONGO_URI` en `config.py` apunte a una instancia de MongoDB válida.
        *   Ejecutar el agente o un script de inicialización que intente conectar la memoria.
    *   **Verificación (Logs):** Buscar mensajes de "Memoria conectada a MongoDB." y la ausencia de errores de conexión en los logs del agente.

2.  **Inicialización del Agente:**
    *   **Objetivo:** Confirmar que la clase `Agente` se inicializa correctamente en un entorno real.
    *   **Pasos:**
        *   Ejecutar el agente principal (e.g., `main.py` si existe un punto de entrada).
    *   **Verificación (Logs):** Buscar "Inicializando Agente..." y confirmación de la configuración del modelo en los logs.
    *   **Estado:** Completado (la verificación de la inicialización básica se realizó con un test unitario, pero se revalidará en este contexto de pruebas reales).

### Fase 2: Pruebas de Acciones Principales

1.  **Acciones Primitivas (Controlador):**
    *   **Objetivo:** Verificar la ejecución correcta de cada acción de bajo nivel del controlador en el sistema operativo.
    *   **Pasos (para cada acción):**
        *   Diseñar un escenario donde el agente deba ejecutar una acción primitiva específica (e.g., pedirle que mueva el ratón a una posición, escriba un texto, haga clic).
        *   Observar el comportamiento en pantalla (si es posible) y el resultado de la acción.
    *   **Acciones a Probar (ejemplos):**
        *   `mover_raton(x, y, duracion)`
        *   `escribir(texto, intervalo)`
        *   `clic(x=None, y=None, boton='left')`
        *   `presionar_tecla(tecla)`
        *   `scroll(clics)`
        *   `esperar(segundos)`
    *   **Verificación (Logs):** Buscar "Ejecutando acción primitiva: [nombre_accion] con args: [args]" y "Resultado de la acción [nombre_accion]: [resultado]" en los logs.

2.  **Acciones Compuestas (Orquestador):**
    *   **Objetivo:** Verificar la secuencia de acciones para tareas más complejas que involucran múltiples pasos.
    *   **Pasos (para cada acción):**
        *   Diseñar un escenario donde el agente deba ejecutar una acción compuesta (e.g., pedirle que navegue a una URL, busque en Google).
        *   Observar el comportamiento en pantalla y el resultado de la secuencia de acciones.
    *   **Acciones a Probar (ejemplos):**
        *   `navegar_a_url(url)`: Probar con una URL válida.
        *   `buscar_en_google(termino_busqueda)`: Probar con un término de búsqueda.
    *   **Verificación (Logs):** Buscar "Ejecutando acción compuesta: [nombre_accion] con args: [args]" y "Resultado de la acción [nombre_accion]: [resultado]" en los logs, así como los logs de las acciones primitivas subyacentes.

3.  **Acciones Internas:**
    *   **Objetivo:** Asegurar que las acciones internas del agente funcionan y actualizan el contexto correctamente.
    *   **Pasos (para cada acción):**
        *   Diseñar un escenario donde el agente deba ejecutar una acción interna (e.g., pedirle que analice la pantalla, consulte la base de conocimiento).
    *   **Acciones a Probar (ejemplos):**
        *   `responder_chat(mensaje)`: Verificar que el mensaje se envía al comunicador.
        *   `analizar_pantalla()`: Verificar que `vision_analysis` se actualiza.
        *   `consultar_base_conocimiento(termino_busqueda)`: Verificar que `kb_info` se actualiza.
        *   `finalizar_tarea(mensaje_final)`: Verificar que la tarea se marca como finalizada.
    *   **Verificación (Logs):** Buscar mensajes específicos de cada acción interna y confirmación de actualizaciones de contexto en los logs.

### Fase 3: Gestión de Memoria y Contexto

1.  **Historial de Chat:**
    *   **Objetivo:** Confirmar que los mensajes se guardan y recuperan correctamente de MongoDB durante interacciones reales.
    *   **Pasos:**
        *   Realizar varias interacciones con el agente.
        *   Después de las interacciones, revisar directamente la base de datos MongoDB para verificar los mensajes guardados.
    *   **Verificación (Logs):** Buscar "Recuperando historial de chat para la sesión..." y "Guardando mensaje..." en los logs.

2.  **Actualizaciones de Contexto:**
    *   **Objetivo:** Asegurar que `vision_analysis` y `kb_info` se actualizan después de las acciones correspondientes en un flujo de trabajo real.
    *   **Pasos:**
        *   Ejecutar `analizar_pantalla()` y `consultar_base_conocimiento()` a través de interacciones con el agente.
        *   Revisar los logs para confirmar que los valores de `self.vision_analysis` y `self.kb_info` se registran como actualizados.
    *   **Verificación (Logs):** Buscar mensajes de actualización de contexto en los logs.

3.  **Interacción con el LLM:**
    *   **Objetivo:** Verificar que el LLM recibe el prompt correcto y que sus decisiones se parsean adecuadamente.
    *   **Pasos:**
        *   Realizar una interacción con el agente y revisar el prompt completo enviado al LLM (si es posible configurarlo para que se loguee).
        *   Revisar la respuesta bruta del LLM y el JSON parseado en los logs.
    *   **Verificación (Logs):** Buscar "Enviando petición al modelo de IA...", "Respuesta BRUTA del modelo:", y "Contenido de json_str antes de parsear:" en los logs.

### Fase 4: Manejo de Errores y Casos Extremos

1.  **Acciones Inválidas:**
    *   **Objetivo:** Probar cómo el agente maneja solicitudes de acciones no existentes o mal formadas.
    *   **Pasos:**
        *   Solicitar al agente que ejecute una acción con un nombre inventado o con argumentos incorrectos.
    *   **Verificación (Logs):** Buscar "Acción primitiva desconocida:" o un mensaje de error similar en los logs.

2.  **Errores de Conexión a MongoDB:**
    *   **Objetivo:** Simular problemas de conexión a MongoDB y observar el comportamiento del agente.
    *   **Pasos:**
        *   Detener el servicio de MongoDB (o modificar `MONGO_URI` a uno inválido en `config.py`).
        *   Intentar inicializar el agente o guardar/recuperar mensajes.
    *   **Verificación (Logs):** Buscar "ERROR al inicializar MongoDBChatMemory:" o "Error al guardar mensaje:" en los logs.

3.  **Errores en la Respuesta del LLM:**
    *   **Objetivo:** Simular respuestas vacías o mal formadas del LLM.
    *   **Pasos:**
        *   (Requiere modificación temporal del `ModelProvider` para simular estos errores o forzar una respuesta inválida).
        *   Ejecutar un ciclo del agente con esta configuración.
    *   **Verificación (Logs):** Buscar "Error al decodificar JSON:" o "La respuesta del modelo está vacía." en los logs.

---
**Actualizaciones:**
*   2025-11-05: Iniciando la verificación de "Fase 1: Configuración y Funcionalidad Básica - 2. Inicialización del Agente".
*   2025-11-05: Completada la verificación de "Fase 1: Configuración y Funcionalidad Básica - 2. Inicialización del Agente". Se añadió `test_agente_initialization` a `test_agente_actions.py` y se corrigieron los tests existentes para que pasaran.
*   2025-11-05: Se actualizó el plan de pruebas para enfocarse en pruebas de integración con el agente real y la verificación a través de logs, según la solicitud del usuario.