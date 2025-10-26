import tkinter as tk
from tkinter import ttk, messagebox
import threading

from agente import Agente
from model_manager import (
    load_providers_from_db,
    get_model_provider,
    get_default_provider_config,
    update_last_used_model
)
from gui_model_manager import ProviderManagerWindow

class InteractIAGUI:
    def __init__(self, root, titulo="InteractIA - Agente Inteligente", id_objetivo=None):
        print("Initializing InteractIAGUI...")
        self.root = root
        self.titulo_ventana = titulo
        self.id_objetivo = id_objetivo
        self.root.title(self.titulo_ventana)
        self.root.geometry("800x600")

        # --- Estado de la App ---
        self.providers_data = []
        self.selected_provider_type = None
        self.selected_key_config = None
        self.selected_model_name = None
        self.agente = None
        self._agent_writing = False

        self._create_widgets()
        self._configure_chat_tags()
        # self.reload_providers_config(initial_load=True) # Removed this line

    def _create_widgets(self):
        self.main_frame = ttk.Frame(self.root, padding="0")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)
        self.main_frame.columnconfigure(0, weight=1)

        top_frame = ttk.Frame(self.main_frame, padding=(10, 5, 10, 5))
        top_frame.grid(row=0, column=0, sticky="ew")
        top_frame.columnconfigure(3, weight=1)
        top_frame.columnconfigure(5, weight=1)

        ttk.Label(top_frame, text="Proveedor:").grid(row=0, column=0, padx=(0, 5))
        self.provider_selector = ttk.Combobox(top_frame, state="readonly", width=15)
        self.provider_selector.grid(row=0, column=1)
        self.provider_selector.bind("<<ComboboxSelected>>", self._on_provider_selected)

        ttk.Label(top_frame, text="Nombre API:").grid(row=0, column=2, padx=(10, 5))
        self.api_key_selector = ttk.Combobox(top_frame, state="disabled")
        self.api_key_selector.grid(row=0, column=3, sticky="ew")
        self.api_key_selector.bind("<<ComboboxSelected>>", self._on_api_key_selected)

        ttk.Label(top_frame, text="Modelo:").grid(row=0, column=4, padx=(10, 5))
        self.model_selector = ttk.Combobox(top_frame, state="disabled")
        self.model_selector.grid(row=0, column=5, sticky="ew")
        self.model_selector.bind("<<ComboboxSelected>>", self._on_model_selected)

        manage_button = ttk.Button(top_frame, text="Gestionar...", command=self._open_provider_manager_window)
        manage_button.grid(row=0, column=6, padx=(10, 0))

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
        input_frame.columnconfigure(0, weight=1)

        self.input_entry = tk.Text(input_frame, height=2, font=('Arial', 10), wrap="word")
        self.input_entry.grid(row=0, column=0, sticky="nsew")
        
        input_scrollbar = ttk.Scrollbar(input_frame, orient=tk.VERTICAL, command=self.input_entry.yview)
        input_scrollbar.grid(row=0, column=1, sticky="ns")
        self.input_entry['yscrollcommand'] = input_scrollbar.set

        self.input_entry.bind("<Control-Return>", self.process_command)
        self.input_entry.bind("<KeyRelease>", self._update_input_height)

        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=0, column=2, sticky="ns", padx=5)

        self.send_button = ttk.Button(button_frame, text="Enviar", command=self.process_command)
        self.send_button.pack(side="top", fill="x")
        self.stop_button = ttk.Button(button_frame, text="Detener", command=self._on_stop_clicked)
        self.stop_button.pack(side="top", fill="x", pady=5)

    def _update_input_height(self, event=None):
        num_lines = self.input_entry.index('end-1c').split('.')[0]
        current_height = int(num_lines)
        new_height = min(max(2, current_height), 15) # Min 2, Max 15
        self.input_entry.config(height=new_height)

    def reload_providers_config(self, initial_load=False):
        self.providers_data = load_providers_from_db()
        
        if not self.providers_data or not any(p.get("api_key_configs") for p in self.providers_data):
            if initial_load:
                self._prompt_for_initial_configuration()
            else:
                self.show_error_and_exit("No se encontraron configuraciones de API key.")
            return

        provider_types = [p["provider_type"] for p in self.providers_data if p.get("api_key_configs")]
        self.provider_selector["values"] = provider_types

        try:
            p_type, key_config, model_name = get_default_provider_config()
            self.provider_selector.set(p_type)
            self._update_api_key_dropdown(p_type, select_key_name=key_config["name"])
            self._update_model_dropdown(key_config, select_model_name=model_name)
            print("DEBUG: Calling _initialize_agent...") # Temporary debug print
            self._initialize_agent()
        except (RuntimeError, StopIteration):
            if provider_types:
                self.provider_selector.set(provider_types[0])
                self._on_provider_selected(None)
            else:
                self.show_error_and_exit("No se pudo cargar una configuración de modelo válida.")

    def _prompt_for_initial_configuration(self):
        messagebox.showinfo("Configuración Inicial", 
                            "No se ha encontrado ninguna configuración de proveedor de modelos. "
                            "Por favor, añade una configuración para continuar.",
                            parent=self.root)
        win = ProviderManagerWindow(self.root)
        win.grab_set()
        win.wait_window(win) # Add this line to make it modal

    def _on_provider_selected(self, event):
        self.selected_provider_type = self.provider_selector.get()
        self._update_api_key_dropdown(self.selected_provider_type)
        self._on_api_key_selected(None) # Trigger cascade

    def _update_api_key_dropdown(self, provider_type, select_key_name=None):
        provider = next((p for p in self.providers_data if p["provider_type"] == provider_type), None)
        if not provider or not provider.get("api_key_configs"):
            self.api_key_selector["values"] = []
            self.api_key_selector.set("")
            self.api_key_selector.config(state="disabled")
            return

        key_names = [k["name"] for k in provider["api_key_configs"]]
        self.api_key_selector["values"] = key_names
        self.api_key_selector.config(state="readonly")

        if select_key_name and select_key_name in key_names:
            self.api_key_selector.set(select_key_name)
        else:
            self.api_key_selector.set(key_names[0])

    def _on_api_key_selected(self, event):
        key_name = self.api_key_selector.get()
        provider_type = self.provider_selector.get()
        provider = next((p for p in self.providers_data if p["provider_type"] == provider_type), None)
        self.selected_key_config = next((k for k in provider["api_key_configs"] if k["name"] == key_name), None)
        
        self._update_model_dropdown(self.selected_key_config)
        self._on_model_selected(None) # Trigger cascade

    def _update_model_dropdown(self, key_config, select_model_name=None):
        if not key_config or not key_config.get("available_models"):
            self.model_selector["values"] = []
            self.model_selector.set("")
            self.model_selector.config(state="disabled")
            return

        model_names = [m["name"] for m in key_config["available_models"]]
        self.model_selector["values"] = model_names
        self.model_selector.config(state="readonly")

        if select_model_name and select_model_name in model_names:
            self.model_selector.set(select_model_name)
        else:
            self.model_selector.set(model_names[0])

    def _on_model_selected(self, event):
        self.selected_model_name = self.model_selector.get()
        if not self.selected_model_name:
            return
        
        update_last_used_model(self.provider_selector.get(), self.api_key_selector.get(), self.selected_model_name)
        self._initialize_agent()

    def _initialize_agent(self):
        if not self.selected_key_config or not self.selected_model_name:
            return
        try:
            print("DEBUG: Before get_model_provider") # New print
            self.active_provider = get_model_provider(
                provider_type=self.selected_key_config['provider_type'],
                api_key_config=self.selected_key_config
            )
            print("DEBUG: After get_model_provider, before set_model") # New print
            self.active_provider.set_model(self.selected_model_name)
            print("DEBUG: After set_model, before Agente constructor") # New print

            self.agente = Agente(
                model_provider=self.active_provider,
                model_name=self.selected_model_name,
                id_ventana=self.titulo_ventana,
                id_objetivo=self.id_objetivo,
                callback_hablar=self.mostrar_mensaje_agente,
                callback_finalizar=self.finalizar_respuesta_agente,
                callback_log=self.insert_log_message
            )
            print("DEBUG: After Agente constructor, before insert_log_message") # New print
            self.insert_log_message(f"Agente listo con {self.api_key_selector.get()} y modelo {self.selected_model_name}")
            print("DEBUG: After insert_log_message") # New print
        except Exception as e:
            print(f"DEBUG: Exception caught in _initialize_agent: {e}") # New print statement
            self.show_error_and_exit(f"Error al inicializar agente: {e}")

    def _open_provider_manager_window(self):
        ProviderManagerWindow(self.root)

    def show_error_and_exit(self, message):
        messagebox.showerror("Error Crítico", message, parent=self.root)
        # self.root.destroy() # Temporarily commented out

    def exit_application(self):
        self.root.destroy()

    def _on_stop_clicked(self):
        if self.agente:
            self.agente.detener_proceso_emergencia()
            self.insert_log_message("Solicitud de parada de emergencia enviada.")

    def process_command(self, event=None):
        command = self.input_entry.get("1.0", tk.END).strip()
        if not command or not self.agente or not self.agente.operativo:
            return False # Return False to prevent default newline insertion
        self.insert_message(command, 'user')
        self.input_entry.delete("1.0", tk.END)
        self.loading_bar.grid()
        self.loading_bar.start(10)
        self.agente.establecer_objetivo(command)
        thread = threading.Thread(target=self.agente.stream_run)
        thread.start()
        return "break" # Prevents the default newline character from being inserted

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
        print(f"DEBUG: insert_log_message received: {message}") # Temporary debug print
        self.root.after(0, self._insert_log_message, message)

    def _insert_log_message(self, message):
        print(f"DEBUG: _insert_log_message received: {message}") # Temporary debug print
        self.chat_history_text.config(state='normal')
        self.chat_history_text.insert(tk.END, f"{message}\n") # Removed 'log' tag temporarily
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