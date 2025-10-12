import subprocess
import datetime
import sys

def run_and_log(command_str):
    """Ejecuta un comando como una cadena y muestra su salida en tiempo real."""
    print(f"--- Ejecutando: {command_str} ---")
    try:
        # Popen para un control más directo y streaming de salida
        process = subprocess.Popen(command_str, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        
        output_lines = []
        for line in process.stdout:
            print(line, end='')
            output_lines.append(line)
        
        process.wait() # Esperar a que el proceso termine
        output = "".join(output_lines)

        if process.returncode != 0:
            # Caso especial para git commit: si no hay cambios, el código de salida es 1.
            # No lo tratamos como un error fatal.
            if "nothing to commit" in output or "nada para hacer commit" in output:
                 print("\n--- INFO: No había nuevos cambios para incluir en el commit. ---")
                 return True
            
            print(f"\n!!! ERROR: El comando finalizó con código de salida {process.returncode} !!!")
            return False
            
        print(f"\n--- Comando finalizado con éxito ---\n")
        return True

    except Exception as e:
        print(f"!!! Ocurrió un error inesperado al ejecutar el comando: {e} !!!")
        return False

def main():
    """
    Script para automatizar el proceso de commit y compilación de la aplicación InteractIA.
    """
    print(">>> INICIANDO SCRIPT DE COMMIT Y COMPILACIÓN AUTOMÁTICA <<<\\n")

    # 1. Añadir todos los archivos al área de preparación (stage)
    if not run_and_log("git add ."):
        print("\\n>>> Proceso abortado por error en 'git add'.")
        sys.exit(1)

    # 2. Realizar el commit
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_message = f"Build automático: {timestamp}"
    if not run_and_log(f'git commit -m "{commit_message}"'):
        print("\\nADVERTENCIA: 'git commit' no se completó como se esperaba, pero se continúa con la compilación.")
    
    # 3. Compilar la aplicación con PyInstaller
    pyinstaller_command = "pyinstaller --onefile --noconsole --name InteractIA main.py"
    if not run_and_log(pyinstaller_command):
        print("\\n>>> Proceso abortado por error en la compilación con PyInstaller.")
        sys.exit(1)

    print("\\n>>> SCRIPT FINALIZADO. La aplicación ha sido compilada en la carpeta 'dist'. <<<\\n")

if __name__ == "__main__":
    main()
