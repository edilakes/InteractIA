import subprocess

def buscar_tesseract():
    """
    Busca el ejecutable de Tesseract en las rutas de instalación más comunes.
    Devuelve la ruta completa si lo encuentra, de lo contrario None.
    """
    print("Buscando Tesseract OCR...")
    comandos = [
        'dir "C:\Program Files\Tesseract-OCR\tesseract.exe" /s /b',
        'dir "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" /s /b'
    ]

    for cmd in comandos:
        try:
            print(f"Ejecutando: {cmd}")
            resultado = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, text=True).strip()
            if resultado and resultado.endswith("tesseract.exe"):
                print(f"(+) Tesseract encontrado en: {resultado}")
                return resultado
        except subprocess.CalledProcessError:
            # El comando falla si no encuentra el archivo, lo cual es esperado.
            continue
        except Exception as e:
            print(f"(-) Ocurrió un error inesperado al ejecutar el comando: {e}")
            continue
            
    print("(-) Tesseract no se encontró en las rutas de instalación comunes.")
    return None

if __name__ == '__main__':
    ruta_tesseract = buscar_tesseract()
    if ruta_tesseract:
        print(f"\nLa ruta del ejecutable de Tesseract es: {ruta_tesseract}")
    else:
        print("\nNo se pudo encontrar Tesseract. Por favor, asegúrate de que esté instalado.")
