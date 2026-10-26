import argparse
import base64
import json
import os
from datetime import date

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from consumir_gemini import ErrorTransitorio, enviar_peticion, extraer_texto, URL_BASE, API_KEY

# Constantes
MODELO_PDF = "gemini-3.5-flash-lite"
RUTA_DATOS = os.path.join(os.path.dirname(__file__), "..", "data", "flotapp.json")
DIAS_ALERTA = 30
TIMEOUT_PDF = 120  # leer un PDF tarda mas que una pregunta de texto
TIPOS_DOCUMENTO = ["Permiso de circulacion", "Padron", "Revision tecnica", "SOAP"]
INTENTOS = 3

# el formato lo garantiza la API: el tipo solo puede ser uno de TIPOS_DOCUMENTO
ESQUEMA_RESPUESTA = {
    "type": "OBJECT",
    "properties": {
        "patente": {"type": "STRING"},
        "tipo_documento": {"type": "STRING", "enum": TIPOS_DOCUMENTO},
        "fecha_vencimiento": {"type": "STRING", "nullable": True},
    },
    "required": ["patente", "tipo_documento", "fecha_vencimiento"],
}

PROMPT = (
    "Lee este documento de un vehiculo chileno y extrae sus datos. "
    "La patente va sin puntos ni guiones y SIN el digito verificador que va despues del guion "
    '(ej: "TRGJ.62-6" -> "TRGJ62"). '
    "La fecha de vencimiento va en formato YYYY-MM-DD. "
    "El Padron no suele vencer: si no hay fecha de vencimiento, usa null."
)


# Requisito 1: lectura de PDF
def leer_pdf(ruta):
    if not ruta.lower().endswith(".pdf"):
        raise ValueError(f"El archivo no es un PDF: {ruta}")
    if not os.path.isfile(ruta):
        raise ValueError(f"No se encontro el archivo: {ruta}")
    with open(ruta, "rb") as archivo:
        return base64.b64encode(archivo.read()).decode("ascii")


def armar_peticion_pdf(pdf_base64, nombre_modelo=MODELO_PDF):
    if not API_KEY:
        raise ValueError("Falta GEMINI_API_KEY en el archivo .env")
    url = f"{URL_BASE}{nombre_modelo}:generateContent?key={API_KEY}"
    body = {
        "contents": [
            {
                "parts": [
                    {"inline_data": {"mime_type": "application/pdf", "data": pdf_base64}},
                    {"text": PROMPT},
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": ESQUEMA_RESPUESTA,
        },
    }
    return url, body


# reintenta solo errores transitorios de la API (503, 429, timeout), con espera creciente
@retry(
    retry=retry_if_exception_type(ErrorTransitorio),
    stop=stop_after_attempt(INTENTOS),
    wait=wait_exponential(multiplier=2, min=2, max=20),
    reraise=True,
)
def consultar_gemini(url, body):
    return extraer_texto(enviar_peticion(url, body, timeout=TIMEOUT_PDF))


def interpretar_documento(texto):
    try:
        datos = json.loads(texto)
        patente = datos["patente"].upper().replace("-", "").replace(" ", "").replace(".", "")
        tipo = datos["tipo_documento"]
        vencimiento = datos["fecha_vencimiento"]
    except (json.JSONDecodeError, KeyError, AttributeError, TypeError):
        raise RuntimeError("No se pudo interpretar el documento: respuesta con formato inesperado.")

    if len(patente) == 7:
        # el digito verificador (ej: TRGJ.62-6) no es parte de la patente
        patente = patente[:6]
    if not patente:
        raise RuntimeError("No se encontro la patente en el documento.")
    if tipo not in TIPOS_DOCUMENTO:
        raise RuntimeError(f"Tipo de documento no reconocido: {tipo}")
    if vencimiento is not None:
        try:
            date.fromisoformat(vencimiento)
        except (ValueError, TypeError):
            raise RuntimeError(f"Fecha de vencimiento invalida: {vencimiento}")
    return patente, tipo, vencimiento


# Requisito 2: recordar documentos y fechas por patente
def cargar_datos():
    if not os.path.isfile(RUTA_DATOS):
        return {}
    try:
        with open(RUTA_DATOS, encoding="utf-8") as archivo:
            return json.load(archivo)
    except json.JSONDecodeError:
        raise RuntimeError(f"El archivo de datos esta danado: {os.path.abspath(RUTA_DATOS)}")


def guardar_datos(datos):
    os.makedirs(os.path.dirname(RUTA_DATOS), exist_ok=True)
    with open(RUTA_DATOS, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=2)


def registrar_documento(ruta_pdf):
    pdf_base64 = leer_pdf(ruta_pdf)
    url, body = armar_peticion_pdf(pdf_base64)
    texto = consultar_gemini(url, body)
    patente, tipo, vencimiento = interpretar_documento(texto)

    datos = cargar_datos()
    # un documento nuevo del mismo tipo y patente reemplaza al anterior
    datos.setdefault(patente, {})[tipo] = {
        "vencimiento": vencimiento,
        "archivo": os.path.basename(ruta_pdf),
    }
    guardar_datos(datos)
    return patente, tipo, vencimiento


# Requisito 3: resumen de vencimientos por patente
def calcular_estado(dias):
    if dias < 0:
        return "VENCIDO"
    if dias <= DIAS_ALERTA:
        return "POR VENCER"
    return "VIGENTE"


def construir_resumen(datos, hoy=None):
    hoy = hoy or date.today()
    filas = []
    for patente, documentos in datos.items():
        for tipo, info in documentos.items():
            if info["vencimiento"] is None:
                filas.append((patente, tipo, None, None, "SIN VENCIMIENTO"))
                continue
            vencimiento = date.fromisoformat(info["vencimiento"])
            dias = (vencimiento - hoy).days
            filas.append((patente, tipo, vencimiento, dias, calcular_estado(dias)))
    # por patente, luego por fecha (los sin vencimiento al final)
    return sorted(filas, key=lambda f: (f[0], f[2] or date.max))


def imprimir_resumen(datos):
    filas = construir_resumen(datos)
    if not filas:
        print("No hay documentos registrados. Usa: python miniapp.py subir <archivo.pdf>")
        return
    patente_actual = None
    for patente, tipo, vencimiento, dias, estado in filas:
        if patente != patente_actual:
            print(f"\nPatente {patente}")
            patente_actual = patente
        if vencimiento is None:
            print(f"  {tipo:<24} {'-':<12} {estado}")
        else:
            print(f"  {tipo:<24} {vencimiento.isoformat():<12} {estado} ({dias} dias)")


def main():
    parser = argparse.ArgumentParser(description="FLOTAPP: alertas de documentos de vehiculos")
    subcomandos = parser.add_subparsers(dest="comando", required=True)
    subir = subcomandos.add_parser("subir", help="Registra uno o mas documentos PDF")
    subir.add_argument("pdfs", nargs="+", help="Rutas de los PDF")
    subcomandos.add_parser("resumen", help="Muestra los vencimientos por patente")
    args = parser.parse_args()

    if args.comando == "subir":
        for ruta in args.pdfs:
            try:
                patente, tipo, vencimiento = registrar_documento(ruta)
                print(f"OK {ruta}: {patente} - {tipo} - vence {vencimiento or 'sin vencimiento'}")
            except (ValueError, RuntimeError) as error:
                print(f"No se pudo procesar {ruta}: {error}")
    else:
        imprimir_resumen(cargar_datos())


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError) as error:
        print("No se pudo completar la operacion: ", error)
