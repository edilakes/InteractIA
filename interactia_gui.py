import tkinter as tk
from tkinter import ttk
from agente import Agente
import threading

class InteractIAGUI:
    def __init__(self, root, titulo="InteractIA - Agente Inteligente", id_objetivo=None):
        self.root = root
        self.titulo_ventana = titulo
        self.root.title(self.titulo_ventana)
        self.root.geometry("800x600")

        # --- Layout Principal ---
        self.main_frame = ttk.Frame(self.root, padding="0")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Placeholder para el Sidebar (Fase 3)
        # self.sidebar_frame = ttk.Frame(self.main_frame, width=200, relief=tk.RIDGE)
        # self.sidebar_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W))

        # --- Frame Principal del Chat ---
        self.chat_area_frame = ttk.Frame(self.main_frame, padding="10")
        self.chat_area_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        # --- Historial de Chat Unificado ---
        self.chat_history_text = tk.Text(self.chat_area_frame, wrap="word", state='disabled', font=('Arial', 10))
        self.chat_history_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.chat_area_frame.rowconfigure(0, weight=1)
        self.chat_area_frame.columnconfigure(0, weight=1)

        # Scrollbar para el chat
        self.scrollbar = ttk.Scrollbar(self.chat_area_frame, orient=tk.VERTICAL, command=self.chat_history_text.yview)
        self.scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.chat_history_text['yscrollcommand'] = self.scrollbar.set

        # --- Indicador de Carga ---
        self.loading_bar = ttk.Progressbar(self.chat_area_frame, mode='indeterminate')
        self.loading_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        self.loading_bar.grid_remove() # Oculto por defecto

        # --- Frame de Entrada de Comandos ---
        self.input_frame = ttk.Frame(self.chat_area_frame)
        self.input_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        self.input_frame.columnconfigure(1, weight=1)

        # Botón para adjuntar archivos (Fase 3)
        self.upload_button = ttk.Button(self.input_frame, text="+", width=3)
        self.upload_button.grid(row=0, column=0, padx=(0, 5))

        self.input_entry = ttk.Entry(self.input_frame)
        self.input_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.input_entry.bind("<Return>", self.process_command)

        self.send_button = ttk.Button(self.input_frame, text="Enviar", command=self.process_command)
        self.send_button.grid(row=0, column=2, padx=5)

        # --- Inicialización ---
        self._configure_chat_tags()
        self.agente = Agente(
            id_ventana=self.titulo_ventana,
            id_objetivo=id_objetivo,
            callback_hablar=self.mostrar_mensaje_agente,
            callback_finalizar=self.finalizar_respuesta_agente
        )
        self._agent_writing = False

    def _configure_chat_tags(self):
        """Configura los tags para roles y formatos."""
        self.chat_history_text.tag_configure('user', justify='right', background='#E0F7FA', relief='raised', borderwidth=1, lmargin1=60, lmargin2=60, spacing3=5)
        self.chat_history_text.tag_configure('agent', justify='left', background='#F0F0F0', foreground='black', relief='raised', borderwidth=1, lmargin1=10, lmargin2=10, spacing3=5)

    def insert_message(self, message, role):
        """Inserta un mensaje completo en el historial de chat."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_history_text.config(state='normal')
        self.chat_history_text.insert(tk.END, f"[{timestamp}] {message}\n\n", role)
        self.chat_history_text.config(state='disabled')
        self.chat_history_text.see(tk.END)

    def process_command(self, event=None):
        """Procesa el comando del usuario, lo muestra y arranca el agente."""
        command = self.input_entry.get()
        if not command:
            return

        self.insert_message(command, 'user')
        self.input_entry.delete(0, tk.END)

        self.loading_bar.grid()
        self.loading_bar.start(10)

        self.agente.establecer_objetivo(command)
        thread = threading.Thread(target=self.agente.stream_run)
        thread.start()

    def mostrar_mensaje_agente(self, token):
        """Callback thread-safe para insertar un token de la respuesta del agente."""
        self.root.after(0, self._insert_agent_token, token)

    def finalizar_respuesta_agente(self):
        """Callback thread-safe para señalar el fin de la respuesta."""
        self.root.after(0, self._finalize_agent_response)

    def _insert_agent_token(self, token):
        """Inserta un token en la GUI, iniciando un nuevo bloque de agente si es necesario."""
        from datetime import datetime
        self.chat_history_text.config(state='normal')
        
        if not self._agent_writing:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.chat_history_text.insert(tk.END, f"Agente [{timestamp}]: ", 'agent')
            self._agent_writing = True
            # Detener la barra de progreso al recibir el primer token
            self.loading_bar.stop()
            self.loading_bar.grid_remove()

        self.chat_history_text.insert(tk.END, token, 'agent')
        self.chat_history_text.config(state='disabled')
        self.chat_history_text.see(tk.END)

    def _finalize_agent_response(self):
        """Finaliza el bloque de respuesta del agente."""
        self.chat_history_text.config(state='normal')
        self.chat_history_text.insert(tk.END, "\n\n", 'agent')
        self.chat_history_text.config(state='disabled')
        self.chat_history_text.see(tk.END)
        self._agent_writing = False
        # Aquí se llamaría al parser de Markdown en el futuro (Fase 2)
        # self._apply_markdown_formatting()

if __name__ == "__main__":
    root = tk.Tk()
    app = InteractIAGUI(root)
    root.mainloop()