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
3. **Portable.** Se descomprime y funciona. Sin permisos de administrador,
   sin modificar el registro. Ejecutable desde un USB.
4. **Aplicación gráfica de Windows, no de consola.** Sin ventana negra de DOS.
5. **No modifica el original.** Siempre genera un archivo nuevo (`nombre_fol.pdf`).
   Si ya existe, se renombra (`nombre_fol (1).pdf`), nunca se sobrescribe.

## Equipo objetivo
- **Mínimo soportado:** Intel Core i5 de 11.ª generación, 8 GB de RAM,
  Windows 10/11 de 64 bits.

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

### 5. Tipografía
| Parámetro | Opciones | Predeterminado |
|-----------|----------|----------------|
| Fuente    | Ver lista completa abajo | Roboto |
| Tamaño    | 10 / 12 / 14 / 16 pt | 10 pt |
| Color     | Negro (fijo) | — |

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
- **PDFs con contraseña:** se muestra un campo para ingresar la clave. En lotes, los archivos
  protegidos quedan en estado "pendiente de clave"; el usuario puede ingresarlas una por una
  o saltarlos. La clave nunca se guarda en disco.
- **Páginas en blanco:** reciben folio igual que las demás (el folio corre sin interrupción).
  No se detectan ni se saltan páginas en blanco automáticamente.

### 8. Salida
- Mismo directorio que el original, con sufijo configurable (predeterminado `_fol`):
  `Contrato_fol.pdf`. El usuario puede cambiar el sufijo en la configuración.
- Si el directorio no tiene permiso de escritura: `Documentos\pdf-foliado\`.
- Si el archivo de salida ya existe, se renombra (`Contrato_fol (1).pdf`), nunca se sobrescribe.

### 9. Vista previa
- Antes de procesar, el panel muestra una miniatura de la primera página del PDF seleccionado
  en la lista, con el folio superpuesto en la posición y formato configurados.
- Se actualiza en tiempo real al cambiar posición, fuente, tamaño o prefijo.
- No requiere procesar el archivo; solo renderiza la primera página con el overlay.

### 10. Reporte al finalizar
- Al terminar el lote, se muestra un resumen en pantalla:
  - Archivos procesados correctamente (nombre, páginas, rango de folios asignado).
  - Archivos con error (nombre, motivo).
- El resumen se puede exportar como TXT simple (`reporte_foliado.txt`) con un clic.

### 11. Procesamiento
- **Paralelo:** varios PDFs se procesan a la vez (un hilo por archivo, limitado por CPUs disponibles).
- **Cancelable:** botón "Cancelar" detiene el lote. Los archivos ya terminados se conservan.
- **Tolerante a errores:** si un archivo falla, se marca en rojo, se sigue con los demás
  y al final se muestra el motivo del error.
- **Escritura atómica:** cada archivo de salida se escribe en un temporal y se renombra
  al terminar, para no dejar archivos corruptos si se interrumpe.

## Reglas técnicas
- Python 3.13.
- Interfaz: **PySide6** (Qt, LGPL).
- Empaquetado: PyInstaller `--onedir --noconsole`, sin compresión UPX.
- **PDF:** pikepdf (MIT) para leer y fusionar páginas + reportlab (BSD) para generar
  la capa de texto del folio. reportlab crea una página-overlay transparente con el folio
  exactamente posicionado y la fuente embebida; pikepdf la fusiona sobre la página original.
- Licencias: PROHIBIDO cualquier componente AGPL, GPL o de uso no comercial.
  Mantener `LICENCIAS.md` con la licencia de cada dependencia.
- Datos propios (preferencias guardadas) dentro de la carpeta portable (`pdf-foliado\datos\`),
  nunca en el registro de Windows.

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
  - Fuente: selector (Roboto / Arial / Calibri).
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
- PDFs con contraseña (en v0.1: mensaje claro "El archivo está protegido con contraseña").
- Formato de salida distinto a PDF.

## Fases y criterios de aceptación
1. **Núcleo:** estampado de folio en PDF monoarchivo, todos los parámetros, UI completa,
   modo claro/oscuro, empaquetado portable.
   Criterio: procesar 10 PDFs variados (1–200 págs.) sin internet, resultado visualmente
   correcto en el equipo de referencia.
2. **Lotes y correlativo:** procesamiento paralelo multi-archivo, modo correlativo, cancelación.
3. **Pulido:** preferencias guardadas, comparación de nomenclatura de salida en modo
   correlativo, distribución en GitHub Releases.

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
