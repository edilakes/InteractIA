# Arquitectura del Agente: El Modelo Cerebro/Cuerpo

Este documento formaliza la filosofía de diseño que gobierna el funcionamiento del agente InteractIA, resolviendo la aparente contradicción entre su memoria interna y su interacción física con el ordenador.

## El Conflicto

El agente tiene dos directivas principales:

1.  **Máxima de Interacción Física:** La única forma que tiene el agente de interactuar con el sistema operativo es emulando a un usuario humano, es decir, utilizando exclusivamente el **teclado**, el **ratón** y la **pantalla**.
2.  **Necesidad de Memoria:** El agente debe ser capaz de aprender y recordar habilidades en su `KnowledgeBase` para no tener que empezar de cero en cada sesión.

El conflicto surge porque una consulta directa a una base de datos (como MongoDB) es una acción de red, no una acción que un humano realizaría a través de sus sentidos y manos para "recordar" algo.

## La Solución: Separación de Responsabilidades

Para resolver esto, el agente se modela con dos componentes conceptuales distintos:

### 1. El Cerebro (Lógica Interna del Agente)

-   **Componentes:** La clase principal `Agente`, el modelo de lenguaje (LLM) y la `KnowledgeBase`.
-   **Función:** Pensar, razonar, planificar y **recordar**.
-   **Reglas:** Las acciones del Cerebro son **internas, abstractas y no están sujetas a las limitaciones físicas**. Cuando el agente necesita recordar cómo hacer algo, consulta su `KnowledgeBase`. Este acto es análogo al recuerdo en un humano: es un proceso mental interno, no una interacción con el mundo exterior.

### 2. El Cuerpo (El Controlador Físico)

-   **Componentes:** La clase `Controlador`.
-   **Función:** Ejecutar las acciones físicas ordenadas por el Cerebro.
-   **Reglas:** El Cuerpo está **estrictamente limitado por la Máxima de Interacción Física**. Solo puede realizar las acciones atómicas que un humano podría: mover el ratón, hacer clic, escribir en el teclado, etc. No tiene capacidad de decisión, solo de ejecución.

## Flujo de Trabajo

El ciclo de operación del agente sigue este modelo:

1.  **Observar (Físico):** El agente captura información de la pantalla.
2.  **Pensar (Mental):** El Cerebro recibe la información visual. Consulta su memoria (`KnowledgeBase`) y usa su capacidad de razonamiento (el LLM) para decidir cuál es la siguiente **acción física** necesaria para avanzar hacia su objetivo.
3.  **Actuar (Físico):** El Cerebro envía una orden específica (ej: `clic(x=120, y=340)`) al Cuerpo (`Controlador`), que la ejecuta fielmente.

Este modelo asegura que, aunque el agente tiene una memoria interna persistente, todas sus interacciones con el ordenador son 100% fieles a la simulación de un usuario humano.
