# Manual de Usuario de InteractIA

Bienvenido a InteractIA, un agente de IA autónomo diseñado para ayudarte a automatizar tareas en tu ordenador. Este manual te guiará a través de las características y funcionalidades de la aplicación.

## 1. Introducción

InteractIA es un agente inteligente que puede controlar el teclado y el ratón para realizar tareas que le encomiendes. Puedes interactuar con el agente a través de una interfaz de chat, dándole objetivos y observando cómo los lleva a cabo. El agente es capaz de aprender de sus acciones e incluso puede pedirte ayuda.

## 2. Conceptos Clave

Para entender cómo funciona InteractIA, es útil conocer su arquitectura conceptual, que se basa en un modelo de "Cerebro" y "Cuerpo".

*   **El Cerebro:** Es la parte pensante del agente. Incluye la lógica principal, el modelo de lenguaje (LLM) que le da su capacidad de razonamiento, y su base de conocimiento donde almacena lo que aprende. Las acciones del Cerebro son internas y abstractas, como planificar los pasos para cumplir un objetivo o recordar una habilidad aprendida.

*   **El Cuerpo:** Es el componente que interactúa con el ordenador. Está estrictrictamente limitado a emular las acciones de un usuario humano: mover el ratón, hacer clic, escribir en el teclado y leer la pantalla. El Cuerpo ejecuta las órdenes físicas que le da el Cerebro.

Esta separación asegura que, aunque el agente tiene una memoria y una capacidad de razonamiento complejas, todas sus interacciones con tu ordenador son transparentes y se realizan de la misma manera que lo haría una persona.

## 3. Modos de Operación

InteractIA puede funcionar en dos modos:

*   **Modo GUI (Interfaz Gráfica de Usuario):** Este es el modo principal y recomendado. Lanza una ventana con una interfaz de chat y controles visuales. Para iniciar en modo GUI, simplemente ejecuta la aplicación sin ningún parámetro adicional.

*   **Modo CLI (Línea de Comandos):** Este modo te permite darle un objetivo al agente directamente desde la terminal. El agente se ejecutará, intentará completar la tarea y luego terminará. Para usar este modo, pasa el objetivo como un argumento al ejecutar la aplicación. Por ejemplo:
    ```bash
    python main.py "abre el bloc de notas y escribe hola mundo"
    ```

## 4. La Interfaz Gráfica (Modo GUI)

La ventana principal de InteractIA está diseñada para ser intuitiva y fácil de usar.

![Esquema de la GUI de InteractIA](https://i.imgur.com/your-image-url.png) <!-- Placeholder for a screenshot -->

### 4.1. Ventana Principal

La interfaz se divide en varias secciones:

*   **Menú Superior:**
    *   **Archivo:** Contiene la opción para salir de la aplicación.
    *   **Modelos:** Te permite acceder al gestor de proveedores de modelos de IA.
    *   **Conocimiento:** Te permite acceder al gestor de "consideraciones" del agente, que son las lecciones que ha aprendido.

*   **Selección de Modelo:**
    En la parte superior, encontrarás tres menús desplegables:
    1.  **Proveedor:** Elige el proveedor del modelo de IA que deseas usar (ej. OpenAI, Google).
    2.  **Nombre API:** Selecciona la configuración de clave de API específica.
    3.  **Modelo:** Elige el modelo de IA específico (ej. `gpt-4`, `gemini-pro`).

*   **Área de Chat:**
    Es el componente central de la interfaz. Aquí es donde te comunicas con el agente.
    *   Los mensajes que envías aparecen a la derecha.
    *   Las respuestas y acciones del agente aparecen a la izquierda.
    *   También verás mensajes de registro (en gris) que te informan sobre el estado interno del agente.

*   **Entrada de Usuario:**
    En la parte inferior se encuentra el cuadro de texto para comunicarte con el agente.
    *   **Cuadro de Texto:** Escribe aquí tus objetivos o mensajes. Puedes presionar `Shift+Return` para insertar un salto de línea.
    *   **Botón Enviar:** Envía tu mensaje al agente para que lo procese. También puedes presionar `Return`.
    *   **Botón Detener:** Este botón envía una solicitud de "parada de emergencia" al agente. Úsalo si el agente está haciendo algo inesperado y quieres que se detenga de inmediato.

### 4.2. Gestión de Proveedores

Desde el menú `Modelos > Gestionar Proveedores...`, puedes abrir una ventana para configurar los proveedores de modelos de IA. Aquí puedes añadir, editar o eliminar proveedores, así como gestionar tus claves de API para cada uno. InteractIA necesita al menos un proveedor configurado para poder funcionar.

### 4.3. Gestión de Consideraciones

Desde el menú `Conocimiento > Gestionar Consideraciones...`, puedes ver las lecciones que el agente ha aprendido. Cada "consideración" es una regla o heurística que el agente ha generado basándose en el éxito o fracaso de sus acciones pasadas. Esta es una ventana de solo lectura que te permite observar el proceso de aprendizaje del agente.

## 5. Cómo Usar InteractIA

Interactuar con el agente es tan simple como chatear con él.

### 5.1. Dar un Objetivo

Para empezar, escribe un objetivo claro y conciso en el cuadro de texto y haz clic en "Enviar". Por ejemplo:

*   `"Abre la calculadora"`
*   `"Busca en Google 'el tiempo en madrid'"`
*   `"Crea un nuevo archivo de texto en el escritorio y llámalo 'lista_de_compras.txt'"`

### 5.2. El Ciclo del Agente

Una vez que el agente recibe tu objetivo, comienza su ciclo de trabajo:

1.  **Planificación:** El agente analiza tu petición, observa la pantalla y consulta su base de conocimiento para decidir qué acción tomar.
2.  **Ejecución:** El agente ejecuta la acción decidida (mover el ratón, escribir, etc.).
3.  **Verificación:** Después de actuar, el agente vuelve a analizar la pantalla para comprobar si la acción tuvo el efecto esperado.
4.  **Aprendizaje:** Basándose en si la acción fue exitosa o no, el agente genera una nueva "consideración" o lección para mejorar su comportamiento futuro.
5.  El ciclo se repite hasta que el objetivo se completa.

### 5.3. Interacción Durante la Tarea

A veces, el agente puede no estar seguro de cómo proceder. Si su "puntuación de confianza" para una acción es demasiado baja, te pedirá ayuda. Verás un mensaje en el chat preguntándote qué hacer.

**Nota Importante:** La funcionalidad de ayuda interactiva (proceder, corregir, mostrar) y el "Modo de Demostración" **solo están implementados para el modo de línea de comandos (CLI)**. En el modo GUI, si el agente tiene baja confianza, el proceso puede detenerse esperando una entrada que no se puede proporcionar a través de la interfaz gráfica.

### 5.4. Modo de Demostración (Solo CLI)

Si ejecutas la aplicación en modo CLI y el agente te pide ayuda, puedes elegir la opción `[M]` para mostrarle cómo se hace una tarea.

1.  El agente te pedirá que realices la tarea tú mismo.
2.  Mientras actúas, un grabador registrará todas tus acciones (clics, pulsaciones de teclas, etc.).
3.  Cuando hayas terminado, volverás a la terminal y presionarás `ENTER`.
4.  El agente guardará la secuencia de acciones grabadas como una nueva habilidad.

La próxima vez que le pidas una tarea similar en modo CLI, el agente podrá usar la demostración que grabaste.

## 6. Conclusión

InteractIA es una herramienta poderosa con la capacidad de aprender y adaptarse. Cuanto más interactúes con él, más aprenderá y mejor será realizando las tareas que le encomiendes. ¡Experimenta con diferentes objetivos y no dudes en enseñarle nuevas habilidades!