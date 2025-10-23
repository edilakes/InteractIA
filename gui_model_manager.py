import tkinter as tk
from tkinter import ttk, messagebox
import json
import threading

from model_manager import refresh_provider_models, load_providers_from_file, get_model_provider, _update_last_used_model

class ProviderEditDialog(tk.Toplevel):
    """Diálogo para añadir o editar una configuración de proveedor."""
    def __init__(self, parent, provider_data=None):
        super().__init__(parent)
        self.transient(parent)
        self.title("Añadir/Editar Proveedor")
        self.result = None
        self.provider_data = provider_data or {}

        frame = ttk.Frame(self, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text="Nombre de Configuración:").grid(row=0, column=0, sticky="w", pady=2)
        self.name_entry = ttk.Entry(frame, width=40)
        self.name_entry.grid(row=0, column=1, sticky="ew")
        self.name_entry.insert(0, self.provider_data.get("name", ""))

        ttk.Label(frame, text="Tipo de Proveedor:").grid(row=1, column=0, sticky="w", pady=2)
        self.type_combo = ttk.Combobox(frame, values=["gemini"], state="readonly")
        self.type_combo.grid(row=1, column=1, sticky="ew")
        self.type_combo.set(self.provider_data.get("provider_type", "gemini"))

        ttk.Label(frame, text="Variable de Entorno (API Key):").grid(row=2, column=0, sticky="w", pady=2)
        self.api_key_env_entry = ttk.Entry(frame)
        self.api_key_env_entry.grid(row=2, column=1, sticky="ew")
        self.api_key_env_entry.insert(0, self.provider_data.get("config", {}).get("api_key_env", ""))

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(button_frame, text="Guardar", command=self.on_save).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancelar", command=self.destroy).pack(side="left", padx=5)

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.wait_window(self)

    def on_save(self):
        name = self.name_entry.get().strip()
        provider_type = self.type_combo.get()
        api_key_env = self.api_key_env_entry.get().strip()

        if not all([name, provider_type, api_key_env]):
            messagebox.showerror("Error de Validación", "Todos los campos son obligatorios.", parent=self)
            return

        self.result = {
            "id": self.provider_data.get("id", f"{provider_type}-{name.lower().replace(' ', '-')}"),
            "name": name,
            "provider_type": provider_type,
            "config": {"api_key_env": api_key_env}
        }
        self.destroy()

class ProviderManagerWindow(tk.Toplevel):
    """Ventana para gestionar las configuraciones de proveedores de IA.""" 
    def __init__(self, parent, providers_config: list):
        super().__init__(parent)
        self.transient(parent)
        self.title("Gestionar Proveedores de IA")
        self.geometry("600x500") # Adjusted geometry for two listboxes
        self.parent = parent
        self.providers_config = list(providers_config)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1) # Row for providers list
        self.grid_rowconfigure(1, weight=1) # Row for models list
        self.grid_rowconfigure(2, weight=0) # Row for buttons

        # --- Providers Frame ---
        providers_frame = ttk.LabelFrame(self, text="Proveedores", padding="10")
        providers_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        providers_frame.grid_rowconfigure(0, weight=1)
        providers_frame.grid_columnconfigure(0, weight=1)

        self.providers_listbox = tk.Listbox(providers_frame)
        self.providers_listbox.grid(row=0, column=0, sticky="nsew")
        self.providers_listbox.bind("<<ListboxSelect>>", self._on_list_select)

        providers_scrollbar = ttk.Scrollbar(providers_frame, orient="vertical", command=self.providers_listbox.yview)
        providers_scrollbar.grid(row=0, column=1, sticky="ns")
        self.providers_listbox.config(yscrollcommand=providers_scrollbar.set)

        # --- Models Frame ---
        models_frame = ttk.LabelFrame(self, text="Modelos del Proveedor Seleccionado", padding="10")
        models_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        models_frame.grid_rowconfigure(0, weight=1)
        models_frame.grid_columnconfigure(0, weight=1)

        self.models_listbox = tk.Listbox(models_frame)
        self.models_listbox.grid(row=0, column=0, sticky="nsew")
        self.models_listbox.bind("<<ListboxSelect>>", self._on_model_list_select) # New binding for model selection

        models_scrollbar = ttk.Scrollbar(models_frame, orient="vertical", command=self.models_listbox.yview)
        models_scrollbar.grid(row=0, column=1, sticky="ns")
        self.models_listbox.config(yscrollcommand=models_scrollbar.set)

        # --- Button Frame ---
        self.button_frame = ttk.Frame(self) # Make button_frame an instance variable
        self.button_frame.grid(row=2, column=0, pady=10)

        self.add_button = ttk.Button(self.button_frame, text="Añadir...", command=self.add_provider)
        self.add_button.pack(side="left", padx=5)
        self.edit_button = ttk.Button(self.button_frame, text="Editar...", command=self.edit_provider, state="disabled")
        self.edit_button.pack(side="left", padx=5)
        self.delete_button = ttk.Button(self.button_frame, text="Eliminar", command=self.delete_provider, state="disabled")
        self.delete_button.pack(side="left", padx=5)

        self.refresh_models_button = ttk.Button(self.button_frame, text="Refrescar Modelos", command=self.refresh_models_for_selected_provider, state="disabled")
        self.refresh_models_button.pack(side="left", padx=5)

        ttk.Button(self.button_frame, text="Cerrar", command=self.on_close).pack(side="right", padx=5)

        self.refresh_listbox()

    def refresh_listbox(self):
        self.providers_config = load_providers_from_file() # Reload providers config
        self.providers_listbox.delete(0, tk.END)
        
        if not self.providers_config:
            self.models_listbox.delete(0, tk.END)
            self.edit_button.config(state="disabled")
            self.delete_button.config(state="disabled")
            self.refresh_models_button.config(state="disabled")
            messagebox.showinfo("Configuración", "No se encontraron proveedores. Por favor, añada uno.", parent=self)
            return

        # Try to find the last used provider and model
        found_last_used = False
        selected_provider_idx = 0
        selected_model_name = None

        for i, provider_config in enumerate(self.providers_config):
            self.providers_listbox.insert(tk.END, provider_config['name'])
            if "available_models" in provider_config and provider_config["available_models"]:
                for model in provider_config["available_models"]:
                    if model.get("is_last_used"):
                        selected_provider_idx = i
                        selected_model_name = model["name"]
                        found_last_used = True
                        break
            if found_last_used:
                break
        
        # If no last used model found, or provider has no models, use fallback logic
        if not found_last_used or not self.providers_config[selected_provider_idx].get("available_models"):
            # Select the first provider
            selected_provider_idx = 0
            current_provider_config = self.providers_config[selected_provider_idx]
            provider_id = current_provider_config.get("id")

            if provider_id:
                messagebox.showinfo("Configuración Inicial", f"Configurando proveedor '{current_provider_config['name']}'. Refrescando modelos...", parent=self)
                try:
                    # Refresh models in a separate thread to avoid freezing the UI
                    threading.Thread(target=self._perform_initial_refresh_and_select, args=(provider_id, selected_provider_idx)).start()
                    return # Exit to let the thread handle UI updates
                except Exception as e:
                    messagebox.showerror("Error", f"Error al refrescar modelos iniciales: {e}", parent=self)
            else:
                messagebox.showwarning("Advertencia", "El primer proveedor no tiene un ID válido.", parent=self)
                # Fallback to disabling buttons if even first provider is invalid
                self.models_listbox.delete(0, tk.END)
                self.edit_button.config(state="disabled")
                self.delete_button.config(state="disabled")
                self.refresh_models_button.config(state="disabled")
                return

        # If a last used model was found, or after fallback refresh, update UI
        self.providers_listbox.selection_set(selected_provider_idx)
        self._update_models_display(selected_provider_idx, selected_model_name)
        self._set_button_states(True)

    def _perform_initial_refresh_and_select(self, provider_id, selected_provider_idx):
        try:
            refresh_provider_models(provider_id)
            # Reload providers_config after refresh
            self.providers_config = load_providers_from_file()
            current_provider_config = self.providers_config[selected_provider_idx]

            # Select the first model in the newly refreshed list as last used
            if "available_models" in current_provider_config and current_provider_config["available_models"]:
                first_model_name = current_provider_config["available_models"][0]["name"]
                _update_last_used_model(provider_id, first_model_name)
                selected_model_name = first_model_name
            else:
                selected_model_name = None
            
            # Update UI on the main thread
            self.parent.after(0, lambda: self._update_ui_after_initial_refresh(selected_provider_idx, selected_model_name))
        except Exception as e:
            self.parent.after(0, lambda: messagebox.showerror("Error", f"Error en el refresco inicial en segundo plano: {e}", parent=self))

    def _update_ui_after_initial_refresh(self, selected_provider_idx, selected_model_name):
        self.providers_listbox.selection_set(selected_provider_idx)
        self._update_models_display(selected_provider_idx, selected_model_name)
        self._set_button_states(True)
        if hasattr(self.parent, "reload_providers_config"):
            self.parent.reload_providers_config()
        messagebox.showinfo("Configuración Inicial", "Modelos refrescados y configurados correctamente.", parent=self)

    def _update_models_display(self, provider_idx, model_to_select_name=None):
        self.models_listbox.delete(0, tk.END)
        selected_provider = self.providers_config[provider_idx]
        if "available_models" in selected_provider and selected_provider["available_models"]:
            for i, model in enumerate(selected_provider["available_models"]):
                self.models_listbox.insert(tk.END, model["name"])
                if model.get("name") == model_to_select_name:
                    self.models_listbox.selection_set(i)
                    self.models_listbox.see(i)

    def _set_button_states(self, enable: bool):
        state = "normal" if enable else "disabled"
        self.edit_button.config(state=state)
        self.delete_button.config(state=state)
        self.refresh_models_button.config(state=state)

    def _on_list_select(self, event):
        cur_selection = self.providers_listbox.curselection()
        if cur_selection:
            idx = cur_selection[0]
            self._update_models_display(idx)
            self._set_button_states(True)
        else:
            self.models_listbox.delete(0, tk.END)
            self._set_button_states(False)

    def _on_model_list_select(self, event):
        # This method is called when a model is selected in the models_listbox
        # We need to update the is_last_used flag in providers.json
        cur_provider_selection = self.providers_listbox.curselection()
        cur_model_selection = self.models_listbox.curselection()

        if cur_provider_selection and cur_model_selection:
            provider_idx = cur_provider_selection[0]
            model_idx = cur_model_selection[0]
            selected_provider = self.providers_config[provider_idx]
            selected_model_name = selected_provider["available_models"][model_idx]["name"]
            _update_last_used_model(selected_provider["id"], selected_model_name)
            # Also notify main GUI to reload if necessary
            if hasattr(self.parent, "reload_providers_config"):
                self.parent.reload_providers_config()

    def add_provider(self):
        dialog = ProviderEditDialog(self)
        if dialog.result:
            # Ensure new provider has an empty available_models list
            if "available_models" not in dialog.result:
                dialog.result["available_models"] = []
            self.providers_config.append(dialog.result)
            self.refresh_listbox()

    def edit_provider(self):
        idx = self.providers_listbox.curselection()[0]
        dialog = ProviderEditDialog(self, provider_data=self.providers_config[idx])
        if dialog.result:
            # Preserve available_models if not explicitly set in dialog.result
            if "available_models" not in dialog.result and "available_models" in self.providers_config[idx]:
                dialog.result["available_models"] = self.providers_config[idx]["available_models"]
            elif "available_models" not in dialog.result:
                dialog.result["available_models"] = []
            self.providers_config[idx] = dialog.result
            self.refresh_listbox()

    def delete_provider(self):
        idx = self.providers_listbox.curselection()[0]
        if messagebox.askyesno("Confirmar", f"¿Seguro que quieres eliminar '{self.providers_config[idx]['name']}'?", parent=self):
            del self.providers_config[idx]
            self.refresh_listbox()

    def on_close(self):
        try:
            # No need to write providers.json here, as _update_last_used_model and refresh_provider_models handle it
            if hasattr(self.parent, "reload_providers_config"):
                self.parent.reload_providers_config()
        except Exception as e:
            messagebox.showerror("Error", f"Error al cerrar la ventana: {e}", parent=self)
        self.destroy()

    def refresh_models_for_selected_provider(self):
        cur_selection = self.providers_listbox.curselection()
        if not cur_selection:
            return

        idx = cur_selection[0]
        selected_provider = self.providers_config[idx]
        provider_id = selected_provider.get("id")

        if provider_id:
            try:
                messagebox.showinfo("Refrescando Modelos", f"Refrescando modelos para {selected_provider['name']}...", parent=self)
                # Perform refresh in a separate thread
                threading.Thread(target=self._perform_refresh_and_update_ui, args=(provider_id, idx)).start()
            except Exception as e:
                messagebox.showerror("Error al Refrescar Modelos", f"Ocurrió un error: {e}", parent=self)
        else:
            messagebox.showwarning("Advertencia", "El proveedor seleccionado no tiene un ID.", parent=self)

    def _perform_refresh_and_update_ui(self, provider_id, provider_idx):
        try:
            refresh_provider_models(provider_id)
            self.providers_config = load_providers_from_file() # Reload config after refresh
            self.parent.after(0, lambda: self._update_ui_after_refresh(provider_idx))
        except Exception as e:
            self.parent.after(0, lambda: messagebox.showerror("Error", f"Error al refrescar modelos en segundo plano: {e}", parent=self))

    def _update_ui_after_refresh(self, provider_idx):
        # Re-select the provider in the listbox to trigger models list update
        self.providers_listbox.selection_clear(0, tk.END)
        self.providers_listbox.selection_set(provider_idx)
        self._on_list_select(None) # This will update the models listbox and button states

        # Notify the main GUI to reload its configuration
        if hasattr(self.parent, "reload_providers_config"):
            self.parent.reload_providers_config()

        messagebox.showinfo("Refrescando Modelos", "Modelos actualizados correctamente.", parent=self)
