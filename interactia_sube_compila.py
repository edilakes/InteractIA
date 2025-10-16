import subprocess
import datetime
import sys

def run_and_log(command_str):
    """Ejecuta un comando como una cadena y muestra su salida en tiempo real."""
    print(f"--- Ejecutando: {command_str} ---")
    try:
        process = subprocess.Popen(command_str, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        
        output_lines = []
        for line in process.stdout:
            print(line, end='')
            output_lines.append(line)
        
        process.wait()
        output = "".join(output_lines)

        if process.returncode != 0:
            if "nothing to commit" in output or "nada para hacer commit" in output:
                 print("--- INFO: No habia nuevos cambios para incluir en el commit. ---")
                 return True
            
            print(f"!!! ERROR: El comando finalizo con codigo de salida {process.returncode} !!!")
            return False
            
        print("--- Comando finalizado con exito ---")
        return True

    except Exception as e:
        print(f"!!! Ocurrio un error inesperado al ejecutar el comando: {e} !!!")
        return False

def main():
    """
    Script para automatizar el proceso de commit y compilacion de la aplicacion InteractIA.
    """
    print(">>> INICIANDO SCRIPT DE COMMIT Y COMPILACION AUTOMATICA <<<")

    if not run_and_log("git add ."):
        print(">>> Proceso abortado por error en 'git add'.")
        sys.exit(1)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_message = f"Build automatico: {timestamp}"
    if not run_and_log(f'git commit -m "{commit_message}"'):
        print("ADVERTENCIA: 'git commit' no se completo como se esperaba, pero se continua con la compilacion.")
    
    # --- COMANDO CORREGIDO ---
    # Se anade --paths . para que PyInstaller busque modulos en el directorio raiz.
    # Se mantienen los --hidden-import para asegurar la inclusion de modulos no explicitos.
    pyinstaller_command = (
        "pyinstaller --onefile --noconsole --name InteractIA "
        "--paths . "
        "--hidden-import=agente "
        "--hidden-import=controlador "
        "--hidden-import=vision "
        "--hidden-import=knowledge_base "
        "--hidden-import=memoria_chat_mongodb "
        "--hidden-import=logger_config "
        "--hidden-import=comunicador "
        "--hidden-import=contexto_manager "
        "--hidden-import=config "
        "--hidden-import=lock_manager "
        "main.py"
    )
    
    if not run_and_log(pyinstaller_command):
        print(">>> Proceso abortado por error en la compilacion con PyInstaller.")
        sys.exit(1)

    print(">>> SCRIPT FINALIZADO. La aplicacion ha sido compilada en la carpeta 'dist'. <<<")

if __name__ == "__main__":
    main()
