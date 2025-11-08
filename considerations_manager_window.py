import tkinter as tk
from tkinter import ttk, messagebox
from considerations_db_manager import considerations_db_manager
from bson.objectid import ObjectId

class AddEditConsiderationDialog(tk.Toplevel):
    def __init__(self, parent, consideration_data=None):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("Añadir/Editar Consideración")
        self.result = None  # Para almacenar el resultado de la operación

        self.consideration_data = consideration_data if consideration_data else {}

        frame = ttk.Frame(self, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text="Nombre:").grid(row=0, column=0, sticky="w", pady=2)
        self.name_entry = ttk.Entry(frame, width=50)
        self.name_entry.grid(row=0, column=1, sticky="ew", pady=2)
        self.name_entry.insert(0, self.consideration_data.get("nombre", ""))

        ttk.Label(frame, text="Contenido:").grid(row=1, column=0, sticky="nw", pady=2)
        self.content_text = tk.Text(frame, width=50, height=10)
        self.content_text.grid(row=1, column=1, sticky="ew", pady=2)
        self.content_text.insert(tk.END, self.consideration_data.get("contenido", ""))

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(button_frame, text="Guardar", command=self.on_save).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancelar", command=self.destroy).pack(side="left", padx=5)

        self.wait_window(self)

    def on_save(self):
        nombre = self.name_entry.get().strip()
        contenido = self.content_text.get("1.0", tk.END).strip()

        if not nombre or not contenido:
            messagebox.showerror("Error", "Nombre y contenido no pueden estar vacíos.", parent=self)
            return

        self.result = {"nombre": nombre, "contenido": contenido}
        self.destroy()


class ConsiderationsManagerWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("Gestionar Consideraciones Adicionales")
        self.geometry("800x600")
        self.parent = parent

        # Frame principal
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # Treeview para mostrar las consideraciones
        self.tree = ttk.Treeview(main_frame, columns=("Nombre", "Fecha Creación", "Fecha Actualización"), show="headings")
        self.tree.heading("Nombre", text="Nombre")
        self.tree.heading("Fecha Creación", text="Fecha Creación")
        self.tree.heading("Fecha Actualización", text="Fecha Actualización")
        self.tree.column("Nombre", width=200)
        self.tree.column("Fecha Creación", width=150, anchor="center")
        self.tree.column("Fecha Actualización", width=150, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew", columnspan=2)

        # Scrollbar para el Treeview
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=2, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Botones de acción
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=3, pady=(10, 0), sticky="ew")
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)

        ttk.Button(button_frame, text="Añadir", command=self.add_consideration).grid(row=0, column=0, padx=5, sticky="ew")
        ttk.Button(button_frame, text="Editar", command=self.edit_consideration).grid(row=0, column=1, padx=5, sticky="ew")
        ttk.Button(button_frame, text="Eliminar", command=self.delete_consideration).grid(row=0, column=2, padx=5, sticky="ew")

        self.load_considerations()
        self.wait_window(self)

    def load_considerations(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            considerations = considerations_db_manager.get_all_considerations()
            for cons in considerations:
                # Convertir ObjectId a string para mostrar
                _id_str = str(cons["_id"])
                nombre = cons["nombre"]
                fecha_creacion = cons["fecha_creacion"].strftime("%Y-%m-%d %H:%M")
                fecha_actualizacion = cons["fecha_actualizacion"].strftime("%Y-%m-%d %M:%S")
                self.tree.insert("", tk.END, iid=_id_str, values=(nombre, fecha_creacion, fecha_actualizacion))
        except Exception as e:
            messagebox.showerror("Error de Base de Datos", f"No se pudieron cargar las consideraciones: {e}", parent=self)

    def add_consideration(self):
        dialog = AddEditConsiderationDialog(self)
        if dialog.result:
            try:
                considerations_db_manager.add_consideration(dialog.result["nombre"], dialog.result["contenido"])
                self.load_considerations()
            except ValueError as ve:
                messagebox.showwarning("Advertencia", str(ve), parent=self)
            except Exception as e:
                messagebox.showerror("Error", f"Error al añadir consideración: {e}", parent=self)

    def edit_consideration(self):
        selected_item_id = self.tree.focus()
        if not selected_item_id:
            messagebox.showwarning("Advertencia", "Selecciona una consideración para editar.", parent=self)
            return

        try:
            # Recuperar la consideración completa de la base de datos usando el ID
            consideration_id = ObjectId(selected_item_id)
            consideration = considerations_db_manager.collection.find_one({"_id": consideration_id})

            if consideration:
                dialog = AddEditConsiderationDialog(self, consideration_data=consideration)
                if dialog.result:
                    considerations_db_manager.update_consideration(
                        selected_item_id, dialog.result["nombre"], dialog.result["contenido"]
                    )
                    self.load_considerations()
            else:
                messagebox.showwarning("Advertencia", "Consideración no encontrada.", parent=self)
        except ValueError as ve:
            messagebox.showwarning("Advertencia", str(ve), parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Error al editar consideración: {e}", parent=self)

    def delete_consideration(self):
        selected_item_id = self.tree.focus()
        if not selected_item_id:
            messagebox.showwarning("Advertencia", "Selecciona una consideración para eliminar.", parent=self)
            return

        if messagebox.askyesno("Confirmar Eliminación", "¿Estás seguro de que quieres eliminar esta consideración?", parent=self):
            try:
                considerations_db_manager.delete_consideration(selected_item_id)
                self.load_considerations()
            except Exception as e:
                messagebox.showerror("Error", f"Error al eliminar consideración: {e}", parent=self)

if __name__ == '__main__':
    # Ejemplo de uso (para pruebas)
    root = tk.Tk()
    root.withdraw() # Ocultar la ventana principal de Tkinter
    manager = ConsiderationsManagerWindow(root)
    root.mainloop()
