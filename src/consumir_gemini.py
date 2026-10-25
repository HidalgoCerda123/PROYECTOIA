import os
import requests
from dotenv import load_dotenv

load_dotenv()

#Constantes 
MODELO = "gemini-3.6-flash"
URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models/"
API_KEY = os.getenv("GEMINI_API_KEY")

#funcion para crear la solicitud 
def armar_peticion(pregunta): #pregunta= "Confirma la conexion"
    if not pregunta:
        raise ValueError("La pregunta no puede estar vacía.")
    url = f"{URL_BASE}{MODELO}:generateContent?key={API_KEY}"
    body = {
    "contents": [
        {
            "parts": [
                {"text": pregunta}
            ]
        }
    ]
    }
    return url, body
#arma_peticion_openai -> url, body

#funcion envia la peticion 
def enviar_peticion(url, body):
    try:
        respuesta= requests.post(url, json=body, timeout=30)
    except requests.exceptions.ConnectionError:
        raise RuntimeError("No se pudo conectar con el servicio. Intenta de nuevo en unos momentos.")
    except requests.exceptions.Timeout:
        raise RuntimeError("Se agoto el tiempo. Intenta de nuevo en unos momentos.")

    if respuesta.status_code != 200:
        raise RuntimeError(f"Error en la solicitud. Status Code: {respuesta.status_code}")
    
    try:
        return respuesta.json()
    except requests.exceptions.JSONDecodeError:
        raise RuntimeError("La respuesta del servicio no llego en el formato esperado.") 

#funcion procesa y extrae dato 
def extraer_texto(datos):
    try: 
      return datos["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError("La respuesta no recibe el texto generado en el lugar definido.")
    
def obtener_dato_prueba(pregunta):
    url, body = armar_peticion(pregunta)
    datos = enviar_peticion(url, body)
    costo = calcular_costo(datos, 0.00000075, 0.00000375)
    print(f"Costo de la solicitud: ${costo:.6f} USD")
    return extraer_texto(datos)

def calcular_costo(datos, precio_entrada, precio_salida):
    uso = datos["usageMetadata"]
    tokens_entrada = uso["promptTokenCount"]
    tokens_salida = uso["candidatesTokenCount"]
    tokens_razonamiento = uso["thoughtsTokenCount"]
    costo = (tokens_entrada * precio_entrada) + ((tokens_salida + tokens_razonamiento) * precio_salida)
    return costo


try:
  print(obtener_dato_prueba("Confirma en una frase corta que esta conexion funciona correctamente"))
except (ValueError, RuntimeError) as error:
  print("No se pudo completar la petición: ", error)

