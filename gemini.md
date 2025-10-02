# Plan de Trabajo: Agente InteractIA

## Objetivo General

Desarrollar un agente de IA (`InteractIA`) capaz de emular las tareas que es capaz de realizar un ser humano con el ordenador. Tareas tales como usar el sistema operativo (abrir y manejar aplicaciones, buscar archivos, saber comandos y atajos de teclado para su día a día). El agente será capaz de tener una ventana en la que mostrará información útil al usuario, podrá recibir indicaciones en un cuadro de entrada y manejará el ratón y el teclado para ejecutar las tareas que se le manden siempre apoyado en la capacidad de ver la pantalla para recibir feedback de sus acciones y las del usuario. Lo que modifique el usuario también podrá ser percibido por InteractIA para que puedan trabajar en paralelo y ser un agente realmente útil.

## Estado Actual

*   **Arquitectura Modular Implementada:** Se ha desarrollado una arquitectura base con módulos separados para el control, la percepción y la lógica del agente:
    *   `controlador.py`: Una clase `Controlador` que abstrae todas las acciones de bajo nivel (ratón, teclado).
    *   `vision.py`: Una clase `Vision` para la captura de pantalla y el reconocimiento de texto (OCR).
    *   `agente.py`: La clase principal `Agente` que orquesta el bucle "Observar -> Pensar -> Actuar".
    *   `knowledge_base.py`: Una clase `KnowledgeBase` que permite al agente almacenar y recuperar conocimiento en una base de datos MongoDB.
*   **Capacidad de Aprendizaje:** El agente puede aprender de la interacción con el usuario y almacenar nuevos conocimientos en su base de datos.
*   **Capacidades de Percepción y Acción:**
    *   El agente puede ver la pantalla y reconocer texto (OCR) gracias a la integración con Tesseract.
    *   El agente puede realizar acciones básicas como hacer clic, escribir, abrir aplicaciones, presionar teclas y desplazarse por las ventanas.
*   **Inteligencia Artificial:** El agente utiliza un modelo de lenguaje multimodal (Gemini) para tomar decisiones.

## Plan de Trabajo

### Fase 1: Arquitectura Base - ✅ **Completado**

*   **Resultado:** Se ha implementado la arquitectura modular del agente, con los módulos `Controlador`, `Vision`, `Agente` y `KnowledgeBase`.

### Fase 2: Percepción y Acción Básicas - ✅ **Completado**

*   **Resultado:** El agente es capaz de capturar la pantalla, reconocer texto y realizar acciones básicas de control del sistema operativo.

### Fase 3: Integración de la IA - ✅ **Completado**

*   **Resultado:** Se ha integrado el modelo de lenguaje Gemini para la toma de decisiones del agente.

### Fase 4: Aprendizaje y Base de Conocimiento - ✅ **Completado**

*   **Resultado:** El agente es capaz de almacenar y recuperar conocimiento en una base de datos MongoDB, lo que le permite aprender de la interacción con el usuario.

### Fase 5: Implementación de la GUI - 🚧 **En Progreso**

*   **Objetivo:** Desarrollar una interfaz gráfica de usuario (GUI) para que el usuario pueda interactuar con el agente de una forma más amigable.
*   **Plan de Acción:**
    1.  **Diseño de la GUI:** Diseñar una interfaz de usuario simple e intuitiva que permita al usuario:
        *   Ver la información útil que el agente quiera mostrar.
        *   Introducir objetivos y comandos en un cuadro de entrada.
        *   Ver el historial de acciones del agente.
    2.  **Implementación de la GUI:** Desarrollar la GUI utilizando una librería como Tkinter o PyQt.
    3.  **Integración con el Agente:** Integrar la GUI con el agente para que puedan comunicarse entre sí.

### Fase 6: Mejoras en la Percepción y la Acción

*   **Objetivo:** Mejorar las capacidades de percepción y acción del agente.
*   **Plan de Acción:**
    *   **Reconocimiento de Objetos:** Implementar la capacidad de reconocer objetos en la pantalla, como botones, iconos y cuadros de texto.
    *   **Interacción con Elementos de la GUI:** Implementar la capacidad de interactuar con elementos específicos de la GUI, como hacer clic en un botón o escribir en un cuadro de texto, basándose en su reconocimiento.

### Fase 7: Tareas Complejas y Planificación

*   **Objetivo:** Permitir que el agente realice tareas más complejas que requieran planificación y una secuencia de acciones.
*   **Plan de Acción:**
    *   **Planificación de Tareas:** Implementar un módulo de planificación que permita al agente descomponer un objetivo complejo en una secuencia de acciones más simples.
    *   **Ejecución de Tareas:** Mejorar el bucle principal del agente para que pueda ejecutar planes de tareas complejos.

## Próximo Paso

El próximo paso es comenzar con la implementación de la GUI. Para ello, se propone utilizar la librería Tkinter, que viene incluida en la instalación estándar de Python.

## idea que se ha quedado a medio hacer, revisar en la próxima entrega

antes de seguir quiero que hagas un repaso al uso de ventanas, quiero que investigues acciones tales como abrir una ventana, cerrarla, maximizarla y demás acciones, investiga por internet un curso de ofimática de windows y haz un plan para mejorar tus habilidades en el uso de las aplicaciones en el entorno windows. esto será un caplitulo de habilidades. estos capítulos correrán en paralelo con el desarrollo del agente, no estáran en el plan de interactia sion que serán habilidades específicas que quiero que interactia aprenda. Diseña una estructura de trabajo que permita la obtencion de estos capítulos o habilidades. Por ejemplo, interactia debería guardar este capítulo como la habilidad para manejar windows. Si consideras que en tu base de conocimientos ya tienes esta estructura bien conseguida, no hagas nada, si esta información te resulta útil, integrala en el agente de la mejor forma posible.

