import tkinter as tk
from tkinter import ttk, messagebox
import threading

from agente import Agente
from model_manager import load_providers_from_db, get_model_provider, get_default_provider_config, _update_last_used_model
from gui_model_manager import ProviderManagerWindow
from skill_manager_gui import SkillManagerGUI

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
        self.selected_model = None
        self.agente = None
        self._agent_writing = False

        self._create_widgets()
        self._create_menu_bar()
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

        self.chat_history_text = tk.Text(self.main_frame, wrap=tk.WORD, state='disabled', font=('Arial', 10))
        self.chat_history_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        chat_scrollbar = ttk.Scrollbar(self.chat_history_text, orient=tk.VERTICAL, command=self.chat_history_text.yview)
        chat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_history_text.config(yscrollcommand=chat_scrollbar.set)

        input_frame = ttk.Frame(self.main_frame, padding="10")
        input_frame.grid(row=2, column=0, sticky="ew")
        input_frame.columnconfigure(0, weight=1)

        self.input_text = tk.Text(input_frame, height=1, font=('Arial', 10), wrap="word")
        self.input_text.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.input_text.bind("<Control-Return>", self.process_command)
        self.input_text.bind("<KeyRelease>", self._on_input_text_change)

        self.input_scrollbar = ttk.Scrollbar(input_frame, orient=tk.VERTICAL, command=self.input_text.yview)
        self.input_text.config(yscrollcommand=self.input_scrollbar.set)
        
        self.send_button = ttk.Button(input_frame, text="Enviar", command=self.process_command)
        self.send_button.grid(row=0, column=2, sticky="e")

        self.loading_bar = ttk.Progressbar(self.main_frame, orient="horizontal", mode="indeterminate")
        self.loading_bar.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.loading_bar.grid_remove()

    def _on_input_text_change(self, event=None):
        # Calculate the number of visible lines (including wrapped lines)
        num_lines = self.input_text.count("1.0", "end", "displaylines")[0]
        
        if num_lines <= 10:
            self.input_text.config(height=num_lines)
            self.input_scrollbar.grid_remove()
        else:
            self.input_text.config(height=10)
            self.input_scrollbar.grid(row=0, column=1, sticky="ns")

    def _create_menu_bar(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Archivo", menu=file_menu)
        file_menu.add_command(label="Salir", command=self.root.quit)

        skills_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Habilidades", menu=skills_menu)
        skills_menu.add_command(label="Gestionar Habilidades", command=self._open_skill_manager_window)

        models_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Modelos", menu=models_menu)
        models_menu.add_command(label="Gestionar Proveedores/Modelos", command=self._open_provider_manager_window)

    def _open_skill_manager_window(self):
        SkillManagerWindow(self.root)

    def reload_providers_config(self, initial_load=False):
        self.providers_config = load_providers_from_db()
        if not self.providers_config:
            self.show_error_and_exit("No se encontraron proveedores en la base de datos.")
            return
        
        provider_names = [p['name'] for p in self.providers_config]
        self.provider_selector['values'] = provider_names

        default_provider_config, default_model_name = get_default_provider_config()
        
        self.provider_selector.set(default_provider_config['name'])
        self.selected_provider_config = default_provider_config

        self._update_models_dropdown(default_model_name)
        
        self._initialize_agent()

    def _on_provider_selected(self, event):
        selected_name = self.provider_selector.get()
        self.selected_provider_config = next(p for p in self.providers_config if p['name'] == selected_name)
        self.insert_log_message(f"Proveedor seleccionado: {selected_name}. Cargando modelos...")
        
        last_used_model_name = None
        if "available_models" in self.selected_provider_config:
            for model in self.selected_provider_config["available_models"]:
                if model.get("is_last_used"):
                    last_used_model_name = model["name"]
                    break
        
        self._update_models_dropdown(last_used_model_name)
        self._initialize_agent()

    def _update_models_dropdown(self, model_to_select: str = None):
        available_models_names = [model["name"] for model in self.selected_provider_config.get("available_models", [])]
        
        if available_models_names:
            self.model_selector['values'] = available_models_names
            self.model_selector.config(state="readonly")
            
            if model_to_select and model_to_select in available_models_names:
                self.model_selector.set(model_to_select)
            else:
                self.model_selector.set(available_models_names[0])
            
            self.selected_model = self.model_selector.get()
        else:
            self.model_selector.set("No se encontraron modelos")
            self.model_selector.config(state="disabled")
            self.selected_model = None

    def _on_model_selected(self, event):
        self.selected_model = self.model_selector.get()
        if self.selected_model and self.selected_model != "Cargando...":
            _update_last_used_model(self.selected_provider_config["id"], self.selected_model)
            self._initialize_agent()

    def _initialize_agent(self):
        if not self.selected_provider_config or not self.selected_model:
            return
        try:
            self.active_provider = get_model_provider(self.selected_provider_config)
            self.active_provider.set_model(self.selected_model)

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
        ProviderManagerWindow(self.root, providers_config=self.providers_config)

    def show_error_and_exit(self, message):
        messagebox.showerror("Error Crítico", message, parent=self.root)
        self.root.destroy()

    def _on_stop_clicked(self):
        if self.agente:
            self.agente.detener_proceso_emergencia()
            self.insert_log_message("Solicitud de parada de emergencia enviada.")

    def process_command(self, event=None):
        command = self.input_text.get("1.0", tk.END).strip()
        if not command or not self.agente or not self.agente.operativo:
            return
        self.insert_message(command, 'user')
        self.input_text.delete("1.0", tk.END)
        self._on_input_text_change()
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
