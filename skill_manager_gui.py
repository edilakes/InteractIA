import tkinter as tk
from tkinter import ttk, messagebox
from knowledge_base import KnowledgeBase
import json

class SkillManagerGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Gestión de Habilidades")
        self.master.geometry("900x700")

        self.kb = KnowledgeBase()
        if not self.kb.client:
            messagebox.showerror("Error de Conexión", "No se pudo conectar a la base de datos de conocimiento.")
            self.master.destroy()
            return

        self._create_widgets()
        self._populate_skill_list()
        self._clear_detail_panel() # Start with a clean detail panel

    def _create_widgets(self):
        # Main frame for layout
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1) # Skill list column
        main_frame.columnconfigure(1, weight=2) # Detail panel column
        main_frame.rowconfigure(0, weight=1)

        # --- Left Panel: Skill List ---
        list_frame = ttk.LabelFrame(main_frame, text="Habilidades Existentes", padding="10")
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self.skill_list = ttk.Treeview(list_frame, columns=("Nombre",), show="headings")
        self.skill_list.heading("Nombre", text="Nombre de Habilidad")
        self.skill_list.pack(fill=tk.BOTH, expand=True)
        self.skill_list.bind("<<TreeviewSelect>>", self._on_skill_select)

        list_scrollbar = ttk.Scrollbar(self.skill_list, orient=tk.VERTICAL, command=self.skill_list.yview)
        self.skill_list.configure(yscrollcommand=list_scrollbar.set)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Right Panel: Skill Details/Editor ---
        detail_frame = ttk.LabelFrame(main_frame, text="Detalles de Habilidad", padding="10")
        detail_frame.grid(row=0, column=1, sticky="nsew")
        detail_frame.columnconfigure(1, weight=1) # Make entry/text fields expand

        # Skill Name
        ttk.Label(detail_frame, text="Nombre:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(detail_frame, state="readonly")
        self.name_entry.grid(row=0, column=1, sticky="ew", pady=5)

        # Skill Type (fixed for now)
        ttk.Label(detail_frame, text="Tipo:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.type_var = tk.StringVar(value="Habilidad")
        self.type_entry = ttk.Entry(detail_frame, textvariable=self.type_var, state="readonly")
        self.type_entry.grid(row=1, column=1, sticky="ew", pady=5)

        # Skill Data (JSON content)
        ttk.Label(detail_frame, text="Contenido (JSON):").grid(row=2, column=0, sticky=tk.NW, pady=5)
        self.data_text = tk.Text(detail_frame, height=20, width=60, state="disabled", wrap=tk.WORD)
        self.data_text.grid(row=2, column=1, sticky="nsew", pady=5)
        detail_frame.rowconfigure(2, weight=1) # Make text area expand

        data_scrollbar = ttk.Scrollbar(self.data_text, orient=tk.VERTICAL, command=self.data_text.yview)
        self.data_text.configure(yscrollcommand=data_scrollbar.set)
        data_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        button_frame = ttk.Frame(detail_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)

        self.new_button = ttk.Button(button_frame, text="Nueva Habilidad", command=self._new_skill)
        self.new_button.pack(side=tk.LEFT, padx=5)

        self.edit_button = ttk.Button(button_frame, text="Editar", command=self._edit_skill, state="disabled")
        self.edit_button.pack(side=tk.LEFT, padx=5)

        self.save_button = ttk.Button(button_frame, text="Guardar", command=self._save_skill, state="disabled")
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.delete_button = ttk.Button(button_frame, text="Eliminar", command=self._delete_skill, state="disabled")
        self.delete_button.pack(side=tk.LEFT, padx=5)

        self.cancel_button = ttk.Button(button_frame, text="Cancelar", command=self._cancel_edit, state="disabled")
        self.cancel_button.pack(side=tk.LEFT, padx=5)

        self.current_skill_name = None # To keep track of the skill being edited/viewed

    def _populate_skill_list(self):
        for i in self.skill_list.get_children():
            self.skill_list.delete(i)
        
        skills = self.kb.get_all_skills()
        for skill in skills:
            self.skill_list.insert("", tk.END, values=(skill["nombre_recurso"],), iid=skill["nombre_recurso"])
        
        self._clear_detail_panel()
        self._set_detail_panel_state("disabled")
        self.edit_button.config(state="disabled")
        self.delete_button.config(state="disabled")

    def _on_skill_select(self, event):
        selected_item = self.skill_list.focus()
        if not selected_item:
            self._clear_detail_panel()
            self._set_detail_panel_state("disabled")
            self.edit_button.config(state="disabled")
            self.delete_button.config(state="disabled")
            return

        skill_name = self.skill_list.item(selected_item, "values")[0]
        self.current_skill_name = skill_name
        skill_data = self.kb.conocer_habilidad(skill_name)
        
        self._clear_detail_panel()
        self.name_entry.config(state="normal")
        self.name_entry.insert(0, skill_data["nombre_recurso"])
        self.name_entry.config(state="readonly")

        self.type_entry.config(state="normal")
        self.type_entry.delete(0, tk.END)
        self.type_entry.insert(0, skill_data["tipo_recurso"])
        self.type_entry.config(state="readonly")

        self.data_text.config(state="normal")
        self.data_text.delete("1.0", tk.END)
        try:
            # Pretty print JSON for readability
            self.data_text.insert(tk.END, json.dumps(skill_data["datos"], indent=4, ensure_ascii=False))
        except Exception as e:
            self.data_text.insert(tk.END, str(skill_data["datos"])) # Fallback if not valid JSON
            messagebox.showwarning("Advertencia", f"El contenido de la habilidad no es JSON válido: {e}")
        self.data_text.config(state="disabled")

        self._set_detail_panel_state("readonly")
        self.edit_button.config(state="normal")
        self.delete_button.config(state="normal")
        self.save_button.config(state="disabled")
        self.cancel_button.config(state="disabled")

    def _new_skill(self):
        self._clear_detail_panel()
        self._set_detail_panel_state("normal")
        self.name_entry.config(state="normal") # Name is editable for new skills
        self.type_var.set("Habilidad") # Default type for new skills
        self.current_skill_name = None # No current skill selected
        self.edit_button.config(state="disabled")
        self.delete_button.config(state="disabled")
        self.save_button.config(state="normal")
        self.cancel_button.config(state="normal")

    def _edit_skill(self):
        if not self.current_skill_name:
            return
        self._set_detail_panel_state("normal")
        self.name_entry.config(state="readonly") # Name is not editable when editing existing skill
        self.edit_button.config(state="disabled")
        self.delete_button.config(state="disabled")
        self.save_button.config(state="normal")
        self.cancel_button.config(state="normal")

    def _save_skill(self):
        name = self.name_entry.get().strip()
        skill_type = self.type_var.get().strip()
        data_str = self.data_text.get("1.0", tk.END).strip()

        if not name:
            messagebox.showerror("Error", "El nombre de la habilidad no puede estar vacío.")
            return
        
        try:
            skill_data_json = json.loads(data_str)
        except json.JSONDecodeError:
            messagebox.showerror("Error", "El contenido de la habilidad debe ser un JSON válido.")
            return

        # Check if skill name already exists for new skills
        if not self.current_skill_name: # This is a new skill
            if self.kb.conocer_habilidad(name):
                messagebox.showerror("Error", f"Ya existe una habilidad con el nombre '{name}'.")
                return
        
        self.kb.aprender_habilidad(name, skill_type, skill_data_json)
        messagebox.showinfo("Éxito", f"Habilidad '{name}' guardada exitosamente.")
        self._populate_skill_list()
        self._clear_detail_panel()
        self._set_detail_panel_state("disabled")
        self.save_button.config(state="disabled")
        self.cancel_button.config(state="disabled")
        self.new_button.config(state="normal") # Re-enable new button

    def _delete_skill(self):
        if not self.current_skill_name:
            return
        
        if messagebox.askyesno("Confirmar Eliminación", f"¿Está seguro de que desea eliminar la habilidad '{self.current_skill_name}'?"):
            self.kb.olvidar_habilidad(self.current_skill_name)
            messagebox.showinfo("Éxito", f"Habilidad '{self.current_skill_name}' eliminada.")
            self._populate_skill_list()
            self._clear_detail_panel()
            self._set_detail_panel_state("disabled")
            self.edit_button.config(state="disabled")
            self.delete_button.config(state="disabled")
            self.save_button.config(state="disabled")
            self.cancel_button.config(state="disabled")

    def _cancel_edit(self):
        self._clear_detail_panel()
        self._set_detail_panel_state("disabled")
        self.save_button.config(state="disabled")
        self.cancel_button.config(state="disabled")
        self.new_button.config(state="normal")
        # If a skill was selected before, re-select it to show its details
        if self.current_skill_name:
            self.skill_list.selection_set(self.current_skill_name)
            self._on_skill_select(None)
        else:
            self.edit_button.config(state="disabled")
            self.delete_button.config(state="disabled")

    def _clear_detail_panel(self):
        self.name_entry.config(state="normal")
        self.name_entry.delete(0, tk.END)
        self.name_entry.config(state="readonly")

        self.type_entry.config(state="normal")
        self.type_entry.delete(0, tk.END)
        self.type_entry.insert(0, "Habilidad") # Default type
        self.type_entry.config(state="readonly")

        self.data_text.config(state="normal")
        self.data_text.delete("1.0", tk.END)
        self.data_text.config(state="disabled")
        self.current_skill_name = None

    def _set_detail_panel_state(self, state):
        # 'normal' for editable, 'readonly' for view-only, 'disabled' for empty
        if state == "normal":
            self.name_entry.config(state="normal")
            self.type_entry.config(state="normal")
            self.data_text.config(state="normal")
        elif state == "readonly":
            self.name_entry.config(state="readonly")
            self.type_entry.config(state="readonly")
            self.data_text.config(state="disabled")
        elif state == "disabled":
            self.name_entry.config(state="disabled")
            self.type_entry.config(state="disabled")
            self.data_text.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = SkillManagerGUI(tk.Toplevel(root))
    root.withdraw() # Hide the root window
    root.mainloop()
