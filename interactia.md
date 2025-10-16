# InteractIA: Un Agente de IA Autónomo y Evolutivo

Este documento detalla la arquitectura, filosofía y mecanismos internos de InteractIA, un agente de IA diseñado para operar en un entorno de escritorio, aprender de la interacción con el usuario y ejecutar tareas de forma autónoma.

## 1. Filosofía y Principios Fundamentales

1.  **Emulación de Usuario Físico**: El agente no tiene "atajos". Su única forma de interactuar con el sistema es a través de la visión (captura de pantalla) y el control de periféricos (ratón y teclado), emulando a un usuario humano.

2.  **Cerebro vs. Cuerpo**: La arquitectura se divide conceptualmente:
    *   **Cerebro (`agente.py`):** Es el centro de razonamiento, planificación y aprendizaje. Orquesta el ciclo de operación, gestiona la memoria y se comunica con el modelo de IA (LLM).
    *   **Cuerpo (`controlador.py`, `vision.py`):** Son los sentidos y las extremidades. `vision.py` actúa como los ojos (capturando la pantalla y usando OCR) y `controlador.py` como las manos (ejecutando clics y pulsaciones de teclas).

3.  **Aprendizaje Continuo y Supervisado**: El agente no es una herramienta estática. Su propósito es aprender y mejorar a través de la interacción. El usuario actúa como un supervisor final, validando el conocimiento que el agente destila de sus experiencias.

## 2. Arquitectura del Agente

### El Ciclo de Ejecución Principal (Motor Autónomo)

El corazón del agente es su bucle de ejecución principal, implementado en el método `stream_run` de `agente.py`. A diferencia de un sistema de un solo paso, InteractIA opera en un ciclo continuo (`while True`) que le permite persistir en una tarea hasta completarla. Este bucle solo se detiene si:

*   La tarea se completa con éxito (`finalizar`).
*   El agente necesita la intervención del usuario (`pedir_aclaracion` o `proponer_aprendizaje`).
*   Ocurre un error irrecuperable.

### El Ciclo de Pensamiento (Observar-Consultar-Pensar-Actuar)

Dentro del bucle principal, en cada iteración, se ejecuta un ciclo de pensamiento mejorado:

1.  **Observar**: El agente captura el estado actual de la pantalla.
2.  **Consultar Memoria**: El agente invoca a su módulo de memoria activa (`memoria_chat_mongodb.py`) para obtener un resumen inteligente y conciso de la conversación hasta la fecha. Este resumen, y no el historial en bruto, se convierte en el contexto principal.
3.  **Pensar**: Usando el resumen de la memoria, su conocimiento previo (KB) y la captura de pantalla, el agente crea un plan y decide la siguiente acción atómica a realizar.
4.  **Actuar**: El agente ejecuta la acción decidida (ej. un clic, escribir texto) y el ciclo vuelve a empezar.

### 3.1. Memoria Activa y Relevante

La memoria de InteractIA ha evolucionado de un simple log persistente a una capa de inteligencia activa. En lugar de pasar el historial de chat en bruto al cerebro del agente, el sistema ahora pre-procesa la conversación para extraer relevancia.

*   **Procesador Activo (`memoria_chat_mongodb.py`):** El módulo de memoria ya no es un simple almacén. Ahora contiene lógica para invocar a un LLM y actuar como un "analista de memoria".
*   **Generación de Contexto:** Antes de cada ciclo de pensamiento, el agente le pide al módulo de memoria un resumen de la conversación. El módulo recupera el historial reciente y le pide al LLM que lo sintetice en los puntos clave: intención del usuario, entidades importantes, estado actual y preguntas pendientes.
*   **Contexto de Alta Calidad:** El resultado es un contexto conciso y de alta calidad (ej: *"El usuario quiere los datos de ventas del último trimestre del fichero 'ventas_Q3.xlsx'"*) que se inyecta directamente en el prompt principal del agente. Esto permite al agente tomar decisiones más rápidas y precisas.
*   **Consultas Específicas:** El sistema también permite al agente hacer preguntas concretas a su memoria para resolver ambigüedades (ej: *"¿Cuál fue el nombre del fichero que se mencionó antes?"*).

Este enfoque reduce drásticamente la carga cognitiva del agente principal y representa un paso clave hacia un razonamiento más eficiente y similar al humano.

### El Proceso de Planificación Proactiva

Cuando el agente se enfrenta a un objetivo para el que no tiene una habilidad predefinida, no se rinde. Su "cerebro" (`_construir_prompt`) está diseñado para instruir al modelo de IA a que actúe como un planificador. Se le presenta el objetivo, el contexto de la conversación y la lista de **habilidades fundamentales** que posee (cargadas desde la Knowledge Base). Con esta información, el LLM debe formular un plan y derivar la siguiente acción concreta para avanzar en él.

## 3. Gestión del Conocimiento: El Ciclo de Aprendizaje

InteractIA trasciende la simple ejecución gracias a su sofisticado ciclo de gestión del conocimiento.

### La Base de Conocimiento (KnowledgeBase)

Implementada en `knowledge_base.py` y respaldada por MongoDB, es la memoria a largo plazo del agente. Almacena "habilidades" en formato estructurado. Crucialmente, las propias capacidades fundamentales del agente se cargan desde un recurso especial en la KB (`habilidades_fundamentales_agente`), haciendo el sistema altamente modular.

### El Flujo: Ignorar -> Aprender -> Conocer

El vocabulario de la KB refleja un proceso de aprendizaje natural:

*   **Conocer (`conocer_habilidad`)**: El acto de consultar la KB para ver si existe una habilidad.
*   **Ignorar**: El estado en el que se encuentra el agente cuando `conocer_habilidad` no devuelve nada. Este estado activa el proceso de planificación o aprendizaje.
*   **Aprender (`aprender_habilidad`)**: El acto de consolidar y guardar un nuevo conocimiento en la KB.

### 3.2. El Ciclo de Aprendizaje Supervisado: Destilación y Meta-Aprendizaje

El aprendizaje es la característica que define a InteractIA. El agente puede aprender de dos formas: en tiempo real a partir de la conversación activa (Destilación Directa) y de forma proactiva analizando conversaciones pasadas (Meta-Aprendizaje).

#### Destilación Directa (en tiempo real)

Cuando el agente completa una tarea guiado por el usuario, puede usar la acción `proponer_aprendizaje`. Esto desencadena un proceso donde el agente resume la interacción actual en una habilidad estructurada y se la propone al usuario para guardarla en la Knowledge Base. Es un aprendizaje inmediato y contextual.

#### Meta-Aprendizaje Proactivo (sobre el historial)

Esta es la forma más avanzada de aprendizaje, donde el agente reflexiona sobre sus experiencias pasadas. El objetivo es descubrir múltiples habilidades que pudieron haberse enseñado en una sola conversación y procesarlas de forma individual y robusta.

**1. El Disparador**

Actualmente, este ciclo se inicia de forma manual. El usuario puede pedirle al agente que inicie el proceso con el comando `/aprender_de_historial`.

**2. Fase de Descubrimiento**

Una vez iniciado, el agente busca en su memoria una conversación que no haya analizado previamente. Su objetivo se convierte en: "Analiza este chat y extrae TODAS las posibles habilidades".
*   **Extracción de Hipótesis**: Usando al LLM, el agente identifica todas las "oportunidades de aprendizaje" de esa conversación.
*   **Cola de Oportunidades**: Cada oportunidad se guarda como un documento individual en una nueva base de datos (`oportunidades_aprendizaje`), con un estado inicial de `pendiente_verificacion`.
*   **Registro de Análisis**: La conversación original se marca como analizada para no volver a procesarla, usando la colección `sesiones_analizadas`.

**3. Fase de Procesamiento Individual**

En un ciclo posterior, el agente toma una única oportunidad de la cola que esté pendiente.
*   **Validación de Hipótesis**: El agente presenta la habilidad potencial al usuario para que confirme si es útil y merece ser formalizada (Ej: *"He encontrado una habilidad potencial de una conversación pasada: 'Cómo buscar un fichero por su extensión'. ¿Crees que es útil que intente aprenderla?"*).
*   **Actualización de Estado**: Si el usuario aprueba, el estado de la oportunidad cambia a `verificacion_exitosa`. Si la rechaza, a `rechazada_por_usuario`. De esta forma, aunque en un chat hubiera 3 habilidades y el usuario descarte una, las otras dos no se pierden y quedan pendientes en la cola.
*   **Destilación Final**: Las oportunidades que han sido verificadas con éxito pueden ser procesadas en un futuro para, usando el contexto de la conversación original, destilar los pasos exactos y proponer la habilidad final y estructurada a la Knowledge Base.

## 4. Características Notables

*   **Autonomía**: Gracias a su bucle principal, puede ejecutar tareas de múltiples pasos sin intervención.
*   **Memoria Conversacional Persistente**: El historial de la conversación no solo se incluye en el contexto de pensamiento, sino que se guarda de forma persistente en una base de datos MongoDB. Esto le permite recordar conversaciones entre reinicios. (Ver sección 3.1 para más detalles).
*   **Independencia de Resolución**: Utiliza coordenadas relativas para las acciones de clic, lo que lo hace robusto a diferentes resoluciones de pantalla.
*   **Capacidades Externalizadas**: Sus habilidades fundamentales no están codificadas, sino que se cargan desde la Base de Conocimiento, permitiendo una gran modularidad.
*   **Robustez**: Implementa un sistema de auto-corrección para respuestas JSON mal formadas del LLM y un sistema de depuración que genera un log detallado (`interactia_debug.log`).

## 5. Errores detectados

- hay ejecuciones que son exitosas pero el agente no detecta que se ha cumplido el objetivo.
- las combinaciones de teclas tipo win+e no funcionan pero sin embargo, solo la tecla win sí funciona.

## 6. Propuesta de Futuro: Modelo de Tutoría Jerárquica

### 1. Concepto Central

La idea es crear un sistema de dos niveles donde una instancia de InteractIA (el **Supervisor**) monitoriza, depura y guía a otra instancia (el **Controlado** o "trabajador"). La comunicación del Supervisor hacia el Controlado se limita a emular a un usuario humano, escribiendo instrucciones en su cuadro de chat. Sin embargo, el Supervisor tiene acceso privilegiado de "lectura" tanto a la memoria (historial de chat) como al "cerebro" (estado interno y logs) del Controlado, además de poder ver la pantalla completa.

Esto crea una dinámica de **Tutor-Aprendiz**, donde el Supervisor ayuda al Aprendiz a superar obstáculos, permitiendo resolver problemas más complejos y, a la vez, generando un historial de chat limpio y exitoso en el agente Controlado, ideal para el aprendizaje futuro.

### 2. Análisis de Pros y Contras

**Pros (Ventajas Estratégicas):**

*   **Depuración y Tutoría Avanzada:** Si un agente se atasca, el Supervisor puede analizar su estado interno (su "razonamiento"), ver qué está fallando y darle una instrucción correctiva. Es un mecanismo de auto-depuración y auto-mejora extremadamente potente.
*   **Descomposición de Tareas Complejas:** Permite abordar problemas de un nivel de abstracción superior. Un usuario podría darle al Supervisor un objetivo muy complejo (ej: "Prepara un informe de ventas trimestral"). El Supervisor lo descompondría en pasos simples que iría pasando uno a uno al agente Controlado.
*   **Generación de Datos de Entrenamiento de Alta Calidad:** Al guiar al agente Controlado por el camino correcto, el historial de chat resultante de esa instancia es un ejemplo "perfecto" de cómo completar una tarea, ideal para el ciclo de meta-aprendizaje.
*   **Alineación con la Filosofía del Agente:** Refuerza el principio de "no atajos". El Supervisor está forzado a actuar como un usuario, lo que mantiene la coherencia del sistema.

**Contras (Desafíos Técnicos y Conceptuales):**

*   **Comunicación Entre Instancias (IPC):** Es el mayor desafío. La solución propuesta es utilizar **MongoDB como un bus de estado**. El agente Controlado escribiría su estado actual (objetivo, última acción, error) en un documento dedicado, y el Supervisor lo leería para obtener telemetría en tiempo real.
*   **Consumo de Recursos:** Ejecutar dos instancias completas de InteractIA podría consumir una cantidad considerable de CPU y memoria.
*   **Definición del "Acceso al Cerebro":** Se necesitaría definir con precisión qué conjunto de datos del "cerebro" se exponen de forma segura y útil.
*   **Riesgo de Bucles:** El flujo de interacción debe ser cuidadosamente diseñado para evitar bucles infinitos.

### 3. Flujo de Trabajo Propuesto

1.  **Activación:** El usuario, en la ventana de `interactia_1234`, pulsa un nuevo botón "Crear Supervisor".
2.  **Lanzamiento:** El sistema ejecuta `python main.py --supervisando-a 1234`, abriendo una nueva ventana, `interactia_5678` (el Supervisor).
3.  **Asignación de Tarea:** El usuario le da un objetivo al Supervisor: "Asegúrate de que la instancia 1234 abre la terminal".
4.  **Observación (Supervisor):** Lee el documento de estado en MongoDB de `interactia_1234` y observa la pantalla.
5.  **Pensamiento (Supervisor):** Ve que `1234` está atascado o ha cometido un error.
6.  **Actuación (Supervisor):** Usa su `controlador` para encontrar el cuadro de texto de `1234` y escribe una instrucción correctiva.
7.  El ciclo se repite hasta que la tarea se completa.

## 7. Análisis del Sistema de Aprendizaje y Propuesta de Autonomía

### Situación Actual: Un Sistema Híbrido y Manual

Actualmente, el agente aprende de dos maneras principales, ambas requiriendo intervención manual:

1.  **Registro Directo (Los scripts `registrar_*.py`):**
    *   **Cómo funciona:** Creas un script de Python (como los que hemos visto) donde defines una "habilidad" en un diccionario y usas la función `kb.aprender_habilidad()` para guardarla en la base de datos.
    *   **Análisis:** Este método es robusto y bueno para definir habilidades complejas y fundamentales (como las de navegación o las acciones básicas). Sin embargo, es un proceso de desarrollo de software, no de aprendizaje autónomo. Cada nueva habilidad requiere que escribas y ejecutes código nuevo.

2.  **Aprendizaje Semi-Autónomo (El script `aprendiz_gemini.py`):**
    *   **Cómo funciona:** Este script abre la web de Gemini en Chrome y te pide que le preguntes a Gemini cómo hacer una tarea. Luego, **tú tienes que copiar y pegar manualmente** cada paso que te da Gemini en la terminal para que el script los guarde como una nueva habilidad.
    *   **Análisis:** Esta es una idea muy potente y un gran primer paso hacia la autonomía. El agente intenta usar una fuente de conocimiento externa (Gemini) para aprender. El punto débil es la dependencia del usuario para hacer de "puente" entre la web de Gemini y el script.

**En resumen: El sistema actual es funcional, pero no es autónomo. El agente no puede crear nuevas habilidades por sí mismo a partir de su experiencia o de consultas a Gemini sin una intervención manual significativa.**

### Propuesta para la Autonomía Total: Un Plan en 3 Fases

Para lograr que el agente aprenda de forma verdaderamente autónoma, te propongo el siguiente plan evolutivo:

#### Fase 1: Del Script a la Conversación (Auto-Registro de Habilidades)

*   **Objetivo:** Eliminar por completo la necesidad de los scripts `registrar_*.py` para habilidades sencillas.
*   **Cómo:** Potenciaremos la acción `proponer_aprendizaje` que el agente ya conoce.
    1.  Cuando el agente complete una tarea nueva o una secuencia de acciones que considere útil, podría usar `proponer_aprendizaje` para decirte: "He aprendido a hacer X. ¿Quieres que lo guarde como una nueva habilidad llamada 'habilidad_X'?".
    2.  Si le respondes "sí", el propio agente llamaría internamente a la función `kb.aprender_habilidad()` para guardar esa nueva secuencia de acciones en su base de conocimiento, sin necesidad de ningún script.

#### Fase 2: De la Web a la API (Automatización del Aprendizaje con Gemini)

*   **Objetivo:** Eliminar el paso manual de copiar y pegar en `aprendiz_gemini.py`.
*   **Cómo:** El agente ya usa la API de Gemini para "pensar". Podemos crear un "modo de aprendizaje" en el que use esa misma API para aprender.
    1.  Cuando se enfrente a una tarea que no sabe cómo resolver, el agente podría entrar en "modo aprendizaje".
    2.  En este modo, en lugar de preguntarse a sí mismo qué hacer, le preguntaría a la API de Gemini (con un prompt similar al de `aprendiz_gemini.py`): "¿Cómo puedo 'desinstalar UltraVNC'? Dame los pasos".
    3.  El agente recibiría la respuesta directamente, la analizaría, y guardaría los pasos como una nueva habilidad. **Cero intervención del usuario.**

#### Fase 3: Del Aprendizaje Reactivo al Proactivo (Iniciativa Propia)

*   **Objetivo:** Que el agente decida por sí mismo cuándo y qué necesita aprender.
*   **Cómo:** Una vez completadas las fases 1 y 2, el agente tendría las herramientas para aprender por sí solo. El siguiente paso es darle la iniciativa.
    1.  **Auto-mejora por fallo:** Si el agente falla repetidamente en una tarea, podría activar automáticamente el "modo aprendizaje" (Fase 2) para buscar una solución.
    2.  **Optimización de secuencias:** El agente podría analizar su propio historial de acciones y detectar patrones. Si ve que para hacer "Y" siempre ejecuta los pasos A, B y C, podría proponerte: "He notado que siempre hago A, B y C juntos. ¿Quieres que cree una nueva habilidad 'Y' que haga estos tres pasos de una vez?".