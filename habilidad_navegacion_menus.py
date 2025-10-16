import logging
from controlador import Controlador
from vision import Vision
from PIL import Image

# Configuración inicial de logging
logger = logging.getLogger(__name__)

def encontrar_letra_subrayada(imagen: Image.Image, texto_buscar: str):
    """
    Analiza una imagen para encontrar una cadena de texto y determinar qué letra está subrayada.

    Args:
        imagen (Image.Image): La imagen (captura de pantalla) para analizar.
        texto_buscar (str): El texto del menú que se está buscando (ej. "Archivo").

    Returns:
        str: El carácter subrayado, o None si no se encuentra.
    """
    vision = Vision()
    # Extraer todos los bloques de texto de la imagen
    datos_texto = vision.leer_texto_en_pantalla(imagen)

    # Encontrar el bloque de texto que nos interesa
    bloque_objetivo = None
    for bloque in datos_texto:
        if texto_buscar.lower() in bloque['texto'].lower():
            bloque_objetivo = bloque
            break

    if not bloque_objetivo:
        logger.warning(f"No se encontró el texto '{texto_buscar}' en la pantalla.")
        return None

    # Recortar la imagen a la región del bloque de texto para un análisis más preciso
    region_texto = (
        bloque_objetivo['left'],
        bloque_objetivo['top'],
        bloque_objetivo['left'] + bloque_objetivo['width'],
        bloque_objetivo['top'] + bloque_objetivo['height']
    )
    imagen_recortada = imagen.crop(region_texto)
    
    # Convertir a escala de grises para simplificar el análisis de píxeles
    imagen_gris = imagen_recortada.convert('L')
    
    # Umbral para considerar un píxel como "oscuro" (parte de una línea)
    umbral = 100
    
    # El subrayado suele estar en la parte inferior de la caja de texto
    # Analizaremos los 2-3 píxeles inferiores de la imagen recortada
    y_inicio_analisis = max(0, imagen_gris.height - 5)
    
    pixeles_oscuros_por_columna = [0] * imagen_gris.width
    
    for y in range(y_inicio_analisis, imagen_gris.height):
        for x in range(imagen_gris.width):
            if imagen_gris.getpixel((x, y)) < umbral:
                pixeles_oscuros_por_columna[x] += 1

    # Buscar una secuencia de píxeles oscuros que formen una línea
    # Esto indica la posición horizontal del subrayado
    posicion_x_subrayado = -1
    for x, conteo in enumerate(pixeles_oscuros_por_columna):
        if conteo > 1: # Si hay más de 1 pixel oscuro en la columna, es probable que sea una línea
            posicion_x_subrayado = x
            break
            
    if posicion_x_subrayado == -1:
        logger.warning(f"No se detectó una línea de subrayado para '{texto_buscar}'.")
        return None

    # Ahora, necesitamos mapear esa posición 'x' a un carácter en el texto
    # Esta es una aproximación: asumimos que los caracteres tienen un ancho más o menos uniforme
    ancho_promedio_caracter = bloque_objetivo['width'] / len(bloque_objetivo['texto'])
    indice_caracter = int(posicion_x_subrayado / ancho_promedio_caracter)

    if 0 <= indice_caracter < len(bloque_objetivo['texto']):
        letra_subrayada = bloque_objetivo['texto'][indice_caracter]
        logger.info(f"Letra subrayada detectada para '{texto_buscar}': '{letra_subrayada}'")
        return letra_subrayada.lower()

    return None


def navegar_menu_con_alt(texto_menu: str):
    """
    Activa la barra de menús con 'Alt', busca una opción de menú y la selecciona
    detectando la letra subrayada.

    Args:
        texto_menu (str): El nombre del menú a seleccionar (ej. "Archivo", "Editar").

    Returns:
        bool: True si la operación fue exitosa, False en caso contrario.
    """
    controlador = Controlador()
    vision = Vision()
    
    logger.info(f"Iniciando navegación de menú para: '{texto_menu}'")

    # 1. Presionar 'Alt' para activar la barra de menús
    controlador.presionar_tecla('alt')
    controlador.esperar(0.5) # Esperar a que la animación del menú se complete

    # 2. Capturar la pantalla para analizarla
    captura = vision.capturar_entorno()
    
    # 3. Encontrar la letra subrayada para el texto del menú
    letra_a_pulsar = encontrar_letra_subrayada(captura, texto_menu)

    # 4. Pulsar la tecla correspondiente
    if letra_a_pulsar:
        logger.info(f"Pulsando la tecla '{letra_a_pulsar}' para abrir el menú '{texto_menu}'.")
        controlador.presionar_tecla(letra_a_pulsar)
        # Soltar 'Alt' después de la acción para no dejarlo presionado
        controlador.soltar_tecla('alt')
        return True
    else:
        logger.error(f"No se pudo determinar la tecla de atajo para '{texto_menu}'.")
        # Soltar 'Alt' para devolver el control
        controlador.soltar_tecla('alt')
        return False

if __name__ == '__main__':
    # Para pruebas, necesitamos configurar el logger y un entorno de prueba
    from logger_config import setup_logging
    setup_logging(log_level=logging.INFO)

    # --- PRUEBA ---
    # 1. Abrir una aplicación con barra de menús (ej. Notepad)
    # (Este paso se debe hacer manualmente o con un script de prueba)
    # 2. Darle foco a la ventana
    
    controlador_test = Controlador()
    controlador_test.enfocar_ventana("Bloc de notas") # Asegúrate de que el título es correcto
    controlador_test.esperar(1)

    # 3. Ejecutar la habilidad
    logger.info("Probando la navegación para el menú 'Archivo'...")
    navegar_menu_con_alt("Archivo")

    controlador_test.esperar(2)

    logger.info("Probando la navegación para el menú 'Edición'...")
    navegar_menu_con_alt("Edición")
    
    controlador_test.esperar(2)
    
    # Prueba con un submenú (requiere que el menú principal ya esté abierto)
    # Para esto, la lógica debería ser más compleja (navegar_menu_con_alt anidados)
    # Por ahora, cerramos el menú abierto con 'esc'
    controlador_test.presionar_tecla('esc')

