# FLOTAPP

Mini aplicación de línea de comandos que alerta sobre documentos obligatorios de vehículos próximos a vencer (Permiso de circulación, Padrón, Revisión técnica y SOAP).

Subes los documentos una sola vez como PDF. La aplicación usa el modelo **Gemini** de Google para leer cada PDF, extrae la patente, el tipo de documento y la fecha de vencimiento, los guarda localmente y te muestra un resumen de vencimientos por patente.

## Requisitos previos

- **Python 3.10 o superior** (desarrollado con Python 3.14). Verifica con `python --version`.
- **Git**.
- **Una llave de API de Gemini** (gratuita). Se obtiene en [Google AI Studio](https://aistudio.google.com/apikey) iniciando sesión con una cuenta de Google y pulsando "Create API key".
- Uno o más documentos de vehículo **en formato PDF**.

## Instalación

Los comandos están escritos para **Windows (PowerShell)**; abajo se indica la diferencia en macOS/Linux.

### 1. Descargar el repositorio

```powershell
git clone https://github.com/HidalgoCerda123/PROYECTOIA.git
cd PROYECTOIA
```

### 2. Crear y activar el entorno virtual

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

Si PowerShell rechaza el script de activación con un error de "ejecución de scripts deshabilitada", ejecuta una vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y vuelve a intentarlo.

En macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

Sabrás que quedó activo porque el prompt empieza con `(venv)`.

### 3. Instalar las dependencias

```powershell
pip install -r requirements.txt
```

### 4. Configurar la llave de API

Copia la plantilla de variables de entorno:

```powershell
copy .env.example .env
```

(en macOS/Linux: `cp .env.example .env`)

Abre el archivo `.env` y reemplaza `tu_llave_aqui` por tu llave real:

```
GEMINI_API_KEY=AIza...tu_llave_real
```

El archivo `.env` nunca se sube a GitHub (está en `.gitignore`).

## Uso

Todos los comandos se ejecutan **con el entorno virtual activado** y desde la raíz del proyecto.

### Registrar documentos

```powershell
python src/miniapp.py subir ruta\al\documento.pdf
```

Puedes pasar varios PDF a la vez:

```powershell
python src/miniapp.py subir SOAP.pdf PADRON.pdf PERMISO_CIRCULACION.pdf REVISION_TECNICA.pdf
```

Por cada archivo verás una línea como:

```
OK SOAP.pdf: TRGJ62 - SOAP - vence 2027-03-31
```

Si subes otro documento del mismo tipo y patente, reemplaza al anterior.

### Ver el resumen de vencimientos

```powershell
python src/miniapp.py resumen
```

Ejemplo de salida:

```
Patente TRGJ62
  SOAP                     2027-03-31   VIGENTE (156 dias)
  Permiso de circulacion   2027-03-31   VIGENTE (156 dias)
  Revision tecnica         2027-05-31   VIGENTE (217 dias)
  Padron                   -            SIN VENCIMIENTO
```

Estados posibles:

| Estado | Significado |
|---|---|
| `VIGENTE` | Vence en más de 30 días |
| `POR VENCER` | Vence dentro de los próximos 30 días |
| `VENCIDO` | La fecha de vencimiento ya pasó |
| `SIN VENCIMIENTO` | El documento no vence (por ejemplo, el Padrón) |

Los datos registrados se guardan en `data/flotapp.json` (se crea automáticamente la primera vez que subes un documento).

## Scripts adicionales

- **Probar la conexión con Gemini** (útil para verificar que la llave funciona):

  ```powershell
  python src/consumir_gemini.py
  ```

  Si todo está bien, imprime una respuesta corta del modelo.

- **Comparar modelos** (`src/comparar_modelos.py`): script usado para decidir qué modelo emplear. Requiere PDF de prueba en `~/Documents/DOCS_CAMIONETAS` con nombres específicos, por lo que **no es necesario para usar la aplicación**. Sus resultados ya están en `docs/resultados_comparacion.json`.

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `Falta GEMINI_API_KEY en el archivo .env` | No creaste el `.env` o no está en la raíz del proyecto. Repite el paso 4. |
| `ModuleNotFoundError` | El entorno virtual no está activo o faltó instalar dependencias. Activa `venv` y ejecuta `pip install -r requirements.txt`. |
| `No se encontro el archivo` / `El archivo no es un PDF` | Revisa la ruta; solo se aceptan archivos `.pdf`. Si la ruta tiene espacios, enciérrala entre comillas. |
| Errores 429, 500 o 503 | La API de Gemini está saturada o llegaste a su límite de uso. La aplicación reintenta 3 veces sola; si persiste, espera unos minutos. |
| La patente o fecha salen incorrectas | Verifica que el PDF sea legible y corresponda a uno de los cuatro tipos de documento soportados. |

## Estructura del proyecto

- `src/miniapp.py` : aplicación principal (comandos `subir` y `resumen`).
- `src/consumir_gemini.py` : cliente de la API de Gemini (peticiones, reintentos, manejo de errores).
- `src/comparar_modelos.py` : script de comparación de modelos de IA.
- `data/` : documentos registrados (`flotapp.json`); se genera al usar la app y no se sube al repositorio.
- `docs/` : decisión de arquitectura (`desicion-arquitectura.md`), diagramas y resultados de la comparación de modelos.
- `tests/` : pruebas (por ahora vacío).
- `requirements.txt` : dependencias de Python con versiones fijas.
- `.env.example` : plantilla de variables de entorno, sin valores reales.

## Notas de seguridad

- Ningún secreto va escrito en el código ni en archivos versionados; la llave de API vive solo en tu `.env`.
- Los PDF se envían a la API de Google Gemini para ser leídos. No subas documentos que no quieras compartir con ese servicio.
