import tkinter as tk
from tkinter import ttk, messagebox
import threading

from agente import Agente
from model_manager import load_providers_from_file, get_model_provider
from gui_model_manager import ProviderManagerWindow

class InteractIAGUI:
    def __init__(self, root, titulo="InteractIA - Agente Inteligente", id_objetivo=None):
        self.root = root
        self.titulo_ventana = titulo
        self.id_objetivo = id_objetivo
        self.root.title(self.titulo_ventana)
        self.root.geometry("800x600")

        # --- Estado de la App ---
        self.providers_config = []
        self.selected_provider_config = None
        self.active_provider = None
        self.available_models = []
        self.selected_model = None
        self.agente = None
        self._agent_writing = False

        self._create_widgets()
        self._configure_chat_tags()
        self.reload_providers_config(initial_load=True)

    def _create_widgets(self):
        self.main_frame = ttk.Frame(self.root, padding="0")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)
        self.main_frame.columnconfigure(0, weight=1)

        top_frame = ttk.Frame(self.main_frame, padding=(10, 5, 10, 5))
        top_frame.grid(row=0, column=0, sticky="ew")
        top_frame.columnconfigure(1, weight=1)
        top_frame.columnconfigure(3, weight=1)

        ttk.Label(top_frame, text="Proveedor:").grid(row=0, column=0, padx=(0, 5))
        self.provider_selector = ttk.Combobox(top_frame, state="readonly")
        self.provider_selector.grid(row=0, column=1, sticky="ew")
        self.provider_selector.bind("<<ComboboxSelected>>", self._on_provider_selected)

        ttk.Label(top_frame, text="Modelo:").grid(row=0, column=2, padx=(10, 5))
        self.model_selector = ttk.Combobox(top_frame, state="disabled")
        self.model_selector.grid(row=0, column=3, sticky="ew")
        self.model_selector.bind("<<ComboboxSelected>>", self._on_model_selected)

        manage_button = ttk.Button(top_frame, text="Gestionar...", command=self._open_provider_manager_window)
        manage_button.grid(row=0, column=4, padx=(10, 0))

        # ... (resto de widgets sin cambios) ...
        chat_area_frame = ttk.Frame(self.main_frame, padding=(10, 0, 10, 10))
        chat_area_frame.grid(row=1, column=0, sticky="nsew")
        chat_area_frame.rowconfigure(0, weight=1)
        chat_area_frame.columnconfigure(0, weight=1)
        self.chat_history_text = tk.Text(chat_area_frame, wrap="word", state='disabled', font=('Arial', 10))
        self.chat_history_text.grid(row=0, column=0, sticky="nsew")
        self.scrollbar = ttk.Scrollbar(chat_area_frame, orient=tk.VERTICAL, command=self.chat_history_text.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.chat_history_text['yscrollcommand'] = self.scrollbar.set
        self.loading_bar = ttk.Progressbar(chat_area_frame, mode='indeterminate')
        self.loading_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        self.loading_bar.grid_remove()
        input_frame = ttk.Frame(chat_area_frame)
        input_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=10)
        input_frame.columnconfigure(1, weight=1)
        self.input_entry = ttk.Entry(input_frame)
        self.input_entry.grid(row=0, column=1, sticky="ew")
        self.input_entry.bind("<Return>", self.process_command)
        self.send_button = ttk.Button(input_frame, text="Enviar", command=self.process_command)
        self.send_button.grid(row=0, column=2, padx=5)

    def reload_providers_config(self, initial_load=False):
        self.providers_config = load_providers_from_file()
        if not self.providers_config:
            self.show_error_and_exit("No se encontraron proveedores en providers.json.")
            return
        provider_names = [p['name'] for p in self.providers_config]
        self.provider_selector['values'] = provider_names
        self.provider_selector.set(provider_names[0])
        self._on_provider_selected(None) # Iniciar la carga del primer proveedor

    def _on_provider_selected(self, event):
        selected_name = self.provider_selector.get()
        self.selected_provider_config = next(p for p in self.providers_config if p['name'] == selected_name)
        self.insert_log_message(f"Proveedor seleccionado: {selected_name}. Obteniendo modelos...")
        self.model_selector.set("Cargando...")
        self.model_selector.config(state="disabled")
        self.agente = None # Desactivar agente mientras se cambia de modelo
        threading.Thread(target=self._load_models_for_provider, daemon=True).start()

    def _load_models_for_provider(self):
        try:
            self.active_provider = get_model_provider(self.selected_provider_config)
            self.available_models = self.active_provider.list_models()
            self.root.after(0, self._update_models_dropdown)
        except Exception as e:
            self.root.after(0, lambda: self.show_error_and_exit(f"Error al cargar modelos del proveedor: {e}"))

    def _update_models_dropdown(self):
        if self.available_models:
            self.model_selector['values'] = self.available_models
            self.model_selector.config(state="readonly")
            self.model_selector.set(self.available_models[0])
            self._on_model_selected(None)
        else:
            self.model_selector.set("No se encontraron modelos")

    def _on_model_selected(self, event):
        self.selected_model = self.model_selector.get()
        if self.selected_model and self.selected_model != "Cargando...":
            self._initialize_agent()

    def _initialize_agent(self):
        if not self.active_provider or not self.selected_model:
            return
        try:
            self.agente = Agente(
                model_provider=self.active_provider,
                model_name=self.selected_model,
                id_ventana=self.titulo_ventana,
                id_objetivo=self.id_objetivo,
                callback_hablar=self.mostrar_mensaje_agente,
                callback_finalizar=self.finalizar_respuesta_agente,
                callback_log=self.insert_log_message
            )
            self.insert_log_message(f"Agente listo con {self.selected_provider_config['name']} y modelo {self.selected_model}")
        except Exception as e:
            self.show_error_and_exit(f"Error al inicializar agente: {e}")

    def _open_provider_manager_window(self):
        # El nombre de la config en gui_model_manager.py es `models_config`, hay que pasarlo así
        ProviderManagerWindow(self, providers_config=self.providers_config)

    def show_error_and_exit(self, message):
        messagebox.showerror("Error Crítico", message, parent=self.root)
        self.root.destroy()

    # ... (Resto de métodos de la GUI sin cambios) ...
    def process_command(self, event=None):
        command = self.input_entry.get()
        if not command or not self.agente or not self.agente.operativo:
            return
        self.insert_message(command, 'user')
        self.input_entry.delete(0, tk.END)
        self.loading_bar.grid()
        self.loading_bar.start(10)
        self.agente.establecer_objetivo(command)
        thread = threading.Thread(target=self.agente.stream_run)
        thread.start()

    def _configure_chat_tags(self):
        self.chat_history_text.tag_configure('user', justify='right', background='#E0F7FA', relief='raised', borderwidth=1, lmargin1=60, lmargin2=60, spacing3=5)
        self.chat_history_text.tag_configure('agent', justify='left', background='#F0F0F0', foreground='black', relief='raised', borderwidth=1, lmargin1=10, lmargin2=10, spacing3=5)
        self.chat_history_text.tag_configure('log', foreground='gray', font=('Arial', 8))

    def insert_message(self, message, role):
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_history_text.config(state='normal')
        self.chat_history_text.insert(tk.END, f"[{timestamp}] {message}\n\n", role)
        self.chat_history_text.config(state='disabled')
        self.chat_history_text.see(tk.END)

    def insert_log_message(self, message):
        self.root.after(0, self._insert_log_message, message)

    def _insert_log_message(self, message):
        self.chat_history_text.config(state='normal')
        self.chat_history_text.insert(tk.END, f"{message}\n", 'log')
        self.chat_history_text.config(state='disabled')
        self.chat_history_text.see(tk.END)

    def mostrar_mensaje_agente(self, token):
        self.root.after(0, self._insert_agent_token, token)

    def finalizar_respuesta_agente(self):
        self.root.after(0, self._finalize_agent_response)

    def _insert_agent_token(self, token):
        from datetime import datetime
        self.chat_history_text.config(state='normal')
        if not self._agent_writing:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.chat_history_text.insert(tk.END, f"Agente [{timestamp}]: ", 'agent')
            self._agent_writing = True
            self.loading_bar.stop()
            self.loading_bar.grid_remove()
        self.chat_history_text.insert(tk.END, token, 'agent')
        self.chat_history_text.config(state='disabled')
        self.chat_history_text.see(tk.END)

    def _finalize_agent_response(self):
        self.chat_history_text.config(state='normal')
        self.chat_history_text.insert(tk.END, "\n\n", 'agent')
        self.chat_history_text.config(state='disabled')
        self.chat_history_text.see(tk.END)
        self._agent_writing = False

if __name__ == "__main__":
    root = tk.Tk()
    app = InteractIAGUI(root)
    root.mainloop()