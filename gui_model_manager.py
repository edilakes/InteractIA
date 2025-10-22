import tkinter as tk
from tkinter import ttk, messagebox
import json

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
        self.geometry("500x400")
        self.parent = parent
        self.providers_config = list(providers_config)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        list_frame = ttk.Frame(self, padding="10")
        list_frame.grid(row=0, column=0, sticky="nsew")
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.providers_listbox = tk.Listbox(list_frame)
        self.providers_listbox.grid(row=0, column=0, sticky="nsew")
        self.providers_listbox.bind("<<ListboxSelect>>", self._on_list_select)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.providers_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.providers_listbox.config(yscrollcommand=scrollbar.set)

        button_frame = ttk.Frame(self)
        button_frame.grid(row=1, column=0, pady=10)

        self.add_button = ttk.Button(button_frame, text="Añadir...", command=self.add_provider)
        self.add_button.pack(side="left", padx=5)
        self.edit_button = ttk.Button(button_frame, text="Editar...", command=self.edit_provider, state="disabled")
        self.edit_button.pack(side="left", padx=5)
        self.delete_button = ttk.Button(button_frame, text="Eliminar", command=self.delete_provider, state="disabled")
        self.delete_button.pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cerrar", command=self.on_close).pack(side="right", padx=5)

        self.refresh_listbox()

    def refresh_listbox(self):
        self.providers_listbox.delete(0, tk.END)
        for provider in self.providers_config:
            self.providers_listbox.insert(tk.END, provider['name'])
        self._on_list_select(None)

    def _on_list_select(self, event):
        state = "normal" if self.providers_listbox.curselection() else "disabled"
        self.edit_button.config(state=state)
        self.delete_button.config(state=state)

    def add_provider(self):
        dialog = ProviderEditDialog(self)
        if dialog.result:
            self.providers_config.append(dialog.result)
            self.refresh_listbox()

    def edit_provider(self):
        idx = self.providers_listbox.curselection()[0]
        dialog = ProviderEditDialog(self, provider_data=self.providers_config[idx])
        if dialog.result:
            self.providers_config[idx] = dialog.result
            self.refresh_listbox()

    def delete_provider(self):
        idx = self.providers_listbox.curselection()[0]
        if messagebox.askyesno("Confirmar", f"¿Seguro que quieres eliminar '{self.providers_config[idx]['name']}'?", parent=self):
            del self.providers_config[idx]
            self.refresh_listbox()

    def on_close(self):
        try:
            with open("providers.json", "w", encoding="utf-8") as f:
                json.dump(self.providers_config, f, indent=2, ensure_ascii=False)
            if hasattr(self.parent, "reload_providers_config"):
                self.parent.reload_providers_config()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo escribir en providers.json: {e}", parent=self)
        self.destroy()