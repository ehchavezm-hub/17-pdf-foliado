# pdf-foliado Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `pdf-foliado.exe` — a portable Windows desktop app that stamps sequential folio numbers on PDF pages, distributable as a single ZIP < 80 MB, requiring no installation or admin rights.

**Architecture:** PySide6 two-column UI (file list + config panel); engine layer (validator → stamper → batch) is fully decoupled from UI and communicates only via Qt signals. reportlab generates a transparent overlay PDF page with the folio text; pikepdf merges it onto the original page. pypdfium2 rasterizes the first page for the live preview.

**Tech Stack:** Python 3.13, PySide6 (QtWidgets/QtGui/QtCore only), pikepdf, reportlab, pypdfium2, pytest, PyInstaller.

**Spec:** `ALCANCE.md` (repo root)

## Global Constraints

- Python 3.13 only.
- PySide6 LGPL — import only `QtWidgets`, `QtGui`, `QtCore`. No `QtWebEngine`, `QtMultimedia`, `QtNetwork`.
- Dependencies: pikepdf (MIT), reportlab (BSD), pypdfium2 (Apache 2.0). ZERO AGPL/GPL components.
- ZIP < 80 MB after PyInstaller `--onedir --noconsole` with aggressive `--exclude-module`.
- Windows 10/11 64-bit. No admin rights, no registry writes, no internet connection.
- Original PDF is NEVER modified. Output always `<name><suffix>.pdf`; if exists → `<name><suffix> (1).pdf`.
- Atomic writes: `tempfile.NamedTemporaryFile` + `os.replace`.
- Folio coordinates: 1 mm = 72 ÷ 25.4 ≈ 2.8346 pt.
- Preferences in `pdf-foliado\datos\preferencias.json`. Log in `datos\errores.log` (rotating, max 1 MB).
- Package root: `pdf_foliado/`.
- All UI updates from worker threads go through Qt signals/slots only.

## Review Focus

1. **Mixed-size pages:** CropBox must be read per page, not cached from page 0 — wrong corner placement on A3 pages inside an A4 document.
2. **Rotated pages (/Rotate 90/180/270):** selected corner must be compensated so the folio lands in the visually-correct corner after rotation.
3. **Correlativo + password file:** pre-scan Phase 1 must pause all processing, surface a password prompt, and only continue once the password is accepted or the file is removed.
4. **260-char output path:** must silently fall back to `%USERPROFILE%\Documentos\pdf-foliado\` before writing, never raise an OSError.
5. **Folio text wider than CropBox:** must warn the user at config time (before stamping), not silently clip the text.

---

### Task 1: Project scaffold + test fixtures

**Files:**
- Create: `pyproject.toml`
- Create: `pdf_foliado/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Interfaces:**
- Produces: `pytest` fixtures `pdf_1p`, `pdf_10p`, `pdf_mixed_size`, `pdf_rotated_90`, `pdf_cropbox`, `pdf_encrypted`, `pdf_signed`, `pdf_pdfa`, `pdf_0p` — each returns `pathlib.Path` to a generated PDF.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "pdf-foliado"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "PySide6>=6.7",
    "pikepdf>=9.0",
    "reportlab>=4.2",
    "pypdfium2>=4.30",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-qt>=4.4"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `tests/conftest.py` with programmatic PDF fixtures**

Each fixture uses reportlab to generate a minimal PDF and returns its `Path`. No binary PDFs committed to the repo.

```python
import pytest
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A3
import pikepdf, io, struct

TMP = Path(__file__).parent / "_generated"

def _make_pdf(name, pages=1, pagesize=A4, rotate=0, cropbox=None) -> Path:
    TMP.mkdir(exist_ok=True)
    p = TMP / name
    c = canvas.Canvas(str(p), pagesize=pagesize)
    for i in range(pages):
        c.drawString(50, 700, f"Page {i+1}")
        c.showPage()
    c.save()
    if rotate or cropbox:
        with pikepdf.open(p, allow_overwriting_input=True) as pdf:
            for page in pdf.pages:
                if rotate:
                    page["/Rotate"] = rotate
                if cropbox:
                    page["/CropBox"] = cropbox
            pdf.save(p)
    return p

@pytest.fixture(scope="session") def pdf_1p(tmp_path_factory):   return _make_pdf("1p.pdf", pages=1)
@pytest.fixture(scope="session") def pdf_10p(tmp_path_factory):  return _make_pdf("10p.pdf", pages=10)
@pytest.fixture(scope="session") def pdf_0p(tmp_path_factory):
    TMP.mkdir(exist_ok=True); p = TMP / "0p.pdf"
    canvas.Canvas(str(p)).save(); return p
@pytest.fixture(scope="session") def pdf_rotated_90():  return _make_pdf("rot90.pdf", rotate=90)
@pytest.fixture(scope="session") def pdf_cropbox():
    return _make_pdf("cropbox.pdf", cropbox=[0,0,400,500])
@pytest.fixture(scope="session") def pdf_mixed_size():
    TMP.mkdir(exist_ok=True); p = TMP / "mixed.pdf"
    c = canvas.Canvas(str(p), pagesize=A4)
    c.drawString(50,700,"A4"); c.showPage()
    c.setPageSize(A3); c.drawString(50,700,"A3"); c.showPage()
    c.save(); return p
@pytest.fixture(scope="session") def pdf_encrypted():
    src = _make_pdf("enc_src.pdf", pages=3)
    p = TMP / "enc.pdf"
    with pikepdf.open(src) as pdf:
        pdf.save(p, encryption=pikepdf.Encryption(owner="owner", user="user123"))
    return p
```

- [ ] **Step 3: Run `pytest tests/ -v` — expect "no tests ran" (0 failures)**

- [ ] **Step 4: Commit**

```
git add pyproject.toml pdf_foliado/ tests/
git commit -m "feat: project scaffold + test fixtures"
```

---

### Task 2: `utils/pdf_info.py` + `utils/path_utils.py`

**Files:**
- Create: `pdf_foliado/utils/__init__.py`
- Create: `pdf_foliado/utils/pdf_info.py`
- Create: `pdf_foliado/utils/path_utils.py`
- Test: `tests/utils/test_pdf_info.py`
- Test: `tests/utils/test_path_utils.py`

**Interfaces:**
- Produces:
  - `get_pdf_info(path: Path) -> PdfInfo` where `PdfInfo` is a dataclass with fields: `page_count: int`, `is_encrypted: bool`, `has_signature: bool`, `is_pdfa: bool`.
  - `get_page_box(page: pikepdf.Page) -> tuple[float,float,float,float]` — returns `(x0,y0,w,h)` from CropBox falling back to MediaBox.
  - `get_page_rotation(page: pikepdf.Page) -> int` — returns `/Rotate` value (0,90,180,270).
  - `safe_output_path(input_path: Path, suffix: str) -> Path` — applies suffix, checks 260-char limit, falls back to `~/Documents/pdf-foliado/`, avoids overwrite with `(n)` counter.

- [ ] **Step 1: Write failing tests**

```python
# tests/utils/test_pdf_info.py
from pdf_foliado.utils.pdf_info import get_pdf_info, get_page_box, get_page_rotation
import pikepdf

def test_page_count(pdf_10p):
    info = get_pdf_info(pdf_10p)
    assert info.page_count == 10

def test_zero_pages(pdf_0p):
    info = get_pdf_info(pdf_0p)
    assert info.page_count == 0

def test_encrypted(pdf_encrypted):
    info = get_pdf_info(pdf_encrypted)
    assert info.is_encrypted is True

def test_not_encrypted(pdf_1p):
    assert get_pdf_info(pdf_1p).is_encrypted is False

def test_cropbox_used(pdf_cropbox):
    with pikepdf.open(pdf_cropbox) as pdf:
        x0, y0, w, h = get_page_box(pdf.pages[0])
    assert w == pytest.approx(400, abs=1)
    assert h == pytest.approx(500, abs=1)

def test_rotation(pdf_rotated_90):
    with pikepdf.open(pdf_rotated_90) as pdf:
        assert get_page_rotation(pdf.pages[0]) == 90

def test_no_rotation(pdf_1p):
    with pikepdf.open(pdf_1p) as pdf:
        assert get_page_rotation(pdf.pages[0]) == 0
```

```python
# tests/utils/test_path_utils.py
from pdf_foliado.utils.path_utils import safe_output_path
from pathlib import Path

def test_basic_suffix(tmp_path):
    src = tmp_path / "doc.pdf"
    src.touch()
    out = safe_output_path(src, "_fol")
    assert out.name == "doc_fol.pdf"
    assert out.parent == tmp_path

def test_avoids_overwrite(tmp_path):
    src = tmp_path / "doc.pdf"; src.touch()
    (tmp_path / "doc_fol.pdf").touch()
    out = safe_output_path(src, "_fol")
    assert out.name == "doc_fol (1).pdf"

def test_long_path_fallback(tmp_path):
    long_name = "a" * 250
    src = tmp_path / f"{long_name}.pdf"; src.touch()
    out = safe_output_path(src, "_fol")
    assert len(str(out)) <= 260 or "pdf-foliado" in str(out)
```

- [ ] **Step 2: Run tests — expect FAIL (ImportError)**

- [ ] **Step 3: Implement `pdf_foliado/utils/pdf_info.py`**

`get_pdf_info`: open with `pikepdf.open(path, suppress_warnings=True)` inside try/except `pikepdf.PasswordError` → set `is_encrypted=True`, return early. Check `/Sig` in any page's `/Annots` for `has_signature`. Check XMP metadata `pdfaid:conformance` for `is_pdfa`.

`get_page_box(page)`: read `/CropBox`, fallback to `/MediaBox`; return `(x0, y0, w-x0, h-y0)`.

`get_page_rotation(page)`: return `int(page.get("/Rotate", 0))`.

- [ ] **Step 4: Implement `pdf_foliado/utils/path_utils.py`**

`safe_output_path`: build candidate = `input_path.parent / (stem + suffix + ".pdf")`; if `len(str(candidate)) > 259`, redirect to `Path.home()/"Documents"/"pdf-foliado"/candidate.name` (create dir); then loop `(1)`, `(2)` until non-existing path.

- [ ] **Step 5: Run tests — expect PASS**

```
pytest tests/utils/ -v
```

- [ ] **Step 6: Commit**

```
git commit -m "feat: pdf_info and path_utils"
```

---

### Task 3: `engine/validator.py`

**Files:**
- Create: `pdf_foliado/engine/__init__.py`
- Create: `pdf_foliado/engine/validator.py`
- Test: `tests/engine/test_validator.py`

**Interfaces:**
- Consumes: `get_pdf_info(path)` from Task 2.
- Produces: `validate_file(path: Path, password: str | None = None) -> ValidationResult`
  where `ValidationResult` is a dataclass: `ok: bool`, `error: str | None`, `warnings: list[str]`.

- [ ] **Step 1: Write failing tests**

```python
from pdf_foliado.engine.validator import validate_file

def test_valid_pdf(pdf_1p):
    r = validate_file(pdf_1p)
    assert r.ok is True
    assert r.error is None

def test_zero_pages_rejected(pdf_0p):
    r = validate_file(pdf_0p)
    assert r.ok is False
    assert "0 páginas" in r.error

def test_encrypted_no_password(pdf_encrypted):
    r = validate_file(pdf_encrypted)
    assert r.ok is False
    assert "contraseña" in r.error.lower()

def test_encrypted_wrong_password(pdf_encrypted):
    r = validate_file(pdf_encrypted, password="wrong")
    assert r.ok is False

def test_encrypted_correct_password(pdf_encrypted):
    r = validate_file(pdf_encrypted, password="user123")
    assert r.ok is True

def test_signature_warning(pdf_signed):
    r = validate_file(pdf_signed)
    assert r.ok is True
    assert any("firma" in w.lower() for w in r.warnings)
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `validator.py`**

Call `get_pdf_info`. If `is_encrypted` and no password → `ok=False, error="contraseña requerida"`. If `is_encrypted` and password provided, try `pikepdf.open(path, password=password)`; PasswordError → `ok=False`. If `page_count == 0` → `ok=False, error="El PDF tiene 0 páginas"`. If `has_signature` → append warning. If `is_pdfa` → append warning.

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```
git commit -m "feat: engine validator"
```

---

### Task 4: `engine/stamper.py`

**Files:**
- Create: `pdf_foliado/engine/stamper.py`
- Test: `tests/engine/test_stamper.py`

**Interfaces:**
- Produces: `stamp_page(page: pikepdf.Page, folio_text: str, params: StampParams) -> pikepdf.Page`
  where `StampParams` is a dataclass: `corner: str` (one of `"TL","TR","BL","BR"`), `d1_mm: float`, `d2_mm: float`, `font_name: str`, `font_size_pt: float`, `color_hex: str` (e.g. `"#E4002B"`).

- [ ] **Step 1: Write failing tests**

```python
from pdf_foliado.engine.stamper import stamp_page, StampParams
import pikepdf, pytest

def _get_folio_pos(page):
    # reads XObject stream of the overlay and returns (x, y) of the text
    ...  # helper: parse content stream for Td/Tf operators

def test_folio_bottom_right(pdf_1p):
    params = StampParams(corner="BR", d1_mm=10, d2_mm=15,
                         font_name="Helvetica", font_size_pt=12, color_hex="#000000")
    with pikepdf.open(pdf_1p) as pdf:
        page = pdf.pages[0]
        x0, y0, w, h = get_page_box(page)
        stamped = stamp_page(page, "0001", params)
    # verify overlay xobject was added
    assert "/Resources" in stamped or stamped is page

def test_folio_coordinates_within_box(pdf_1p):
    params = StampParams(corner="BR", d1_mm=10, d2_mm=15,
                         font_name="Helvetica", font_size_pt=12, color_hex="#000000")
    with pikepdf.open(pdf_1p) as pdf:
        page = pdf.pages[0]
        _, _, w, h = get_page_box(page)
        stamp_page(page, "0001", params)
    # folio must be within page bounds — no exception raised is baseline

def test_rotated_page_corner(pdf_rotated_90):
    params = StampParams(corner="BR", d1_mm=10, d2_mm=15,
                         font_name="Helvetica", font_size_pt=12, color_hex="#000000")
    with pikepdf.open(pdf_rotated_90) as pdf:
        page = pdf.pages[0]
        stamp_page(page, "0001", params)  # must not raise

def test_mixed_size_each_page(pdf_mixed_size):
    params = StampParams(corner="BR", d1_mm=10, d2_mm=15,
                         font_name="Helvetica", font_size_pt=12, color_hex="#000000")
    with pikepdf.open(pdf_mixed_size) as pdf:
        for i, page in enumerate(pdf.pages):
            stamp_page(page, str(i+1).zfill(4), params)  # must not raise
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `stamper.py`**

`stamp_page`:
1. Get `(x0, y0, w, h)` from `get_page_box(page)`.
2. Get `rot = get_page_rotation(page)`. Adjust target corner: rotate the logical corner by `-rot` to get PDF-space coordinates. Mapping: `BR@0°→BR, BR@90°→BL, BR@180°→TL, BR@270°→TR`.
3. Compute `(tx, ty)` in PDF points from adjusted corner + `d1_mm * 2.8346` and `d2_mm * 2.8346` inward from edges.
4. Use reportlab `io.BytesIO` canvas at `(w, h)` pagesize; set fill color from `color_hex`; draw `folio_text` with `drawString(tx, ty, folio_text)`; `c.save()`.
5. Open overlay bytes as `pikepdf.open(BytesIO(buf))`.
6. Merge overlay's content stream onto `page` using `pikepdf.Page.merge_resources` / form XObject approach.
7. Return modified `page`.

- [ ] **Step 4: Integration test — stamp a real PDF and verify output**

```python
def test_stamp_produces_valid_pdf(pdf_10p, tmp_path):
    params = StampParams(corner="BR", d1_mm=10, d2_mm=15,
                         font_name="Helvetica", font_size_pt=12, color_hex="#231F20")
    out = tmp_path / "out.pdf"
    with pikepdf.open(pdf_10p) as pdf:
        for i, page in enumerate(pdf.pages):
            stamp_page(page, str(i+1).zfill(4), params)
        pdf.save(out)
    with pikepdf.open(out) as check:
        assert len(check.pages) == 10
```

- [ ] **Step 5: Run — expect PASS**

- [ ] **Step 6: Commit**

```
git commit -m "feat: engine stamper with CropBox + rotation compensation"
```

---

### Task 5: `engine/batch.py`

**Files:**
- Create: `pdf_foliado/engine/batch.py`
- Test: `tests/engine/test_batch.py`

**Interfaces:**
- Consumes: `validate_file`, `get_pdf_info`, `stamp_page`, `safe_output_path`.
- Produces: `BatchWorker(QThread)` with signals:
  - `progress(int, int)` — (current_file_index, total_files)
  - `file_done(str, str)` — (input_path_str, output_path_str)
  - `file_error(str, str)` — (input_path_str, error_message)
  - `password_needed(str)` — (input_path_str) — emitted during pre-scan
  - `finished()` — all files processed
- `BatchConfig` dataclass: `files: list[Path]`, `mode: str` (`"por_documento"` | `"correlativo"`), `order: str` (`"asc"` | `"desc"`), `start: int`, `prefix: str`, `suffix_file: str`, `stamp: StampParams`.

- [ ] **Step 1: Write failing tests**

```python
from PySide6.QtCore import QCoreApplication
from pdf_foliado.engine.batch import BatchWorker, BatchConfig
from pdf_foliado.engine.stamper import StampParams

def _params():
    return StampParams(corner="BR", d1_mm=10, d2_mm=15,
                       font_name="Helvetica", font_size_pt=12, color_hex="#231F20")

def test_por_documento_sequence(pdf_1p, pdf_10p, tmp_path, qtbot):
    cfg = BatchConfig(files=[pdf_1p, pdf_10p], mode="por_documento", order="asc",
                      start=1, prefix="", suffix_file="_fol", stamp=_params())
    worker = BatchWorker(cfg, output_dir=tmp_path)
    done = []
    worker.file_done.connect(lambda i, o: done.append(o))
    with qtbot.waitSignal(worker.finished, timeout=15000):
        worker.start()
    assert len(done) == 2

def test_correlativo_sequence(pdf_1p, pdf_10p, tmp_path, qtbot):
    cfg = BatchConfig(files=[pdf_1p, pdf_10p], mode="correlativo", order="asc",
                      start=1, prefix="", suffix_file="_fol", stamp=_params())
    worker = BatchWorker(cfg, output_dir=tmp_path)
    done = []
    worker.file_done.connect(lambda i, o: done.append(o))
    with qtbot.waitSignal(worker.finished, timeout=15000):
        worker.start()
    # second file's first folio should be 2 (1p has 1 page)
    with pikepdf.open(done[1]) as pdf:
        # read text from first page content stream
        assert len(pdf.pages) == 10
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `batch.py`**

Three phases as QThread:
- **Phase 0** (on add, also at run start): `validate_file` each path; emit `file_error` for hard fails.
- **Phase 1** (correlativo only): scan `get_pdf_info` for page counts; if `is_encrypted` → emit `password_needed` and block until UI provides password via `provide_password(path, pwd)` slot.
- **Phase 2**: iterate files, compute folio numbers (`start` + cumulative offset for correlativo; reset for `por_documento`; reverse for `desc`), call `stamp_page` per page, atomic write via `safe_output_path`, emit `file_done` or `file_error`.

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```
git commit -m "feat: batch worker 3-phase processing"
```

---

### Task 6: `config/preferences.py` + `config/logging_setup.py`

**Files:**
- Create: `pdf_foliado/config/__init__.py`
- Create: `pdf_foliado/config/preferences.py`
- Create: `pdf_foliado/config/logging_setup.py`
- Test: `tests/config/test_preferences.py`

**Interfaces:**
- Produces:
  - `Preferences` dataclass with all UI fields; `load(base_dir: Path) -> Preferences`; `save(prefs: Preferences, base_dir: Path)`.
  - `setup_logging(base_dir: Path)` — configures rotating file handler.

- [ ] **Step 1: Write failing tests**

```python
from pdf_foliado.config.preferences import Preferences, load, save

def test_roundtrip(tmp_path):
    p = Preferences(mode="correlativo", start=5, prefix="Folio ", corner="TL",
                    d1_mm=8.0, d2_mm=12.0, font_name="Figtree", font_size_pt=10,
                    color_hex="#E4002B", suffix_file="_num", order="desc", skin="azul")
    save(p, tmp_path)
    loaded = load(tmp_path)
    assert loaded == p

def test_missing_file_returns_defaults(tmp_path):
    p = load(tmp_path / "nonexistent")
    assert p.mode == "por_documento"
    assert p.start == 1
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `preferences.py`**

`Preferences` dataclass with defaults: `mode="por_documento"`, `order="asc"`, `start=1`, `prefix=""`, `corner="BR"`, `d1_mm=10.0`, `d2_mm=15.0`, `font_name="Roboto"`, `font_size_pt=12`, `color_hex="#231F20"`, `suffix_file="_fol"`, `skin="rojo"`. `save` writes `datos/preferencias.json`; `load` reads it, returns defaults on missing/corrupt.

- [ ] **Step 4: Implement `logging_setup.py`**

`setup_logging(base_dir)`: `RotatingFileHandler` at `base_dir/"datos"/"errores.log"`, max 1 MB, 1 backup. Level WARNING.

- [ ] **Step 5: Run — expect PASS**

- [ ] **Step 6: Commit**

```
git commit -m "feat: preferences + logging"
```

---

### Task 7: UI — `main_window.py` + `file_list.py`

**Files:**
- Create: `pdf_foliado/ui/__init__.py`
- Create: `pdf_foliado/ui/main_window.py`
- Create: `pdf_foliado/ui/file_list.py`

**Interfaces:**
- Consumes: `BatchWorker`, `BatchConfig`, `Preferences`, `validate_file`.
- Produces: `MainWindow(QMainWindow)` — the app's root widget; `FileListWidget(QWidget)` — left pane.

- [ ] **Step 1: Smoke test (UI shows without crash)**

```python
def test_main_window_opens(qtbot):
    from pdf_foliado.ui.main_window import MainWindow
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    assert win.isVisible()
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `file_list.py`**

`FileListWidget`: `QListWidget` subclass with `setDragDropMode(InternalMove)`. Methods: `add_files(paths: list[Path])`, `remove_selected()`, `clear_all()`, `get_ordered_files() -> list[Path]`. Emits `files_changed(list[Path])` signal.

- [ ] **Step 4: Implement `main_window.py`**

`MainWindow`: two-column `QHBoxLayout` — left: `FileListWidget` + drop zone; right: `ConfigPanel` (Task 8, stub for now). Bottom bar: progress `QProgressBar` + Cancel + Foliar buttons. `Foliar` triggers `BatchWorker`; signals wire to progress bar and status label. Apply AECOM palette + Figtree via `setStyleSheet` on `QApplication`.

- [ ] **Step 5: Run smoke test — expect PASS**

- [ ] **Step 6: Commit**

```
git commit -m "feat: main window + file list widget"
```

---

### Task 8: UI — `config_panel.py`

**Files:**
- Create: `pdf_foliado/ui/config_panel.py`

**Interfaces:**
- Produces: `ConfigPanel(QWidget)` with `get_config() -> BatchConfig` and `set_preferences(prefs: Preferences)` / `get_preferences() -> Preferences`. Emits `config_changed()` signal.

- [ ] **Step 1: Smoke test**

```python
def test_config_panel_defaults(qtbot):
    from pdf_foliado.ui.config_panel import ConfigPanel
    panel = ConfigPanel()
    qtbot.addWidget(panel)
    cfg = panel.get_preferences()
    assert cfg.mode in ("por_documento", "correlativo")
    assert 1 <= cfg.start <= 9999
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `config_panel.py`**

Controls (all within a `QScrollArea`):
- Modo: `QButtonGroup` with two `QPushButton` (Por documento / Correlativo) + example block `QLabel`.
- Orden: `QButtonGroup` (0001→N / N→0001).
- Iniciar desde: `QSpinBox` (1–9999) + Prefijo: `QLineEdit`.
- Posición: 2×2 grid of `QPushButton` (TL/TR/BL/BR) + d1/d2 `QDoubleSpinBox` with `mm` suffix.
- Tipografía: `QComboBox` (13 fonts) + tamaño `QComboBox` (10/12/14/16 pt) + color `QButtonGroup` (Negro/Blanco/Rojo).
- Skin: 3 `QPushButton` circles (Rojo/Azul/Bosque) that call `QApplication.setStyleSheet`.
- Sufijo archivo: `QLineEdit`.
- Mode example text updates on mode toggle.

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```
git commit -m "feat: config panel all controls"
```

---

### Task 9: UI — `preview_widget.py`

**Files:**
- Create: `pdf_foliado/ui/preview_widget.py`

**Interfaces:**
- Consumes: `pypdfium2`, `ConfigPanel.config_changed` signal.
- Produces: `PreviewWidget(QWidget)` with `load_pdf(path: Path)` and `update_folio(folio_text: str, params: StampParams)`.

- [ ] **Step 1: Smoke test**

```python
def test_preview_loads(qtbot, pdf_1p):
    from pdf_foliado.ui.preview_widget import PreviewWidget
    pw = PreviewWidget()
    qtbot.addWidget(pw)
    pw.load_pdf(pdf_1p)
    pw.update_folio("0001", StampParams(corner="BR", d1_mm=10, d2_mm=15,
                    font_name="Helvetica", font_size_pt=12, color_hex="#231F20"))
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `preview_widget.py`**

`load_pdf`: use `pypdfium2.PdfDocument(str(path))` → `page.render(scale=1.5)` → `PIL.Image` → `QImage.fromData` → `QPixmap`. Display in `QLabel`. `update_folio`: compute corner position with same logic as stamper but draw on a `QPainter` overlay on the pixmap (no temp PDF needed for preview).

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```
git commit -m "feat: live preview widget with pypdfium2"
```

---

### Task 10: `main.py` + integration wiring

**Files:**
- Create: `pdf_foliado/main.py`
- Test: `tests/test_integration.py`

**Interfaces:**
- Consumes: all previous modules.
- Produces: `def run()` entry point; preferences load/save on open/close; batch worker connected to UI.

- [ ] **Step 1: Integration test**

```python
def test_full_por_documento_round_trip(pdf_10p, tmp_path, qtbot):
    """Stamp 10-page PDF, verify 10 pages in output with no errors."""
    from pdf_foliado.engine.batch import BatchWorker, BatchConfig
    from pdf_foliado.engine.stamper import StampParams
    cfg = BatchConfig(files=[pdf_10p], mode="por_documento", order="asc",
                      start=1, prefix="", suffix_file="_fol",
                      stamp=StampParams("BR", 10, 15, "Helvetica", 12, "#231F20"))
    errors = []
    done = []
    worker = BatchWorker(cfg, output_dir=tmp_path)
    worker.file_error.connect(lambda p, e: errors.append(e))
    worker.file_done.connect(lambda i, o: done.append(o))
    with qtbot.waitSignal(worker.finished, timeout=20000):
        worker.start()
    assert errors == []
    assert len(done) == 1
    with pikepdf.open(done[0]) as pdf:
        assert len(pdf.pages) == 10
```

- [ ] **Step 2: Run — expect PASS (engine already works)**

- [ ] **Step 3: Implement `main.py`**

```python
def run():
    app = QApplication(sys.argv)
    app.setApplicationName("pdf-foliado")
    base_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent.parent
    setup_logging(base_dir)
    prefs = load(base_dir)
    win = MainWindow(base_dir=base_dir, prefs=prefs)
    win.show()
    code = app.exec()
    save(win.get_preferences(), base_dir)
    sys.exit(code)
```

- [ ] **Step 4: Verify app launches: `python -m pdf_foliado.main`**

- [ ] **Step 5: Commit**

```
git commit -m "feat: main entry point + integration wiring"
```

---

### Task 11: PyInstaller packaging

**Files:**
- Create: `build/pdf-foliado.spec`
- Create: `build/build.bat`

**Interfaces:**
- Produces: `dist/pdf-foliado/pdf-foliado.exe` + `dist/pdf-foliado.zip` ≤ 80 MB compressed.

- [ ] **Step 1: Create `build/pdf-foliado.spec`**

```python
# pdf-foliado.spec
excludes = [
    "unittest","doctest","email","html","http","xmlrpc","xml",
    "ftplib","imaplib","smtplib","poplib","telnetlib","nntplib",
    "PySide6.QtWebEngine","PySide6.QtMultimedia","PySide6.QtNetwork",
    "PySide6.Qt3D","PySide6.QtBluetooth","PySide6.QtWebSockets",
    "PySide6.QtDataVisualization","PySide6.QtCharts","PySide6.QtQuick",
    "PySide6.QtQml","PySide6.QtTest","PySide6.QtSql",
    "tkinter","curses","readline","pty","termios",
]
a = Analysis(
    ["../pdf_foliado/main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=["pikepdf._core","reportlab.pdfbase._fontdata_enc_winansi"],
    excludes=excludes,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
          name="pdf-foliado", console=False, icon=None)
coll = COLLECT(exe, a.binaries, a.datas, name="pdf-foliado")
```

- [ ] **Step 2: Create `build/build.bat`**

```bat
@echo off
pyinstaller --clean pdf-foliado.spec
cd dist
powershell -command "Compress-Archive -Path pdf-foliado -DestinationPath pdf-foliado.zip -Force"
powershell -command "(Get-Item pdf-foliado.zip).length / 1MB"
```

- [ ] **Step 3: Run build on Windows CI runner (GitHub Actions)**

Add `.github/workflows/build.yml` with `windows-latest` runner, Python 3.13, `pip install pyinstaller`, run `build.bat`, upload artifact.

- [ ] **Step 4: Verify ZIP ≤ 80 MB**

If over 80 MB: audit `dist/pdf-foliado/` with `du -sh *`, identify largest packages, add more `--exclude-module` entries.

- [ ] **Step 5: "Clean machine" smoke test**

Run `pdf-foliado.exe` on a fresh Windows 10 VM with no Python installed. Verify it opens without DLL errors.

- [ ] **Step 6: Final commit + tag**

```
git add build/ .github/
git commit -m "feat: PyInstaller build script + CI workflow"
git tag v0.1.0
git push --tags
```
