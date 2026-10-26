import json
import os
import statistics
import time

from consumir_gemini import enviar_peticion, extraer_texto
from miniapp import armar_peticion_pdf, interpretar_documento, leer_pdf

# Constantes
CARPETA_PDF = os.path.join(os.path.expanduser("~"), "Documents", "DOCS_CAMIONETAS")
RUTA_RESULTADOS = os.path.join(os.path.dirname(__file__), "..", "docs", "resultados_comparacion.json")
REPETICIONES = 2
TIMEOUT = 120

# precio en USD por token (entrada, salida) segun ai.google.dev/gemini-api/docs/pricing
MODELOS = {
    "gemini-3.5-flash-lite": (0.30e-6, 2.50e-6),
    "gemini-3.8-flash": (0.75e-6, 3.75e-6),
    "gemini-3.6-flash": (1.50e-6, 7.50e-6),
    "gemini-3.1-pro-preview": (2.00e-6, 12.00e-6),
}

# respuesta correcta de cada documento: (patente, tipo, vencimiento)
ESPERADO = {
    "SOAP.pdf": ("TRGJ62", "SOAP", "2027-03-31"),
    "PADRON.pdf": ("TRGJ62", "Padron", None),
    "PERMISO_CIRCULACION.pdf": ("TRGJ62", "Permiso de circulacion", "2027-03-31"),
    "REVISION_TECNICA.pdf": ("TRGJ62", "Revision tecnica", "2027-05-31"),
}


def calcular_costo(datos, precio_entrada, precio_salida):
    uso = datos["usageMetadata"]
    salida = uso.get("candidatesTokenCount", 0) + uso.get("thoughtsTokenCount", 0)
    return uso["promptTokenCount"] * precio_entrada + salida * precio_salida


def probar(modelo, nombre_pdf, pdf_base64):
    precio_entrada, precio_salida = MODELOS[modelo]
    url, body = armar_peticion_pdf(pdf_base64, modelo)
    inicio = time.perf_counter()
    try:
        datos = enviar_peticion(url, body, timeout=TIMEOUT)
        latencia = time.perf_counter() - inicio
        obtenido = interpretar_documento(extraer_texto(datos))
        costo = calcular_costo(datos, precio_entrada, precio_salida)
    except (ValueError, RuntimeError) as error:
        return {"modelo": modelo, "pdf": nombre_pdf, "ok": False, "acierto": False,
                "latencia": time.perf_counter() - inicio, "costo": 0, "error": str(error)}
    return {"modelo": modelo, "pdf": nombre_pdf, "ok": True,
            "acierto": obtenido == ESPERADO[nombre_pdf], "obtenido": list(obtenido),
            "latencia": latencia, "costo": costo}


def resumir(resultados):
    print(f"\n{'modelo':<26}{'respuestas':>11}{'aciertos':>10}{'lat. media':>12}{'lat. max':>10}{'costo/PDF':>12}")
    for modelo in MODELOS:
        filas = [r for r in resultados if r["modelo"] == modelo]
        con_respuesta = [r for r in filas if r["ok"]]
        if not con_respuesta:
            print(f"{modelo:<26}{'0/' + str(len(filas)):>11}")
            continue
        latencias = [r["latencia"] for r in con_respuesta]
        print(f"{modelo:<26}{len(con_respuesta):>5}/{len(filas):<5}"
              f"{sum(r['acierto'] for r in filas):>6}/{len(filas):<3}"
              f"{statistics.mean(latencias):>10.1f} s{max(latencias):>8.1f} s"
              f"{statistics.mean(r['costo'] for r in con_respuesta):>11.5f} $")


if __name__ == "__main__":
    try:
        pdfs = {nombre: leer_pdf(os.path.join(CARPETA_PDF, nombre)) for nombre in ESPERADO}
    except ValueError as error:
        raise SystemExit(f"No se pudo leer los PDF de prueba: {error}")
    resultados = []
    for modelo in MODELOS:
        for repeticion in range(REPETICIONES):
            for nombre, pdf_base64 in pdfs.items():
                r = probar(modelo, nombre, pdf_base64)
                resultados.append(r)
                estado = "OK" if r["acierto"] else ("MAL" if r["ok"] else "ERROR")
                print(f"{modelo} {nombre} #{repeticion + 1}: {estado} {r['latencia']:.1f}s "
                      f"{r.get('error', '')}", flush=True)
    with open(RUTA_RESULTADOS, "w", encoding="utf-8") as archivo:
        json.dump(resultados, archivo, ensure_ascii=False, indent=2)
    resumir(resultados)
