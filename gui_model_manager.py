import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
from dotenv import set_key, get_key
from model_manager import refresh_provider_models, load_providers_from_db, update_last_used_model, PROVIDER_MAP
from provider_db_manager import provider_db_manager

class ApiKeyEditDialog(tk.Toplevel):
    """Diálogo para añadir o editar una configuración de API key."""
    def __init__(self, parent, provider_type, key_data=None):
        super().__init__(parent)
        self.transient(parent)
        self.title(f"Clave de API para {provider_type}")
        self.result = None
        self.key_data = key_data or {}
        self.env_path = ".env"

        frame = ttk.Frame(self, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        # Nombre de la variable de entorno
        ttk.Label(frame, text="Nombre de la Variable de Entorno:").grid(row=0, column=0, sticky="w", pady=2)
        self.name_entry = ttk.Entry(frame, width=40)
        self.name_entry.grid(row=0, column=1, sticky="ew")
        self.name_entry.insert(0, self.key_data.get("name", ""))

        # Valor de la API Key
        ttk.Label(frame, text="Valor de la API Key:").grid(row=1, column=0, sticky="w", pady=2)
        self.api_key_entry = ttk.Entry(frame, width=40, show="*")
        self.api_key_entry.grid(row=1, column=1, sticky="ew")

        # Si estamos editando, cargamos el valor actual
        if self.key_data.get("api_key_env_name"):
            key_value = get_key(self.env_path, self.key_data["api_key_env_name"])
            if key_value:
                self.api_key_entry.insert(0, key_value)

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(button_frame, text="Guardar", command=self.on_save).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancelar", command=self.destroy).pack(side="left", padx=5)

        self.grab_set()
        self.wait_window(self)

    def on_save(self):
        name = self.name_entry.get().strip()
        api_key_value = self.api_key_entry.get().strip()
        api_key_env_name = name  # Asumimos que el nombre es la variable de entorno

        if not name:
            messagebox.showerror("Error", "El nombre de la variable es obligatorio.", parent=self)
            return
        
        if not api_key_value:
            messagebox.showerror("Error", "El valor de la API key es obligatorio.", parent=self)
            return

        try:
            # Guardar la clave en el archivo .env
            set_key(self.env_path, api_key_env_name, api_key_value)
            
            # Actualizar el valor en el entorno de la sesión actual
            os.environ[api_key_env_name] = api_key_value
            
            messagebox.showinfo("Éxito", f"La clave '{api_key_env_name}' ha sido guardada.", parent=self)

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo escribir en el archivo .env: {e}", parent=self)
            return

        self.result = self.key_data.copy()
        self.result.update({"name": name, "api_key_env_name": api_key_env_name})
        if "models" not in self.result:
            self.result["models"] = []
        self.destroy()

class ProviderManagerWindow(tk.Toplevel):
    """Ventana para gestionar proveedores, claves de API y modelos."""
    def __init__(self, parent):
        print("Initializing ProviderManagerWindow...")
        super().__init__(parent)
        self.transient(parent)
        self.title("Gestionar Modelos de IA")
        self.geometry("700x400")
        self.parent = parent
        self.providers_data = []

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Layout
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(1, weight=1)

        # Comboboxes
        ttk.Label(main_frame, text="Proveedor:").grid(row=0, column=0, sticky="w")
        self.provider_combo = ttk.Combobox(main_frame, state="readonly")
        self.provider_combo.grid(row=0, column=1, sticky="ew", pady=2)
        self.provider_combo.bind("<<ComboboxSelected>>", self.on_provider_selected)

        ttk.Label(main_frame, text="Clave API:").grid(row=1, column=0, sticky="w")
        self.api_key_combo = ttk.Combobox(main_frame, state="readonly")
        self.api_key_combo.grid(row=1, column=1, sticky="ew", pady=2)
        self.api_key_combo.bind("<<ComboboxSelected>>", self.on_api_key_selected)

        # Models Listbox
        models_frame = ttk.LabelFrame(main_frame, text="Modelos Disponibles", padding="5")
        models_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=5)
        models_frame.rowconfigure(0, weight=1)
        models_frame.columnconfigure(0, weight=1)
        self.models_listbox = tk.Listbox(models_frame)
        self.models_listbox.grid(row=0, column=0, sticky="nsew")
        self.models_listbox.bind("<<ListboxSelect>>", self.on_model_selected)

        # Buttons
        self.api_key_buttons = ttk.Frame(main_frame)
        self.api_key_buttons.grid(row=1, column=2, padx=5)
        self.add_key_btn = ttk.Button(self.api_key_buttons, text="Añadir", command=self.add_api_key)
        self.add_key_btn.pack(side="left")
        self.edit_key_btn = ttk.Button(self.api_key_buttons, text="Editar", command=self.edit_api_key)
        self.edit_key_btn.pack(side="left")
        self.del_key_btn = ttk.Button(self.api_key_buttons, text="Eliminar", command=self.delete_api_key)
        self.del_key_btn.pack(side="left")

        self.refresh_btn = ttk.Button(main_frame, text="Refrescar Modelos", command=self.refresh_models)
        self.refresh_btn.grid(row=3, column=1, sticky="e", pady=5)

        # New button for selecting model and restarting app
        selection_frame = ttk.Frame(main_frame)
        selection_frame.grid(row=4, column=0, columnspan=3, pady=(10, 0), sticky="ew")
        selection_frame.columnconfigure(0, weight=1) # Center the button

        self.select_and_restart_btn = ttk.Button(selection_frame, text="Seleccionar y Reiniciar", command=self.select_and_restart, state="disabled")
        self.select_and_restart_btn.pack() # Use pack to center within its frame if it only has one button


        self.load_data_and_populate()
        self.grab_set()
        self.wait_window(self)
        print("ProviderManagerWindow initialized and waiting.")

    def load_data_and_populate(self):
        self.providers_data = load_providers_from_db()
        provider_types = list(PROVIDER_MAP.keys())
        self.provider_combo["values"] = provider_types

        # Find and select the last used provider, key, and model
        last_used_provider = None
        last_used_key = None
        for provider in self.providers_data:
            for key_config in provider.get("api_keys", []):
                if any(m.get("is_last_used") for m in key_config.get("models", [])):
                    last_used_provider = provider["provider_type"]
                    last_used_key = key_config["name"]
                    break
            if last_used_provider:
                break
        
        if last_used_provider:
            self.provider_combo.set(last_used_provider)
            self.on_provider_selected(None, select_key=last_used_key)
        elif provider_types:
            self.provider_combo.set(provider_types[0])
            self.on_provider_selected(None)

    def on_provider_selected(self, event, select_key=None):
        provider_type = self.provider_combo.get()
        provider = next((p for p in self.providers_data if p["provider_type"] == provider_type), None)
        
        key_names = []
        if provider:
            key_names = [k["name"] for k in provider.get("api_keys", [])]

        self.api_key_combo["values"] = key_names
        self.models_listbox.delete(0, tk.END)

        if select_key and select_key in key_names:
            self.api_key_combo.set(select_key)
            self.on_api_key_selected(None)
        elif key_names:
            self.api_key_combo.set(key_names[0])
            self.on_api_key_selected(None)
        else:
            self.api_key_combo.set("")

    def on_api_key_selected(self, event):
        provider_type = self.provider_combo.get()
        key_name = self.api_key_combo.get()
        provider = next((p for p in self.providers_data if p["provider_type"] == provider_type), None)
        if not provider or not key_name:
            return

        key_config = next((k for k in provider.get("api_keys", []) if k["name"] == key_name), None)
        self.models_listbox.delete(0, tk.END)
        if not key_config or not key_config.get("models"):
            return

        last_used_model_idx = -1
        for i, model in enumerate(key_config["models"]):
            self.models_listbox.insert(tk.END, model["name"])
            if model.get("is_last_used"):
                last_used_model_idx = i
        
        if last_used_model_idx != -1:
            self.models_listbox.selection_set(last_used_model_idx)

    def on_model_selected(self, event):
        if not self.models_listbox.curselection():
            self.select_and_restart_btn.config(state="disabled")
            return
        provider_type = self.provider_combo.get()
        key_name = self.api_key_combo.get()
        model_name = self.models_listbox.get(self.models_listbox.curselection()[0])
        update_last_used_model(provider_type, key_name, model_name) # Keep this as it updates last used on selection
        self.select_and_restart_btn.config(state="normal") # Enable the button

    def add_api_key(self):
        provider_type = self.provider_combo.get()
        if not provider_type:
            messagebox.showwarning("Atención", "Selecciona un proveedor primero.", parent=self)
            return
        
        dialog = ApiKeyEditDialog(self, provider_type)
        if dialog.result:
            provider_db_manager.add_api_key_config(provider_type, dialog.result)
            self.load_data_and_populate()

    def edit_api_key(self):
        provider_type = self.provider_combo.get()
        key_name = self.api_key_combo.get()
        if not provider_type or not key_name:
            return

        provider = next((p for p in self.providers_data if p["provider_type"] == provider_type), None)
        key_config = next((k for k in provider["api_keys"] if k["name"] == key_name), None)

        dialog = ApiKeyEditDialog(self, provider_type, key_data=key_config)
        if dialog.result:
            provider_db_manager.update_api_key_config(provider_type, key_name, dialog.result)
            self.load_data_and_populate()

    def delete_api_key(self):
        provider_type = self.provider_combo.get()
        key_name = self.api_key_combo.get()
        if not provider_type or not key_name:
            return

        if messagebox.askyesno("Confirmar", f"¿Eliminar la clave '{key_name}'?", parent=self):
            provider_db_manager.delete_api_key_config(provider_type, key_name)
            self.load_data_and_populate()

    def refresh_models(self):
        provider_type = self.provider_combo.get()
        key_name = self.api_key_combo.get()
        if not provider_type or not key_name:
            messagebox.showwarning("Atención", "Selecciona un proveedor y una clave API.", parent=self)
            return

        messagebox.showinfo("Refrescando", f"Refrescando modelos para {key_name}...", parent=self)
        threading.Thread(target=self._refresh_thread, args=(provider_type, key_name)).start()

    def _refresh_thread(self, provider_type, key_name):
        try:
            refresh_provider_models(provider_type, key_name)
            self.after(0, self.load_data_and_populate)
            self.after(0, lambda: messagebox.showinfo("Éxito", "Modelos actualizados.", parent=self))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"No se pudieron refrescar los modelos: {e}", parent=self))

    def select_and_restart(self):
        provider_type = self.provider_combo.get()
        key_name = self.api_key_combo.get()
        if not self.models_listbox.curselection():
            messagebox.showwarning("Selección Incompleta", "Por favor, selecciona un modelo de la lista.", parent=self)
            return
        model_name = self.models_listbox.get(self.models_listbox.curselection()[0])

        messagebox.showinfo("Reiniciando Aplicación", 
                            "La aplicación se cerrará y se reiniciará con el modelo seleccionado.", 
                            parent=self)
        if messagebox.askyesno("Confirmar Selección", 
                               f"Se establecerá '{model_name}' como el modelo predeterminado y la aplicación se cerrará para aplicar los cambios.\n\n¿Deseas continuar?", 
                               parent=self):
            update_last_used_model(provider_type, key_name, model_name)
            # Call a method in the parent (main GUI) to handle the exit
            if hasattr(self.parent, "exit_application"):
                self.parent.exit_application()
            else:
                self.parent.destroy() # Fallback if for some reason the parent doesn't have it

    def on_close(self):
        print("ProviderManagerWindow closing.")
        if hasattr(self.parent, "reload_providers_config"):
            self.parent.reload_providers_config()
        print("Destroying ProviderManagerWindow...")
        self.destroy()