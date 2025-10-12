import time
from knowledge_base import KnowledgeBase
from controlador import Controlador

class AprendizGemini:
    """
    Habilidad para aprender tareas paso a paso consultando Gemini y almacenando el conocimiento adquirido.
    """
    def __init__(self):
        self.kb = KnowledgeBase()
        self.controlador = Controlador()
        self.historial = []
        self.url_gemini = "https://gemini.google.com/"

    def abrir_gemini(self):
        """Abre el navegador en la web de Gemini."""
        self.controlador.abrir_aplicacion("chrome.exe")
        time.sleep(2)
        self.controlador.escribir(self.url_gemini)
        self.controlador.presionar_tecla("enter")
        time.sleep(5)

    def generar_prompt(self, tarea):
        return (
            f"Indica paso a paso, y solo un paso a la vez, cómo realizar la siguiente tarea: {tarea}. "
            "No inventes nada. Espera a que te confirme o te proporcione información antes de dar el siguiente paso. "
            "Si necesitas información adicional, pídela de forma concreta."
        )

    def guardar_pasos(self, tarea, pasos):
        """Guarda la secuencia de pasos aprendidos en la base de conocimientos."""
        self.kb.guardar_habilidad(
            nombre_recurso=f"gemini_{tarea.replace(' ', '_').lower()}",
            tipo_recurso="Aprendizaje Gemini",
            datos_habilidad={
                "tarea": tarea,
                "pasos": pasos,
                "fuente": self.url_gemini
            }
        )

    def aprender_tarea(self, tarea):
        """
        Flujo principal: abre Gemini, formula el prompt, y guía la interacción paso a paso.
        El usuario debe interactuar manualmente con Gemini y copiar los pasos aquí para almacenarlos.
        """
        print(f"Abriendo Gemini para aprender la tarea: {tarea}")
        self.abrir_gemini()
        prompt = self.generar_prompt(tarea)
        print(f"Prompt para Gemini:\n{prompt}\n")
        print("Copia y pega aquí cada paso que Gemini te indique. Escribe 'fin' para terminar.")
        pasos = []
        while True:
            paso = input("Paso de Gemini: ")
            if paso.strip().lower() == "fin":
                break
            pasos.append(paso)
        self.guardar_pasos(tarea, pasos)
        print(f"Tarea '{tarea}' aprendida y almacenada.")

    def aprender_desinstalar_ultravnc(self):
        """
        Método para aprender cómo desinstalar UltraVNC utilizando Gemini.
        """
        tarea = "Desinstalar la aplicación UltraVNC en un ordenador con Windows"
        prompt = self.generar_prompt(tarea)
        print(f"Prompt para Gemini:\n{prompt}\n")
        print("Copia y pega aquí cada paso que Gemini te indique. Escribe 'fin' para terminar.")
        pasos = []
        while True:
            paso = input("Paso de Gemini: ")
            if paso.strip().lower() == "fin":
                break
            pasos.append(paso)
        self.guardar_pasos(tarea, pasos)
        print(f"Tarea '{tarea}' aprendida y almacenada.")

if __name__ == "__main__":
    ag = AprendizGemini()
    tarea = input("¿Qué tarea quieres aprender paso a paso con Gemini?: ")
    ag.aprender_tarea(tarea)
