### Batería de Pruebas para InteractIA

**1. Interacción con Aplicaciones y Creatividad**

Estos prompts prueban la habilidad del agente para abrir aplicaciones, identificar herramientas visualmente y utilizar el control del ratón para tareas no triviales.

*   **Objetivo:** Dibujar en Paint.
    *   **Prompt:** `"Abre Microsoft Paint y dibuja un cuadrado en el centro del lienzo."`
    *   **Qué evalúa:**
        *   Abrir una aplicación (`notepad`, `calc`, `mspaint`...).
        *   Identificar el área de trabajo (lienzo).
        *   Potencialmente, seleccionar la herramienta de lápiz.
        *   Realizar una secuencia de movimientos de ratón (`mover_raton`, `clic`) para simular un arrastre o dibujar líneas.

*   **Objetivo:** Escribir y dar formato.
    *   **Prompt:** `"Abre el Bloc de notas, escribe 'Hola Mundo', luego selecciona todo el texto y busca la opción 'Formato' en el menú para cambiar la fuente."`
    *   **Qué evalúa:**
        *   Escritura de texto (`escribir`).
        *   Uso de atajos de teclado (`presionar_tecla` para `ctrl+a`).
        *   Navegación por menús de una aplicación localizando texto (`vision.leer_texto_en_pantalla` y `controlador.clic`).

**2. Búsqueda de Información y Síntesis**

Estos prompts evalúan la capacidad de leer la pantalla, extraer datos específicos y comunicarlos.

*   **Objetivo:** Consultar información del sistema.
    *   **Prompt:** `"Abre la configuración de 'Fecha y hora' de Windows y dime qué día de la semana es hoy."`
    *   **Qué evalúa:**
        *   Navegación en la interfaz del sistema operativo.
        *   Búsqueda y lectura de un dato específico en una ventana.
        *   Uso de la herramienta `hablar` para comunicar el resultado.

*   **Objetivo:** Búsqueda web simple.
    *   **Prompt:** `"Abre el navegador, ve a google.com, busca 'temperatura actual en Lima' y dime cuál es."`
    *   **Qué evalúa:**
        *   Abrir y manejar una aplicación compleja como un navegador.
        *   Hacer clic en la barra de búsqueda/direcciones.
        *   Escribir una consulta y presionar 'enter'.
        *   Analizar la página de resultados para encontrar un dato numérico relevante y comunicarlo.

**3. Tareas Multi-aplicación y Flujos de Trabajo**

Estos prompts prueban la capacidad de coordinar acciones entre diferentes aplicaciones, simulando un flujo de trabajo real.

*   **Objetivo:** Calcular, copiar y pegar.
    *   **Prompt:** `"Abre la Calculadora, calcula 512 multiplicado por 2. Copia el resultado, abre un nuevo Bloc de notas y pégalo ahí."`
    *   **Qué evalúa:**
        *   Manejo de dos aplicaciones distintas.
        *   Hacer clic en botones específicos (`5`, `1`, `2`, `*`, `2`, `=`).
        *   Uso de atajos de teclado para copiar (`ctrl+c`).
        *   Cambio de foco entre ventanas.
        *   Uso de atajos de teclado para pegar (`ctrl+v`).

*   **Objetivo:** Gestión de archivos simple.
    *   **Prompt:** `"Crea una carpeta en el escritorio llamada 'PruebaInteractIA'. Luego, abre el Bloc de notas, escribe 'Test completado', y guárdalo dentro de esa nueva carpeta con el nombre 'log.txt'."`
    *   **Qué evalúa:**
        *   Interactuar con el escritorio (clic derecho, menús contextuales).
        *   Creación de carpetas y escritura de nombres.
        *   Manejo del diálogo "Guardar como" para navegar en el sistema de archivos.

**4. Autonomía y Resolución de Problemas**

Este prompt evalúa cómo reacciona el agente cuando no puede completar una instrucción directamente.

*   **Objetivo:** Evaluar la capacidad de reportar un fallo.
    *   **Prompt:** `"En el escritorio, busca un icono llamado 'Archivo Inexistente' y hazle doble clic."`
    *   **Qué evalúa:**
        *   Si el agente busca visualmente el elemento.
        *   Si, al no encontrarlo, es capaz de razonar que la tarea no se puede completar.
        *   Si utiliza la herramienta `finalizar` o `hablar` para informar del problema en lugar de quedarse en un bucle de intentos.