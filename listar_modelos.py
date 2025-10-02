import google.generativeai as genai
import os
from dotenv import load_dotenv

# Cargar credenciales de forma segura
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

if not gemini_api_key:
    print("ERROR: No se encontró la GEMINI_API_KEY en el archivo .env")
else:
    try:
        genai.configure(api_key=gemini_api_key)
        
        print("Buscando modelos compatibles con 'generateContent'...")
        
        found_model = False
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
                found_model = True
        
        if not found_model:
            print("No se encontraron modelos compatibles.")
            
    except Exception as e:
        print(f"Ocurrió un error: {e}")
