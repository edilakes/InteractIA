# Plan de Desarrollo: InteractIA v2.0 - Agente de Escritorio Universal

## 1. Visión General

El objetivo de la versión 2.0 es refactorizar `InteractIA` para transformarlo de un sistema basado en habilidades predefinidas a un **Agente de Aprendizaje Interactivo y de Propósito General**. Este nuevo agente operará directamente sobre el entorno de escritorio del usuario (GUI) utilizando la librería `pyautogui`. La toma de decisiones será centralizada en un único modelo de lenguaje (LLM), que generará dinámicamente el código de automatización necesario para cumplir con las solicitudes del usuario.

Además, el agente ahora es capaz de **detectar su propia incertidumbre**, dialogar con el usuario para solicitar ayuda (ofreciendo opciones para proceder, corregir el plan o demostrar la tarea), y **aprender de las demostraciones del usuario** para mejorar su autonomía y base de conocimientos. También se ha implementado un robusto sistema de **verificación de acciones** post-ejecución, utilizando el LLM para confirmar el éxito de cada paso.

La arquitectura se simplifica radicalmente, siguiendo un flujo de control claro y potente, enriquecido con capacidades de aprendizaje y verificación.

---

## 2. Arquitectura y Flujo de Datos

El flujo de operación será el siguiente:

1.  **Entrada de Usuario (GUI):** El usuario envía un mensaje (ej: "Abre el bloc de notas y escribe hola mundo") a través de la interfaz gráfica.
2.  **Núcleo del Agente (`agente.py`):**
    *   Recibe el mensaje.
    *   **Análisis de Novedad:** Verifica en la memoria si existe una demostración similar para la tarea.
    *   Recopila contexto relevante: historial del chat, análisis de la pantalla actual y datos de la "base de conocimiento".
    *   Construye un **"Prompt Maestro"** y lo envía al LLM.
3.  **Decisión del LLM:** El LLM procesa el prompt y decide la acción a tomar, incluyendo una `confidence_score` y una `explanation`. Su respuesta es un objeto JSON estructurado.
4.  **Punto de Decisión (Baja Confianza):** Si la `confidence_score` es baja, el agente pausa la ejecución y dialoga con el usuario, ofreciendo opciones:
    *   `[P]roceder`: Ejecutar la acción sugerida.
    *   `[C]orregir`: El usuario proporciona nuevas instrucciones para re-evaluar el plan.
    *   `[M]ostrar`: Iniciar el modo de "Aprendizaje por Demostración".
5.  **Despachador de Acciones (`dispatcher.py`):** El núcleo del agente parsea el JSON y ejecuta la función correspondiente a la acción solicitada.
6.  **Ejecución de la Acción:**
    *   **Chat:** Se envía una respuesta de texto al usuario.
    *   **Automatización:** Se ejecuta un fragmento de código `pyautogui`.
    *   **Análisis:** Se captura la pantalla para un futuro ciclo de decisión.
    *   **Modo de Grabación:** Si el usuario eligió `[M]ostrar`, las acciones realizadas por el usuario son grabadas y guardadas como una nueva habilidad en la memoria.
7.  **Verificación de Acciones:** Después de ejecutar una acción (que no sea de chat o finalización), el agente realiza un nuevo análisis de pantalla y consulta al LLM para verificar si la acción se ejecutó correctamente y logró su objetivo.
8.  **Bucle:** El ciclo se repite hasta que la tarea se completa o se alcanza un límite de ciclos.

```mermaid
graph TD
    A[Usuario GUI] --> B(Núcleo del Agente);
    B --> B1{Análisis de Novedad};
    B1 --> C{LLM (Decisión con Confianza)};
    C --> D{Punto de Decisión (Baja Confianza)};
    D -- Proceder --> E[Despachador de Acciones];
    D -- Corregir --> B;
    D -- Demostrar --> F[Modo de Grabación];
    F --> G[Usuario Demuestra];
    G --> H[Guardar Demostración en Memoria];
    H --> B;
    E --> I[Acción: Chat];
    E --> J[Acción: Ejecutar PyAutoGUI];
    E --> K[Acción: Analizar Pantalla];
    I --> A;
    J --> L[Sistema Operativo];
    K --> M{Verificación de Acciones};
    M -- Verificado --> B;
    M -- No Verificado --> B;
```

---

## 3. Fases de Desarrollo

### Fase 1: El Núcleo del Agente y el Prompt Maestro [Completada ✅]

**Componentes:** `agente.py`, `dispatcher.py`, `ejecutor.py`

### Fase 2: Módulos de Acción (Las "Herramientas") [Completada ✅]

1.  **Módulo de Ejecución (`ejecutor.py`):**
    *   **Estado:** Implementación básica completada ✅

2.  **Módulo de Visión (`vision.py`):**
    *   **Estado:** Completado ✅
    *   **Descripción:** Se ha implementado la función `capture_and_analyze_screen()` que captura la pantalla y usa un modelo multimodal para obtener una descripción textual de la UI.

3.  **Módulo de Memoria y Conocimiento (`memoria.py`):**
    *   **Estado:** Completado ✅
    *   **Descripción:** Se ha implementado tanto el historial de chat como la base de conocimiento para la documentación de `pyautogui` con búsqueda semántica.

### Fase 3: Limpieza de Código Obsoleto [Completada ✅]

*   **Estado:** Completado ✅
*   **Descripción:** Se han eliminado los componentes de la v1 (sistema de habilidades).

### Fase 4: Estrategia de Aprendizaje Supervisado Interactivo [Completada ✅]

*   **Descripción:** Se ha implementado la base de una estrategia de aprendizaje supervisado interactivo para InteractIA, permitiendo al agente detectar su incertidumbre y aprender de la interacción con el usuario.
    *   **Fase 1: Detección de Incertidumbre:**
        *   Puntuación de Confianza en LLM (`agente.py`, `comunicador.py`) ✅
        *   Análisis de Novedad (`agente.py`, `memoria.py`) ✅
    *   **Fase 2: Diálogo y Solicitud de Ayuda:**
        *   Punto de Decisión en `agente.py` ✅
        *   Mecanismo de Pausa y Diálogo ✅
    *   **Fase 3: Adquisición de Conocimiento:**
        *   Modo de Grabación (Aprendizaje por Demostración) (`grabador.py`, `controlador.py`) ✅
        *   Almacenamiento del Conocimiento (`memoria.py`) ✅
    *   **Fase 4: Integración y Flujo de Trabajo:**
        *   Orquestación del nuevo flujo en `agente.py` ✅

### Fase 5: Verificación de Acciones [Completada ✅]

*   **Descripción:** Se ha implementado un mecanismo robusto para que el agente verifique el éxito de sus acciones después de la ejecución.
    *   **Análisis de Visión Mejorado:** Comparar capturas de pantalla antes y después de una acción para detectar cambios. ✅
    *   **Esperas Inteligentes:** Reemplazar `sleep` fijos con bucles que verifican una condición específica en pantalla con un tiempo de espera. ✅
    *   **Máquina de Estados Explícita:** Introducción de una variable de estado en el agente para rastrear el progreso de la tarea (ej. `waiting_for_window`, `verifying_content`). ✅
    *   **LLM como Verificador:** Uso de prompts estructurados para que el LLM verifique explícitamente los resultados de las acciones. ✅

---

## 4. Riesgos y Mitigaciones

1.  **Riesgo Principal: Seguridad en la Ejecución de Código.**
    *   **Mitigación:** Logging, whitelisting de módulos, sistema de "dry-run".
2.  **Riesgo: Alucinaciones del LLM.**
    *   **Mitigación:** Manejo de errores robusto, base de conocimiento (`pyautogui`) para autocorrección, y ahora, la **Verificación de Acciones** post-ejecución para detectar y corregir fallos.
3.  **Riesgo: Complejidad del Flujo de Control.**
    *   **Mitigación:** La introducción de una **Máquina de Estados Explícita** en el agente ayuda a gestionar la complejidad del flujo de control y las transiciones entre planificación, ejecución, verificación y aprendizaje.