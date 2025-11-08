# Plan para la Gestión de "Consideraciones Adicionales"

Este plan detalla los pasos para implementar un gestor de "Consideraciones Adicionales" en InteractIA, permitiendo al usuario guardar notas relevantes para las tareas del agente en MongoDB y gestionarlas a través de una interfaz gráfica.

## 1. Diseño de la Base de Datos (MongoDB)

### 1.1. Estructura de la Colección "consideraciones"
Se creará una nueva colección en MongoDB llamada `consideraciones`. Cada documento en esta colección representará una consideración y tendrá la siguiente estructura:

```json
{
  "_id": ObjectId("..."), // ID único generado por MongoDB
  "nombre": "string",      // Nombre o título de la consideración (ej. "Mi flujo de trabajo para abrir apps")
  "contenido": "string",   // Contenido detallado de la consideración (la nota en sí)
  "fecha_creacion": "datetime", // Fecha y hora de creación
  "fecha_actualizacion": "datetime" // Fecha y hora de la última actualización
}
```

### 1.2. Módulo de Gestión de Base de Datos (`considerations_db_manager.py`)
**[COMPLETADO]** Se creará un nuevo archivo `considerations_db_manager.py` que contendrá funciones para interactuar con la colección `consideraciones`:

*   `get_all_considerations()`: Recupera todas las consideraciones.
*   `add_consideration(nombre, contenido)`: Añade una nueva consideración.
*   `update_consideration(id, nombre, contenido)`: Actualiza una consideración existente por su `_id`.
*   `delete_consideration(id)`: Elimina una consideración por su `_id`.
*   `get_consideration_by_name(nombre)`: Recupera una consideración por su nombre.

Este módulo utilizará `pymongo` y la `MONGO_URI` configurada en `.env`.

## 2. Implementación de la Interfaz Gráfica (GUI)

### 2.1. Añadir Entrada de Menú en `interactia_gui.py`
**[COMPLETADO]** Se modificará `interactia_gui.py` para añadir una nueva opción en el menú principal (ej. "Herramientas" o "Configuración") que abrirá la ventana del gestor de consideraciones.

### 2.2. Ventana del Gestor de Consideraciones (`considerations_manager_window.py`)
**[COMPLETADO]** Se creará un nuevo archivo `considerations_manager_window.py` que contendrá una clase `ConsiderationsManagerWindow` (heredando de `tk.Toplevel`) con la siguiente funcionalidad:

*   **Visualización:** Un `ttk.Treeview` o `tk.Listbox` para mostrar el `nombre` de todas las consideraciones existentes.
*   **Botones de Acción:**
    *   "Añadir": Abre un diálogo (`AddEditConsiderationDialog`) para crear una nueva consideración.
    *   "Editar": Abre un diálogo (`AddEditConsiderationDialog`) con los datos de la consideración seleccionada para su edición.
    *   "Eliminar": Elimina la consideración seleccionada (con confirmación).
*   **Diálogo Añadir/Editar (`AddEditConsiderationDialog`):** Una clase `tk.Toplevel` para un formulario simple con campos de entrada para `nombre` y `contenido` de la consideración.

## 3. Integración con el Agente (`agente.py`)

### 3.1. Carga de Consideraciones en el Agente
**[COMPLETADO]** Se modificará la clase `Agente` en `agente.py` para que, al inicializarse o al iniciar un ciclo de tarea, cargue las consideraciones relevantes (posiblemente todas, o filtradas por algún criterio futuro) desde `considerations_db_manager.py`.

### 3.2. Actualización del Prompt Maestro
**[COMPLETADO]** Se modificará `MASTER_PROMPT_TEMPLATE` en `agente.py` para incluir un nuevo campo de contexto que contenga las "Consideraciones Adicionales" cargadas. Esto permitirá al LLM tener acceso a esta información al tomar decisiones.

```
MASTER_PROMPT_TEMPLATE = """
...
INFORMACIÓN DE LA BASE DE CONOCIMIENTO:
{info_conocimiento}

CONSIDERACIONES ADICIONALES:
{consideraciones_adicionales}

TAREA ACTUAL DEL USUARIO: "{user_message}"
...
"""
```

### 3.3. Lógica de Uso por el LLM
**[COMPLETADO]** Se confiará en la capacidad del LLM para interpretar y utilizar las `consideraciones_adicionales` proporcionadas en el prompt para mejorar sus decisiones y la ejecución de tareas.

## 4. Pasos de Ejecución

1.  **[COMPLETADO]** Crear `considerations_db_manager.py` con las funciones CRUD.
2.  **[COMPLETADO]** Crear `considerations_manager_window.py` con la interfaz de usuario para gestionar las consideraciones.
3.  **[COMPLETADO]** Modificar `interactia_gui.py` para añadir la opción de menú que abre `ConsiderationsManagerWindow`.
4.  **[COMPLETADO]** Modificar `agente.py`:
    *   Importar `considerations_db_manager`.
    *   Actualizar `__init__` para cargar consideraciones.
    *   Actualizar `_run_single_cycle` para incluir `consideraciones_adicionales` en el `prompt`.
    *   Actualizar `MASTER_PROMPT_TEMPLATE` con el nuevo campo.

Este plan proporciona una hoja de ruta clara para la implementación de la funcionalidad de "Consideraciones Adicionales".