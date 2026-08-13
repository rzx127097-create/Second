from __future__ import annotations

import importlib.util
import re
import zipfile
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
FIG_SCRIPT = ROOT / "scripts" / "figures" / "generate_section_4_2_figures.py"
FIG_STEM = ROOT / "artifacts" / "figures" / "chapter4" / "fig4-3_heterogeneous_decision_model"
SOURCE_MD = ROOT / "docs" / "thesis" / "section-4.2.md"
DOC_SCRIPT = ROOT / "scripts" / "documents" / "build_section_4_2_docx.py"
DOCX_PATH = ROOT / "artifacts" / "documents" / "4.2空地异构协同施药决策模型.docx"


def test_equation_tags_are_continuous() -> None:
    tags = [int(value) for value in re.findall(r"\\tag\{4\.(\d+)\}", SOURCE_MD.read_text(encoding="utf-8"))]
    assert tags == list(range(9, 32))


def test_figure_generator_and_exports_exist() -> None:
    assert FIG_SCRIPT.is_file()
    for suffix in (".svg", ".pdf", ".png", ".tiff"):
        path = FIG_STEM.with_suffix(suffix)
        assert path.is_file() and path.stat().st_size > 1_000


def test_raster_exports_are_large_and_600_dpi() -> None:
    for suffix in (".png", ".tiff"):
        with Image.open(FIG_STEM.with_suffix(suffix)) as image:
            assert image.width >= 4_000
            assert image.height >= 2_000
            dpi = image.info.get("dpi")
            assert dpi is not None
            assert abs(float(dpi[0]) - 600.0) < 1.0
            assert abs(float(dpi[1]) - 600.0) < 1.0


def test_figure_generator_is_importable() -> None:
    spec = importlib.util.spec_from_file_location("section42_figure", FIG_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(module.build_figure)


def test_word_builder_and_output_exist() -> None:
    assert DOC_SCRIPT.is_file()
    assert DOCX_PATH.is_file() and DOCX_PATH.stat().st_size > 50_000


def test_docx_contains_editable_math_and_figure() -> None:
    with zipfile.ZipFile(DOCX_PATH) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
        media = [name for name in archive.namelist() if name.startswith("word/media/")]
    assert xml.count("<m:oMathPara") == 23
    assert xml.count("<m:oMath") >= 80
    assert len(media) == 1
    for number in range(9, 32):
        assert f"（4.{number}）" in xml


def test_docx_has_no_visible_latex_delimiters() -> None:
    with zipfile.ZipFile(DOCX_PATH) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    assert "\\tag{" not in xml
    assert "$$" not in xml
