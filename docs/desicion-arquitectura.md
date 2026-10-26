# Decisión de arquitectura: elección de modelo
  
  Fecha de comparación: Lunes 26/10/2026

  Nombre miniaplicación: "FLOTAPP"

## Modelo elegido
  
  Elegí el modelo: **gemini-3.5-flash-lite** (Google Gemini, vía API REST).

  Mi mini aplicación sirve para: Alertar sobre documentos obligatorios de vehiculos proximos a vencer. Por ejemplo: Permiso de circulacion, Padron, Revision tecnica y SOAP. Solo subiendole los documentos una vez como PDF.

  Los requisitos que necesito cumplir son: 

    1-. Lectura de PDF.
    2-. Recordar fechas y documentos subidos asociados a 1 patente.
    3-. Presentar un resumen de fechas de vencimiento por patente, junto con el nombre del documento asociado a esa fecha.

  El modelo cubre el requisito 1: recibe el PDF completo (también escaneos y fotos de documentos) y devuelve patente, tipo de documento y fecha de vencimiento como JSON con un esquema fijo (`responseSchema`). Los requisitos 2 y 3 los resuelve el código propio (`data/flotapp.json` y el comando `resumen`).

## Diagrama de arquitectura
 
 [Diagrama de Arquitectura de FLOTAPP](diagrama_arquitectura_miniapp.png) · [versión editable (SVG)](diagrama_arquitectura_miniapp.svg)

 El diagrama de la prueba de conexión inicial sigue disponible en [diagrama_arquitectura.png](diagrama_arquitectura.png).

## Comparación de candidatos
  
  Estas son las preguntas y condiciones con las que se midieron los modelos: 

  Preguntas y/o condiciones:

    1-. Calidad: ¿lee bien la patente, el tipo de documento y la fecha de vencimiento? Se midió contra la respuesta correcta de cada PDF (patente sin dígito verificador, tipo dentro de los 4 permitidos y fecha exacta).
    2-. Latencia: ¿cuántos segundos tarda en leer un PDF?
    3-. Costo: ¿cuánto cuesta leer un PDF? (tokens de entrada + salida + razonamiento, a precio oficial).
    4-. Disponibilidad: ¿responde cuando se le llama?

  Prueba: 4 PDF reales de una misma camioneta (SOAP, Padrón, Permiso de circulación y Revisión técnica, de 0,15 a 3,4 MB), cada uno 2 veces por modelo (8 llamadas por modelo). Script: [src/comparar_modelos.py](../src/comparar_modelos.py). Detalle por llamada: [resultados_comparacion.json](resultados_comparacion.json).

  | Modelo | Respuestas | Aciertos | Latencia media | Latencia máx. | Costo por PDF | Precio USD / 1M tokens (entrada / salida) |
  |---|---|---|---|---|---|---|
  | gemini-3.5-flash-lite | 8/8 | 8/8 | 18,2 s | 24,1 s | US$ 0,00030 | 0,30 / 2,50 |
  | gemini-3.6-flash | 8/8 | 8/8 | 15,6 s | 54,7 s | US$ 0,00436 | 1,50 / 7,50 |
  | gemini-3.8-flash | 0/8 | no medible | - | - | - | 0,75 / 3,75 (precio de lanzamiento) |
  | gemini-3.1-pro-preview | 0/8 | no medible | - | - | - | 2,00 / 12,00 |

  - gemini-3.8-flash respondió error 503 (servicio sobrecargado) en las 8 llamadas, y también en un reintento posterior con una pregunta de texto corta.
  - gemini-3.1-pro-preview respondió error 429 (límite de uso de mi clave) en las 8 llamadas.
  - Los precios vienen de la [página de precios de Gemini](https://ai.google.dev/gemini-api/docs/pricing); el de 3.1 Pro proviene de una guía anterior y puede estar desactualizado.
  - Quedaron fuera `gemini-3.5-flash` (Google lo redirige a 3.6 Flash, no es un modelo distinto) y `gemini-3.1-flash-lite` (503 al probarlo).

## Justificación

Elegimos el modelo gemini-3.5-flash-lite por que para nuestra aplicacion lo que importa es leer bien unos pocos documentos que se suben una sola vez, y este modelo lo hizo igual de bien que el siguiente más caro, a una fracción del costo.

Lo que observe en las pruebas fue que gemini-3.5-flash-lite y gemini-3.6-flash acertaron los 8 de 8 casos: patente TRGJ62 sin el dígito verificador, tipo de documento correcto y fechas correctas, incluso con PDFs escaneados o fotografiados (SOAP, Padrón y Revisión técnica) y con el padrón sin fecha de vencimiento (devuelto como `null`). La diferencia estuvo en el costo: gemini-3.6-flash costó unas 14 veces más por PDF (US$ 0,00436 contra US$ 0,00030, es decir US$ 4,36 contra US$ 0,30 por cada 1.000 documentos). En latencia, gemini-3.6-flash fue más rápido en la mayoría de los casos (mediana cercana a 8 s contra 18 s), pero tuvo una respuesta de 54,7 s; flash-lite fue más estable, entre 14 y 24 s.

El criterio mas relevante para mi desicion fue el costo con calidad equivalente, porque ambos modelos acertaron todo y la latencia importa poco: un documento se sube una vez y la lectura tarda segundos. Si el volumen de la flota crece, el costo es la variable que escala.

Una limitacion que encontre en mi eleccion fue que la prueba es chica: 4 documentos de un solo vehículo, 2 repeticiones por modelo, así que no demuestra que acierte con documentos de otras municipalidades o con peor calidad de imagen. Además, 2 de los 4 candidatos no se pudieron medir por errores de la API (503 y 429), por lo que la comparación efectiva es entre 2 modelos y no entre 4. Otros puntos a tener en cuenta: la revisión técnica solo dice "VÁLIDO HASTA MAY 2027" y asumí el último día del mes (2027-05-31), y la API devolvió errores 503 con frecuencia, por eso FLOTAPP reintenta hasta 3 veces ante 503, 429 y timeouts.

## Alternativa descartada y por qué

**gemini-3.6-flash.** Acertó 8 de 8 igual que el elegido y fue más rápido en la mayoría de los casos, pero cuesta unas 14 veces más por documento (US$ 0,00436 contra US$ 0,00030) sin una mejora de calidad medible en esta prueba. Además tuvo una respuesta de 54,7 s. Lo descarto por costo; si en el futuro aparecen documentos donde flash-lite falle, es el primer modelo al que volvería a subir.

**gemini-3.8-flash y gemini-3.1-pro-preview** no pude evaluarlos: respondieron 503 y 429 durante la prueba, por lo que no entran en la comparación. Conviene repetir el script `src/comparar_modelos.py` cuando estén disponibles.
