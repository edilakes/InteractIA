# Plan del Proyecto: Gemini CLI

## Objetivo General
Evolucionar InteractIA de un agente ejecutor a un **agente de aprendizaje interactivo**. El objetivo es que el agente pueda detectar su propia incertidumbre, dialogar con el usuario para solicitar ayuda y aprender de las demostraciones del usuario para mejorar su autonomía y base de conocimientos.

---

## Resumen de Avances Recientes (Estrategia de Aprendizaje Supervisado Interactivo)

**Revisión del Plan:** El plan ha sido revisado. La mayoría de las fases de la "Estrategia de Aprendizaje Supervisado Interactivo" están completadas. El próximo enfoque es la "Verificación de Acciones".

En este paso, se ha implementado la base de una estrategia de aprendizaje supervisado interactivo para InteractIA, permitiendo al agente detectar su incertidumbre y aprender de la interacción con el usuario.

**Fase 1: Detección de Incertidumbre - [HECHO]**
- Se modificó `agente.py` para que el LLM devuelva una `confidence_score` y una `explanation` con cada acción sugerida.
- Se implementó un "Análisis de Novedad" en `memoria.py` y `agente.py` para buscar demostraciones similares de tareas previas, lo que permite al agente identificar si una tarea es nueva o ya conocida.

**Fase 2: Diálogo y Solicitud de Ayuda - [HECHO]**
- Se creó un "Punto de Decisión" en `agente.py` que, ante una baja confianza del LLM, pausa la ejecución.
- Se implementó un "Mecanismo de Pausa y Diálogo" que presenta al usuario opciones para `[P]roceder`, `[C]orregir` el plan, o `[M]ostrar` cómo realizar la tarea.

**Fase 3: Adquisición de Conocimiento - [HECHO]**
- Se desarrolló un "Modo de Grabación (Aprendizaje por Demostración)" mediante la creación del módulo `grabador.py`.
- Se modificó `controlador.py` para que todas las acciones primitivas sean registradas por `grabador.py` cuando el modo de grabación está activo.
- Se integró el proceso de grabación en `agente.py`, permitiendo al usuario demostrar una tarea y al agente guardar la secuencia de acciones en `memoria.py` como una nueva habilidad.

**Fase 4: Integración y Flujo de Trabajo - [HECHO]**
- Se orquestó el nuevo flujo de aprendizaje en `agente.py`, integrando la verificación de memoria, la consulta al LLM con confianza, la evaluación de confianza y el diálogo interactivo.

**Estado Actual:**
La funcionalidad principal para el aprendizaje interactivo está implementada. El próximo objetivo es abordar la "Verificación de Acciones".

---

## Estrategia de Aprendizaje Supervisado Interactivo

### Fase 1: Detección de Incertidumbre (El Disparador)
El primer paso es dotar al agente de la capacidad de saber cuándo necesita ayuda.

*   **Tareas:**
    1.  **Puntuación de Confianza:** Modificar los prompts al LLM (`comunicador.py`) para que cada acción sugerida incluya una puntuación de confianza (ej. `confidence_score`) y una breve explicación. **[HECHO]**
    2.  **Análisis de Novedad:** Implementar una función en `agente.py` que, antes de consultar al LLM, verifique en `memoria.py` si existe una tarea similar ya resuelta (una "demostración"). Si la tarea es completamente nueva, se puede reducir el umbral de confianza para pedir ayuda. **[HECHO]**

### Fase 2: Diálogo y Solicitud de Ayuda (La Interacción)
Cuando la confianza es baja, el agente debe pausar y pedir ayuda de forma estructurada.

*   **Tareas:**
    1.  **Punto de Decisión en `agente.py`:** Crear la lógica principal que compruebe el `confidence_score`. **[HECHO]**
    2.  **Mecanismo de Pausa y Diálogo:** Implementar un sistema que detenga la ejecución del agente y presente un prompt al usuario en la consola, ofreciendo opciones claras como:
        - `[P]roceder`: Ejecutar la acción sugerida a pesar de la baja confianza.
        - `[C]orregir`: Permitir al usuario escribir una instrucción en lenguaje natural para corregir el plan del agente.
        - `[M]ostrar`: Iniciar el modo de "Aprendizaje por Demostración". **[HECHO]**

### Fase 3: Adquisición de Conocimiento (El Aprendizaje)
Esta es la fase clave donde el agente aprende del usuario.

*   **Tareas:**
    1.  **Modo de Grabación (Aprendizaje por Demostración):**
        - Crear un nuevo componente (`grabador.py` o similar) que se active cuando el usuario elige `[M]ostrar`.
        - Este componente registrará la secuencia de acciones que el usuario realiza a través de la interfaz del agente. **[HECHO]**
    2.  **Almacenamiento del Conocimiento:**
        - Una vez que el usuario finaliza la demostración, la secuencia de acciones grabada se guardará en la base de datos de `memoria.py`.
        - La nueva entrada debe estar asociada con el objetivo o prompt original que inició la tarea, para que pueda ser recuperada en el futuro. **[HECHO]**

### Fase 4: Integración y Flujo de Trabajo

*   **Plan de Implementación:**
    1.  **[HECHO]** Modificar `agente.py` para orquestar el nuevo flujo: `Verificar Memoria -> Consultar LLM (con confianza) -> Evaluar Confianza -> Dialogar/Ejecutar -> Verificar Resultado`.
    2.  **[HECHO]** Modificar `comunicador.py` para adaptar los prompts del sistema y del usuario para solicitar la puntuación de confianza.
    3.  **[HECHO]** Desarrollar el sistema de diálogo con el usuario.
    4.  **[HECHO]** Desarrollar el modo de grabación para el aprendizaje por demostración.
    5.  **[HECHO]** Adaptar `memoria.py` para almacenar y consultar las "demostraciones" grabadas.

---

## Tareas Anteriores (Pendientes y Completadas)

*   **Verificación de Acciones:** El problema original de que el agente no sabe si una acción ha tenido éxito sigue siendo crucial. La verificación post-acción es un paso **obligatorio** después de que el agente (o el usuario) ejecuta una acción. Si la verificación falla, puede ser otro disparador para pedir ayuda. **[HECHO]**
    *   **Soluciones propuestas:**
        *   **Análisis de Visión Mejorado:** Comparar capturas de pantalla antes y después de una acción para detectar cambios. **[HECHO]**
        *   **Esperas Inteligentes:** Reemplazar fixed `sleep` calls with loops that check for a specific condition on the screen with a timeout. **[HECHO]**
        *   **Máquina de Estados Explícita:** Introduce a state variable in the agent to track task progress (e.g., `waiting_for_window`, `verifying_content`). **[HECHO]**
        *   **LLM as a Verifier:** Use more structured prompts to have the LLM explicitly verify action outcomes. **[HECHO]**
