# PROMPT DE ALCANCE — 17-pdf-foliado

> Aplicativo independiente. No forma parte de eh-ocr ni depende de él.
> Estado: **borrador para revisión** — pendiente de aprobación para iniciar el desarrollo.

## Rol
Actúa como arquitecto y desarrollador senior de utilidades de documentos PDF.
Vas a construir **pdf-foliado**, una app de escritorio para Windows dedicada a estampar
números de folio visibles en las páginas de uno o más PDFs, según parámetros configurables
por el usuario. Debe ser simple, precisa y portable.

## Identidad
- Nombre: **pdf-foliado**
- Repositorio: https://github.com/ehchavezm-hub/17-pdf-foliado (**privado**; todo el código,
  documentación, tests y releases van aquí)
- Licencia: ninguna pública (repositorio privado, todos los derechos reservados)
- Ejecutable: `pdf-foliado.exe`
- Paquete Python: `pdf_foliado`
- Versión inicial: 0.1.0
- Distribución: `pdf-foliado.zip` — se descomprime y funciona. Sin instalación.
- Actualizaciones: manuales, descargando el ZIP nuevo desde GitHub Releases

## Objetivo
Recibir uno o más archivos PDF y generar, por cada uno, un nuevo PDF con un número de folio
estampado en cada página, en la posición y formato que el usuario elija. El archivo original
nunca se modifica.

## Principios no negociables
1. **100 % gratuito.** Solo librerías con licencia MIT, BSD, Apache 2.0 o LGPL (esta última
   solo con enlace dinámico). Sin servicios de pago, nube ni claves de API.
2. **Absolutamente autónomo.** Funciona 100 % sin internet. Todo viene incluido.
3. **Portable y totalmente autónomo.** Se descomprime y funciona. Sin instalación,
   sin permisos de administrador, sin modificar el registro, sin intervención de TI.
   Ejecutable desde un USB o carpeta de red. Todo lo necesario viene dentro del ZIP:
   runtime de Python, librerías, fuentes. Cero dependencias externas.
4. **Funciona en cualquier Windows de 64 bits.** Compatible con Windows 10 y 11,
   en cualquier marca y modelo de equipo (Intel, AMD, ARM64 con capa de emulación).
   No requiere VC++ Redistributable, .NET, ni ningún componente previo.
   El primer doble clic funciona, sin mensajes de "falta una DLL".
5. **Aplicación gráfica de Windows, no de consola.** Sin ventana negra de DOS.
5. **No modifica el original.** Siempre genera un archivo nuevo (`nombre_fol.pdf`).
   Si ya existe, se renombra (`nombre_fol (1).pdf`), nunca se sobrescribe.
6. **El mejor foliador del mundo.** Maneja correctamente todos los casos reales:
   páginas mixtas, rotadas, CropBox arbitrario, PDFs protegidos, correlativo exacto,
   firmas digitales, PDF/A, rutas UNC. Ningún otro foliador gratuito debe superarlo
   en precisión, control tipográfico ni robustez ante casos extremos.
7. **Equilibrio entre potencia y ligereza.** La meta es un ZIP descargable **< 80 MB**.
   Cada dependencia se justifica por su aporte real; nada entra por comodidad si añade
   peso sin valor medible. PySide6 se incluye con los módulos mínimos; PyInstaller
   excluye agresivamente módulos Python no usados. Funcionalidad sin concesiones,
   huella mínima.

## Equipo objetivo
- **Mínimo soportado:** cualquier CPU de 64 bits (Intel, AMD o ARM64 con emulación x64),
  4 GB de RAM, Windows 10/11 de 64 bits. Sin requisito de tarjeta gráfica ni NPU.
- **Entornos corporativos:** funciona en laptops administradas unidas a dominio,
  sin necesidad de solicitar permisos a TI, sin pasar por lista blanca de instaladores.
- **Sin dependencias del sistema:** el ZIP incluye todo. No se requiere instalar
  VC++ Redistributable, .NET Framework, Python, ni ningún runtime adicional.

## Funcionalidad principal

### 1. Modos de foliado

**a) Por documento (predeterminado)**
Cada PDF recibe su propia secuencia, independiente de los demás.

```
Contrato.pdf   (12 págs.)  →  folios 0001 … 0012
Anexo.pdf      ( 8 págs.)  →  folios 0001 … 0008
Planos.pdf     ( 4 págs.)  →  folios 0001 … 0004
```

**b) Correlativo entre documentos**
Los PDFs se tratan como un solo expediente. La numeración no se corta entre archivos;
el orden lo define el usuario arrastrando los elementos en la lista.

```
Contrato.pdf   (12 págs.)  →  folios 0001 … 0012
Anexo.pdf      ( 8 págs.)  →  folios 0013 … 0020
Planos.pdf     ( 4 págs.)  →  folios 0021 … 0024
```

Uso típico: expedientes legales o administrativos donde todas las hojas deben tener
folio único de principio a fin.

### 2. Orden de numeración
- **Ascendente:** primera página = 0001, última = N.
- **Descendente:** primera página = N, última = 0001.

### 3. Formato del folio
El folio tiene la forma: `[prefijo][número]`
- **Prefijo:** texto libre que el usuario escribe (puede quedar vacío).
  Ejemplos: `Folio `, `F-`, `Pág. ` o vacío para solo el número.
- **Número:** siempre con ceros a la izquierda, ajustado al total de dígitos necesario.
  - 1–9 págs. → 1 dígito  
  - 10–99 págs. → 2 dígitos  
  - 100–999 págs. → 3 dígitos  
  - 1 000–9 999 págs. → 4 dígitos (mínimo 4 dígitos siempre)

### 4. Posición en la página
Cuatro esquinas seleccionables mediante botones en la UI:

```
 [1 ↖]  [2 ↗]
 [3 ↙]  [4 ↘]
```

Márgenes configurables por el usuario:
- **d1** (distancia vertical al borde superior o inferior): predeterminado 10 mm, mín. 3 mm, máx. 30 mm.
- **d2** (distancia horizontal al borde izquierdo o derecho): predeterminado 15 mm, mín. 3 mm, máx. 30 mm.

Valores sugeridos basados en buenas prácticas administrativas:
- Expedientes legales: d1 = 10 mm, d2 = 15 mm (esquina superior derecha).
- Documentos A4 estándar: d1 = 8 mm, d2 = 10 mm.

**Referencia de coordenadas:** siempre se usa el **CropBox** de cada página (zona visible
para el usuario). Si la página no tiene CropBox, se usa el MediaBox. Las coordenadas
se calculan página a página: si el PDF mezcla tamaños (A4 + A3, retrato + paisaje),
los márgenes en mm se recalculan para cada página según sus dimensiones reales.
Conversión exacta: 1 mm = 72 ÷ 25,4 pt ≈ 2,8346 pt.

**Páginas rotadas** (campo `/Rotate` en el PDF): las coordenadas se aplican sobre la
página ya desrotada (lo que el usuario ve). Si una página tiene `/Rotate: 90`, la esquina
"inferior derecha visual" es la esquina "inferior izquierda del PDF crudo", y el motor
debe compensarlo. El folio siempre aparece en la esquina que el usuario seleccionó,
independientemente de la rotación interna del archivo.

### 5. Tipografía
| Parámetro | Opciones | Predeterminado |
|-----------|----------|----------------|
| Fuente    | Ver lista completa abajo | Roboto |
| Tamaño    | 10 / 12 / 14 / 16 pt | 10 pt |
| Color     | Negro / Blanco / Rojo | Negro |

El usuario elige el color del folio. Blanco y Rojo cubren los casos donde el negro
no sería visible (páginas con fondo oscuro, planos de ingeniería).

**Fuentes disponibles** (todas de licencia OFL/Apache 2.0, incluidas en el paquete):

| Grupo | Fuentes |
|---|---|
| Sin serif geométricas | Figtree, Urbanist, Jost, Manrope, Montserrat |
| Sin serif humanistas | Plus Jakarta Sans, IBM Plex Sans, Epilogue |
| Sin serif experimentales | Syne, Tenor Sans |
| Serif Windows (sistema) | Arial, Calibri — verificar redistribución; si no está permitida, sustituir por Liberation Sans (SIL OFL) |

Las fuentes OFL/Apache se incluyen directamente en el paquete. Arial y Calibri solo se
incluyen si la licencia de Microsoft lo permite para distribución portable; en caso contrario
se reemplazan por Liberation Sans sin pérdida de funcionalidad.

### 6. Número de inicio
- Campo configurable "Iniciar desde": por defecto 1.
- Permite continuar una secuencia previa. Ejemplo: expediente ya tiene 48 folios → el nuevo
  lote empieza en 49. Aplica tanto en modo por documento como en modo correlativo.

### 7. Entrada de archivos
- Arrastrar y soltar uno o más PDFs, o botón "Agregar archivos".
- Se muestra la lista con nombre, número de páginas y estado (pendiente / procesando / listo / error).
- **En modo correlativo la lista es reordenable por arrastre** (drag & drop dentro de la lista),
  ya que el orden define qué rango de folios recibe cada archivo.
- Se pueden quitar archivos de la lista antes de procesar.
- **No se aceptan imágenes directamente** (solo PDF). Si el usuario arrastra una imagen,
  mensaje claro: "Solo se aceptan archivos PDF."
- **PDF de 0 páginas:** rechazado inmediatamente al agregar. Mensaje: "El archivo no
  contiene páginas."
- **PDFs con contraseña de apertura:** se muestra un campo para ingresar la clave. En lotes,
  los archivos protegidos quedan en estado "pendiente de clave"; el usuario puede ingresarlas
  una por una o saltarlos. La clave nunca se guarda en disco.
- **PDFs con permisos de modificación restringidos** (sin contraseña visible, solo flags
  internos): pikepdf los procesa igual. Se muestra un aviso: "Este archivo tenía restricciones
  de edición que fueron eliminadas en la copia foliada." El original no se toca.
- **PDFs con firma digital:** se detecta la presencia de firmas (`/Sig` en el PDF).
  Aviso al agregar el archivo: "Este archivo tiene firma digital. La copia foliada tendrá
  la firma invalidada." El usuario decide si continúa. El original nunca se modifica.
- **PDFs con estándar PDF/A** (archivos de impresoras corporativas y escaneos): se detecta
  el metadato `pdfaid:conformance`. Aviso: "Este archivo es PDF/A. El foliado puede
  invalidar el estándar de archivo." El usuario decide si continúa.
- **Archivo bloqueado por otro proceso** (ej. abierto en Adobe Reader): se captura el
  `PermissionError` de Windows al intentar leer. Mensaje claro: "El archivo está en uso
  por otro programa. Ciérralo e intente de nuevo."
- **Rutas de red (UNC):** se soportan rutas `\\servidor\carpeta\archivo.pdf`. La lógica
  de directorio de salida las trata igual que rutas locales; los errores de red se reportan
  como errores del archivo correspondiente, sin detener el lote.
- **Páginas en blanco:** reciben folio igual que las demás (el folio corre sin interrupción).
  No se detectan ni se saltan páginas en blanco automáticamente.

### 8. Salida
- Mismo directorio que el original, con sufijo configurable (predeterminado `_fol`):
  `Contrato_fol.pdf`. El usuario puede cambiar el sufijo en la configuración.
- Si el directorio no tiene permiso de escritura: `Documentos\pdf-foliado\`.
- Si el archivo de salida ya existe, se renombra (`Contrato_fol (1).pdf`), nunca se sobrescribe.
- **Límite de ruta en Windows (260 caracteres):** antes de escribir se verifica que la ruta
  completa del archivo de salida no supere 260 caracteres. Si la supera, se redirige
  automáticamente a `Documentos\pdf-foliado\` y se anota en el reporte.
- **Orden de fusión:** el overlay del folio se aplica **siempre en la capa superior**
  del contenido existente de la página. En páginas con imágenes a sangre o fondo oscuro,
  el folio queda visible sobre todo el contenido.

### 9. Vista previa
- Antes de procesar, el panel muestra la primera página real del PDF seleccionado
  (rasterizada con **pypdfium2**), con el folio superpuesto en la posición y formato
  configurados.
- Se actualiza en tiempo real al cambiar posición, fuente, tamaño, prefijo o color.
- El overlay del preview se dibuja en Qt (no requiere procesar el archivo ni generar
  un PDF temporal): pypdfium2 rasteriza la página, PySide6 dibuja el texto del folio
  encima en las coordenadas calculadas.

### 10. Reporte al finalizar
- Al terminar el lote, se muestra un resumen en pantalla:
  - Archivos procesados correctamente (nombre, páginas, rango de folios asignado).
  - Archivos con error (nombre, motivo).
- El resumen se puede exportar como TXT simple (`reporte_foliado.txt`) con un clic.

### 11. Procesamiento

**Fase 0 — Validación (siempre antes de estampar):**
Al agregar archivos a la lista, cada PDF se abre y se valida:
número de páginas, contraseña, firma digital, PDF/A, permisos. Los avisos se
muestran antes de que el usuario pulse "Foliar".

**Fase 1 — Pre-scan (solo en modo correlativo):**
Antes de estampar el primer folio, se leen los recuentos de páginas de todos los
archivos para calcular el rango de cada uno y el ancho de padding del número.
Los archivos con contraseña pendiente bloquean el pre-scan; la UI los marca en
amarillo y pide las claves faltantes antes de continuar.

**Fase 2 — Estampado:**
- **Paralelo:** `min(CPUs_disponibles, 4)` archivos en simultáneo.
- **Thread safety:** procesamiento en hilos secundarios (`QThread` /
  `concurrent.futures`). Toda actualización de UI exclusivamente via `signals/slots`.
  Nunca se toca un widget desde un hilo secundario.
- **Folio sobre bounds:** antes de estampar cada página se verifica que el texto del
  folio cabe dentro del CropBox. Si no cabe (página muy pequeña o prefijo muy largo),
  el archivo se marca con advertencia y el folio se recorta al borde de la página.
- **Cancelable:** botón "Cancelar" detiene el lote. Los archivos ya terminados se conservan.
- **Tolerante a errores:** si un archivo falla (incluido `PermissionError` por archivo
  bloqueado), se marca en rojo, se sigue con los demás, el error queda en el log.
- **Escritura atómica:** cada salida se escribe en un temporal y se renombra al terminar.

## Reglas técnicas
- Python 3.13.
- Interfaz: **PySide6** (Qt, LGPL) — solo los módulos estrictamente necesarios
  (`QtWidgets`, `QtGui`, `QtCore`). Se excluyen `QtWebEngine`, `QtMultimedia`,
  `QtNetwork`, `Qt3D` y todos los módulos no usados para minimizar tamaño.
- Empaquetado: PyInstaller `--onedir --noconsole`, sin compresión UPX.
  Se usa `--exclude-module` agresivamente para eliminar módulos Python no usados
  (unittest, doctest, email, html, http, xml, etc.). Meta: ZIP < 80 MB.
  El paquete final debe pasar la prueba **"primera ejecución en máquina limpia"**:
  Windows 10/11 recién instalado, sin VC++ ni .NET adicionales, doble clic → funciona.
  Se incluyen todas las DLLs de VC++ runtime necesarias dentro de la carpeta del exe.
  Se verifica en CI con un runner Windows limpio antes de publicar cada release.
- **PDF:**
  - **pikepdf** (MIT): lectura, fusión de páginas, detección de firmas/PDF-A/permisos.
  - **reportlab** (BSD): genera el overlay transparente con el folio exactamente
    posicionado y la fuente embebida como subconjunto (solo los glifos usados).
    El overlay va **siempre en la capa superior** de la página original.
  - **pypdfium2** (Apache 2.0): rasteriza la primera página para la vista previa
    en tiempo real. No se usa para el estampado definitivo.
- Licencias: PROHIBIDO cualquier componente AGPL, GPL o de uso no comercial.
  Mantener `LICENCIAS.md` con la licencia de cada dependencia y cada fuente.
- Datos propios dentro de la carpeta portable (`pdf-foliado\datos\`), nunca en el registro.
  - `preferencias.json`: últimos valores usados de todos los parámetros (modo, orden,
    iniciar desde, prefijo, posición, d1, d2, fuente, tamaño, color, sufijo). Se cargan
    al iniciar y se guardan automáticamente al cerrar.
  - `errores.log`: log rotativo (máx. 1 MB) con timestamp, nombre de archivo y traza del
    error. No guarda contenido de los documentos. Sirve para diagnóstico en campo.

## Arquitectura de módulos

```
pdf_foliado/
├── main.py                  # punto de entrada, arranca QApplication
├── ui/
│   ├── main_window.py       # ventana principal, layout dos columnas
│   ├── file_list.py         # widget de lista reordenable con drag & drop
│   ├── config_panel.py      # panel derecho con todos los parámetros
│   └── preview_widget.py    # miniatura pypdfium2 + overlay Qt del folio
├── engine/
│   ├── stamper.py           # lógica principal: coordenadas, overlay, merge
│   ├── validator.py         # validaciones: 0 págs, firma, PDF/A, permisos, bounds
│   └── batch.py             # orquestador: pre-scan correlativo, cola de hilos
├── config/
│   ├── preferences.py       # carga/guarda preferencias.json
│   └── logging_setup.py     # configura errores.log rotativo
└── utils/
    ├── pdf_info.py          # extrae metadatos: páginas, CropBox, Rotate, firma
    └── path_utils.py        # manejo de rutas UNC, límite 260 chars, fallback
```

**Interfaz entre módulos:** `engine/stamper.py` expone una única función
`stamp_page(page, folio_text, params) → page` sin dependencia de la UI.
`engine/batch.py` emite `signals` Qt (progreso, error, listo) consumidas por la UI.

## Estrategia de tests (pytest)

- **Fixtures programáticas:** los PDFs de prueba se generan con reportlab al inicio
  de la suite (`conftest.py`). No se commitean binarios PDF al repositorio.
- **Casos obligatorios:**
  - PDF de 1 página, 10 páginas, 200 páginas
  - PDF con páginas de tamaño mixto (A4 + A3)
  - PDF con páginas rotadas (90°, 180°, 270°)
  - PDF con CropBox distinto al MediaBox
  - PDF protegido con contraseña
  - PDF con firma digital simulada
  - PDF con estándar PDF/A-1b
  - PDF de 0 páginas (debe rechazarse)
  - Ruta de salida que supera 260 caracteres
  - Folio que excede los límites de la página
- **Tests unitarios:** `engine/stamper.py` y `engine/validator.py` se testean
  sin UI ni disco (mocks de pikepdf).
- **Tests de integración:** generan PDF real, lo estampan, abren el resultado
  con pikepdf y verifican que el folio está en las coordenadas correctas (±1 pt).

## Interfaz (PySide6)
- **Pantalla única.** No hay navegación entre vistas.
- Zona de arrastre (drag & drop) con lista de archivos reordenable debajo.
- Panel de configuración a la derecha:
  - Modo: Por documento / Correlativo (radio buttons).
  - Orden: Ascendente / Descendente (radio buttons).
  - Iniciar desde: campo numérico (predeterminado 1).
  - Prefijo: campo de texto.
  - Posición: 4 botones de esquina con icono.
  - Márgenes: d1 y d2 (spinbox en mm, predeterminados 10 y 15).
  - Fuente: selector con las 13 fuentes disponibles (ver §5).
  - Tamaño: selector (10 / 12 / 14 / 16).
  - Sufijo de salida: campo de texto (predeterminado `_fol`).
- Vista previa en tiempo real de la primera página con el folio superpuesto.
- Botón "Foliar" grande, barra de progreso global y por archivo.
- Botón "Cancelar" mientras procesa.
- Resumen al finalizar con botón "Exportar reporte TXT".
- Modo claro/oscuro según Windows; compatible con pantallas de alta resolución.
- Castellano, textos claros y sin jerga técnica.

## Fuera de alcance
- OCR, conversión de imágenes a PDF, edición de contenido.
- Marcas de agua, sellos distintos al folio (logos, firmas).
- Formato de salida distinto a PDF.

## Fases y criterios de aceptación
1. **Núcleo:** estampado de folio en PDF monoarchivo, todos los parámetros, UI completa,
   modo claro/oscuro, empaquetado portable.
   Criterio: procesar 10 PDFs variados (1–200 págs.) sin internet; el folio aparece a
   ±1 mm de la posición configurada en todos los archivos de prueba; no hay crashes en
   el equipo de referencia.
2. **Lotes y correlativo:** procesamiento paralelo (tope 4 hilos), modo correlativo,
   cancelación, PDFs con contraseña, PDFs con rotación y tamaño mixto.
   Criterio: lote de 20 PDFs procesado sin interrupción; modo correlativo produce
   secuencia continua sin saltos; cancelar no deja archivos corruptos.
3. **Pulido:** preferencias guardadas y restauradas al reiniciar, log de errores,
   distribución en GitHub Releases.
   Criterio: instalar desde ZIP en un equipo distinto al de desarrollo y procesar
   10 PDFs sin ninguna configuración previa.

Cada fase incluye tests con pytest. CI en GitHub Actions (runner Windows):
tests + verificación de licencias + construcción del paquete (solo al publicar versiones).

## Tamaño estimado del paquete
| Componente | Descomprimido aprox. |
|---|---|
| Python 3.13 + librerías base | ~40 MB |
| PySide6 (módulos necesarios) | ~100 MB |
| pikepdf + dependencias | ~20 MB |
| reportlab + fuentes | ~15 MB |
| **Total descomprimido** | **~175 MB** |
| **ZIP a descargar** | **~120 MB** |

## Antes de escribir código
- Verificar versiones actuales, licencias y compatibilidad con Python 3.13 y Windows de:
  pikepdf, reportlab, PySide6.
- Confirmar redistribución de fuentes Arial y Calibri; si no está permitida, usar
  Liberation Sans (SIL Open Font License).
- Proponer la arquitectura de módulos y esperar aprobación.
