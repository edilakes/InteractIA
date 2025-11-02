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

class ChatMessage(tk.Frame):
    def __init__(self, parent, message, role, **kwargs):
        super().__init__(parent, **kwargs)
        self.message = message
        self.role = role
        self.parent = parent

        self.configure(borderwidth=1, relief='raised', highlightbackground="black", highlightthickness=1)

        if role == 'user':
            self.configure(bg='#E0F7FA')
            justify = 'right'
            anchor = 'e'
        else:
            self.configure(bg='#F0F0F0')
            justify = 'left'
            anchor = 'w'

        self.grid_columnconfigure(0, weight=1)

        # Contenedor para el mensaje y el botón
        container = tk.Frame(self, bg=self.cget('bg'))
        container.grid(row=0, column=0, sticky='ew')
        container.grid_columnconfigure(0, weight=1)

        # Mensaje
        self.message_label = tk.Label(container, text=message, justify=justify, bg=self.cget('bg'), anchor=anchor)
        self.message_label.grid(row=0, column=0, padx=10, pady=5, sticky='ew')

        # Botón de copiar
        self.copy_button = ttk.Button(container, text="Copiar", width=6, command=self.copy_to_clipboard)
        self.copy_button.grid(row=0, column=1, padx=(0, 5), pady=5, sticky='ne')

    def copy_to_clipboard(self):
        self.parent.clipboard_clear()
        self.parent.clipboard_append(self.message)
        self.parent.update() # Now it stays on the clipboard after the window is closed
        self.copy_button.config(text="Copiado!")
        self.after(1500, lambda: self.copy_button.config(text="Copiar"))

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
        self.selected_provider_config = None
        self.selected_key_config = None
        self.active_provider = None
        self.selected_model = None
        self.agente = None
        self._agent_writing = False
        self._loading_config = True # Flag to prevent events during setup
        self._agent_thread = None
        self.current_agent_message_widget = None

        self._create_menu()
        self._create_widgets()
        self.reload_providers_config(initial_load=True)

    def start_gui(self):
        """Makes the GUI visible after initialization."""
        self.root.deiconify()

    def _create_menu(self):
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)

        # Menú Archivo
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Archivo", menu=file_menu)
        file_menu.add_command(label="Salir", command=self.root.quit)

        # Menú Modelos
        models_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Modelos", menu=models_menu)
        models_menu.add_command(label="Gestionar Proveedores...", command=self._open_provider_manager_window)

        # Menú Conocimiento
        knowledge_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Conocimiento", menu=knowledge_menu)
        # Aquí se pueden añadir más opciones en el futuro

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

        self.chat_canvas = tk.Canvas(chat_area_frame, highlightthickness=0)
        self.chat_canvas.grid(row=0, column=0, sticky='nsew')
        self.chat_canvas.bind("<Configure>", self._on_canvas_configure)

        self.scrollbar = ttk.Scrollbar(chat_area_frame, orient=tk.VERTICAL, command=self.chat_canvas.yview)
        self.scrollbar.grid(row=0, column=1, sticky='ns')
        self.chat_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.chat_frame = tk.Frame(self.chat_canvas, bg='white')
        self.chat_canvas.create_window((0, 0), window=self.chat_frame, anchor='nw', tags='self.chat_frame')

        self.chat_frame.bind("<Configure>", self._on_frame_configure)
        self.chat_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.chat_frame.bind("<Configure>", self._on_chat_frame_configure, add='+')

        self.loading_bar = ttk.Progressbar(chat_area_frame, mode='indeterminate')
        self.loading_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        self.loading_bar.grid_remove()

        input_frame = ttk.Frame(chat_area_frame)
        input_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=10)
        input_frame.columnconfigure(0, weight=1)

        self.input_entry = tk.Text(input_frame, height=1, wrap="word", font=('Arial', 10))
        self.input_entry.grid(row=0, column=0, sticky="ew")
        self.input_entry.bind("<<Modified>>", self._on_input_modified)
        self.input_entry.bind("<Return>", self.process_command)
        self.input_entry.bind("<Shift-Return>", self._insert_newline)

        self.input_scrollbar = ttk.Scrollbar(input_frame, orient=tk.VERTICAL, command=self.input_entry.yview)
        self.input_entry['yscrollcommand'] = self.input_scrollbar.set

        self.send_button = ttk.Button(input_frame, text="Enviar", command=self.process_command)
        self.send_button.grid(row=0, column=2, padx=5)
        
        self.stop_button = ttk.Button(input_frame, text="Detener", command=self._on_stop_clicked)
        self.stop_button.grid(row=0, column=3, padx=5)

    def _on_frame_configure(self, event=None):
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.chat_canvas.itemconfig('self.chat_frame', width=event.width)

    def _on_chat_frame_configure(self, event):
        chat_message_width = max(1, event.width - 150)
        log_message_width = max(1, event.width - 20)
        for child in self.chat_frame.winfo_children():
            if isinstance(child, ChatMessage):
                child.message_label.config(wraplength=chat_message_width)
            elif isinstance(child, tk.Label):
                child.config(wraplength=log_message_width)

    def _on_mousewheel(self, event):
        self.chat_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _on_input_modified(self, event=None):
        num_lines = self.input_entry.count("1.0", "end", "displaylines")[0]
        if num_lines <= 5:
            self.input_entry.config(height=num_lines)
            self.input_scrollbar.grid_remove()
        else:
            self.input_entry.config(height=5)
            self.input_scrollbar.grid(row=0, column=1, sticky="ns")
        self.input_entry.edit_modified(False)

    def _insert_newline(self, event=None):
        self.input_entry.insert(tk.INSERT, "\n")
        return "break"

    def reload_providers_config(self, initial_load=False):
        self._loading_config = True
        self.providers_data = load_providers_from_db()
        
        if not self.providers_data or not any(p.get("api_keys") for p in self.providers_data):
            if initial_load:
                self._prompt_for_initial_configuration()
            else:
                self.show_error_and_exit("No se encontraron configuraciones de API key.")
            return
        
        self.provider_selector['values'] = [p['name'] for p in self.providers_data]

        try:
            default_provider_type, default_key_config, default_model_name = get_default_provider_config()
            
            default_provider = next((p for p in self.providers_data if p["provider_type"] == default_provider_type), None)
            if default_provider:
                self.provider_selector.set(default_provider['name'])
                
                if default_key_config and default_key_config['name'] in [kc['name'] for kc in default_provider.get("api_keys", [])]:
                    pass

                if default_model_name:
                    pass
            
            self._on_provider_selected(None)

            if default_provider and default_key_config and default_key_config['name'] in self.api_key_selector['values']:
                self.api_key_selector.set(default_key_config['name'])
                self._on_api_key_selected(None)

            if default_model_name and default_model_name in self.model_selector['values']:
                self.model_selector.set(default_model_name)
                self._on_model_selected(None)


        except (RuntimeError, StopIteration) as e:
            self.insert_log_message(f"No se encontró configuración por defecto, usando la primera disponible: {e}")
            if self.provider_selector['values']:
                self.provider_selector.set(self.provider_selector['values'][0])
                self._on_provider_selected(None)
        
        finally:
            self._loading_config = False
            self._initialize_agent()

    def _on_provider_selected(self, event=None):
        self.api_key_selector.set('')
        self.api_key_selector['values'] = []
        self.api_key_selector.config(state="disabled")
        
        self.model_selector.set('')
        self.model_selector['values'] = []
        self.model_selector.config(state="disabled")

        selected_name = self.provider_selector.get()
        self.selected_provider_config = next((p for p in self.providers_data if p['name'] == selected_name), None)
        
        if not self.selected_provider_config:
            return

        api_key_names = [kc['name'] for kc in self.selected_provider_config.get("api_keys", [])]
        self.api_key_selector['values'] = api_key_names
        
        if api_key_names:
            self.api_key_selector.config(state="readonly")
            self.api_key_selector.set(api_key_names[0])
            self._on_api_key_selected(None)
        else:
            self._on_api_key_selected(None)


    def _on_api_key_selected(self, event=None):
        self.model_selector.set('')
        self.model_selector['values'] = []
        self.model_selector.config(state="disabled")

        selected_key_name = self.api_key_selector.get()
        if not selected_key_name or not self.selected_provider_config:
            self.selected_key_config = None
        else:
            self.selected_key_config = next((kc for kc in self.selected_provider_config.get('api_keys', []) if kc['name'] == selected_key_name), None)
        
        if self.selected_key_config:
            model_names = [m['name'] for m in self.selected_key_config.get("models", [])]
            self.model_selector['values'] = model_names
            
            if model_names:
                self.model_selector.config(state="readonly")
                self.model_selector.set(model_names[0])

        self._on_model_selected(None)


    def _on_model_selected(self, event=None):
        self.selected_model = self.model_selector.get()
        if self._loading_config: return

        if self.selected_model and self.selected_provider_config and self.selected_key_config:
            try:
                update_last_used_model(
                    self.selected_provider_config["provider_type"], 
                    self.selected_key_config["name"], 
                    self.selected_model
                )
            except Exception as e:
                self.insert_log_message(f"Error al guardar último modelo: {e}")
        
        self._initialize_agent()

    def _initialize_agent(self):
        if self._loading_config or not self.selected_provider_config or not self.selected_key_config or not self.selected_model:
            return
        try:
            self.insert_log_message(f"Inicializando agente con {self.selected_key_config['name']} y modelo {self.selected_model}...")
            self.active_provider = get_model_provider(
                self.selected_provider_config['provider_type'], 
                self.selected_key_config
            )
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
            self.insert_log_message("Agente listo.")

            # Check for pending user objective from history
            if self.agente.historial_conversacion:
                ultimo_mensaje = self.agente.historial_conversacion[-1]
                if ultimo_mensaje['rol'] == 'usuario':
                    # Check if an agent response is the second to last message
                    if len(self.agente.historial_conversacion) > 1:
                        penultimo_mensaje = self.agente.historial_conversacion[-2]
                        if penultimo_mensaje['rol'] == 'agente':
                            # If the agent already responded, do nothing
                            return

                    objetivo_pendiente = ultimo_mensaje['contenido']
                    self.insert_log_message(f"Objetivo pendiente encontrado: \"{objetivo_pendiente}\"")
                    self.agente._set_initial_objective(objetivo_pendiente) # Call the new method
                    
                    self.loading_bar.grid()
                    self.loading_bar.start(10)
                    
                    self._agent_thread = threading.Thread(target=self.agente.stream_run)
                    self._agent_thread.start()

        except Exception as e:
            self.show_error_and_exit(f"Error al inicializar agente: {e}")

    def _open_provider_manager_window(self):
        ProviderManagerWindow(self.root)

    def show_error_and_exit(self, message):
        messagebox.showerror("Error Crítico", message, parent=self.root)
        self.root.destroy()

    def exit_application(self):
        if self._agent_thread and self._agent_thread.is_alive():
            self.agente.detener_proceso_emergencia()
            self._agent_thread.join(timeout=2) # Esperar un poco a que el hilo termine
        self.root.destroy()

    def _on_stop_clicked(self):
        if self.agente:
            self.agente.detener_proceso_emergencia()
            self.insert_log_message("Solicitud de parada de emergencia enviada.")

    def process_command(self, event=None):
        if event and event.state & 1:
            return self._insert_newline()
            
        command = self.input_entry.get("1.0", tk.END).strip()
        if not command or not self.agente:
            return "break"

        if self._agent_thread and self._agent_thread.is_alive():
            self.insert_log_message("El agente ya está procesando una tarea. Usa 'Detener' o espera a que termine.")
            return "break"
            
        self.insert_message(command, 'user')
        self.input_entry.delete("1.0", tk.END)
        self.loading_bar.grid()
        self.loading_bar.start(10)
        
        self.agente.establecer_objetivo(command)
        self._agent_thread = threading.Thread(target=self.agente.stream_run)
        self._agent_thread.start()

        return "break"

    def insert_message(self, message, role):
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        
        msg_widget = ChatMessage(self.chat_frame, full_message, role)
        
        if role == 'user':
            msg_widget.pack(pady=(5,0), padx=(60,10), anchor='e', fill='x')
        else: # agent or log
            msg_widget.pack(pady=(5,0), padx=(10,60), anchor='w', fill='x')

        self.root.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)
        return msg_widget

    def insert_log_message(self, message):
        self.root.after(0, self._insert_log_message, message)

    def _insert_log_message(self, message):
        msg_widget = tk.Label(self.chat_frame, text=message, fg='gray', font=('Arial', 8), justify='left', anchor='w', bg='white')
        msg_widget.pack(pady=(2,0), padx=10, anchor='w', fill='x')
        self.root.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)

    def mostrar_mensaje_agente(self, token):
        self.root.after(0, self._insert_agent_token, token)

    def finalizar_respuesta_agente(self):
        self.root.after(0, self._finalize_agent_response)

    def _insert_agent_token(self, token):
        if not self._agent_writing:
            self.current_agent_message_widget = self.insert_message("", 'agent')
            self._agent_writing = True
            self.loading_bar.stop()
            self.loading_bar.grid_remove()

        current_text = self.current_agent_message_widget.message
        new_text = current_text + token
        self.current_agent_message_widget.message = new_text
        self.current_agent_message_widget.message_label.config(text=new_text)
        self.root.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)

    def _finalize_agent_response(self):
        self._agent_writing = False
        self.current_agent_message_widget = None
        self.loading_bar.stop()
        self.loading_bar.grid_remove()
        self._agent_thread = None
    
    def _prompt_for_initial_configuration(self):
        if messagebox.askyesno("Configuración Inicial", 
                               "No se encontraron proveedores de modelos. ¿Deseas abrir el gestor para configurarlos ahora?",
                               parent=self.root):
            self._open_provider_manager_window()
        else:
            self.show_error_and_exit("La aplicación no puede funcionar sin proveedores de modelos configurados.")

if __name__ == "__main__":
    root = tk.Tk()
    app = InteractIAGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.exit_application)
    root.mainloop()