"""Build the standalone Word deliverable for thesis section 4.1.

Equations are inserted as editable Office Math (OMML) by converting LaTeX
through Pandoc, then placed in an invisible two-column equation-number table.
"""

from __future__ import annotations

import copy
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Mm, Pt, RGBColor
from docx.text.paragraph import Paragraph


ROOT = Path(__file__).resolve().parents[2]
SOURCE_MD = ROOT / "docs" / "thesis" / "section-4.1.md"
FIG_DIR = ROOT / "artifacts" / "figures" / "chapter4"
OUT_REPO = ROOT / "artifacts" / "documents"
OUT_USER = Path(r"C:\Users\RZX\Desktop\论文\小论文\第二个问题\第二问")
OUTPUT_NAME = "4.1问题描述与空地协同保障机制设计.docx"

BODY_FONT_CN = "宋体"
BODY_FONT_EN = "Times New Roman"
HEADING_FONT_CN = "黑体"
MATH_FONT = "Cambria Math"


def set_east_asia(rpr, font: str) -> None:
    rfonts = rpr.rFonts
    rfonts.set(qn("w:eastAsia"), font)


def set_run_font(run, *, cn=BODY_FONT_CN, en=BODY_FONT_EN, size=Pt(12), bold=False) -> None:
    run.font.name = en
    run.font.size = size
    run.font.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0)
    set_east_asia(run._element.get_or_add_rPr(), cn)


def set_cell_margins(cell, top=45, start=45, bottom=45, end=45) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for key, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{key}"))
        if node is None:
            node = OxmlElement(f"w:{key}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders_none(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for name in ("top", "left", "bottom", "right", "insideH", "insideV"):
        node = borders.find(qn(f"w:{name}"))
        if node is None:
            node = OxmlElement(f"w:{name}")
            borders.append(node)
        node.set(qn("w:val"), "nil")


def set_repeat_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    flag = OxmlElement("w:tblHeader")
    flag.set(qn("w:val"), "true")
    tr_pr.append(flag)


def configure_document(doc: Document) -> None:
    section = doc.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(2.5)
    section.header_distance = Cm(1.5)
    section.footer_distance = Cm(1.5)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = BODY_FONT_EN
    normal.font.size = Pt(12)
    set_east_asia(normal.element.get_or_add_rPr(), BODY_FONT_CN)
    pf = normal.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.first_line_indent = Cm(0.85)
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.widow_control = True

    heading_specs = {
        "Heading 1": (16, 14, 8),
        "Heading 2": (14, 12, 6),
        "Heading 3": (12, 10, 4),
    }
    for name, (size, before, after) in heading_specs.items():
        style = styles[name]
        style.font.name = BODY_FONT_EN
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        set_east_asia(style.element.get_or_add_rPr(), HEADING_FONT_CN)
        fmt = style.paragraph_format
        fmt.alignment = WD_ALIGN_PARAGRAPH.LEFT
        fmt.first_line_indent = Cm(0)
        fmt.space_before = Pt(before)
        fmt.space_after = Pt(after)
        fmt.line_spacing = 1.0
        fmt.keep_with_next = True
        fmt.keep_together = True

    # Footer page field, centered and intentionally simple.
    footer_p = section.footer.paragraphs[0]
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    footer_p._p.append(fld)

    settings = doc.settings._element
    compat = settings.find(qn("w:compat"))
    if compat is None:
        compat = OxmlElement("w:compat")
        settings.append(compat)
    mode = OxmlElement("w:compatSetting")
    mode.set(qn("w:name"), "compatibilityMode")
    mode.set(qn("w:uri"), "http://schemas.microsoft.com/office/word")
    mode.set(qn("w:val"), "15")
    compat.append(mode)


def add_text_paragraph(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.first_line_indent = Cm(0.85)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    run = p.add_run(text)
    set_run_font(run)


def add_markdown_paragraph(doc: Document, markdown: str) -> None:
    """Convert one prose paragraph so every inline formula remains editable."""
    with tempfile.TemporaryDirectory(prefix="section41_para_") as tmp:
        tmp_dir = Path(tmp)
        md_path = tmp_dir / "paragraph.md"
        docx_path = tmp_dir / "paragraph.docx"
        md_path.write_text(markdown + "\n", encoding="utf-8")
        subprocess.run(
            ["pandoc", "--from", "markdown+tex_math_dollars", str(md_path), "-o", str(docx_path)],
            check=True,
            capture_output=True,
        )
        source = Document(docx_path)
        if not source.paragraphs:
            raise RuntimeError(f"Pandoc did not produce a paragraph for: {markdown[:80]}")
        element = copy.deepcopy(source.paragraphs[0]._p)

    body = doc._body._element
    sect_pr = body.find(qn("w:sectPr"))
    if sect_pr is None:
        body.append(element)
    else:
        body.insert(body.index(sect_pr), element)
    paragraph = doc.paragraphs[-1]
    paragraph.style = doc.styles["Normal"]
    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.first_line_indent = Cm(0.85)
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    for run in paragraph.runs:
        set_run_font(run)
    set_math_fonts(element)


def add_heading(doc: Document, text: str, level: int) -> None:
    p = doc.add_paragraph(style=f"Heading {level}")
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    size = {1: Pt(16), 2: Pt(14), 3: Pt(12)}[level]
    set_run_font(run, cn=HEADING_FONT_CN, size=size, bold=True)


def latex_to_omml(latex: str):
    with tempfile.TemporaryDirectory(prefix="section41_eq_") as tmp:
        tmp_dir = Path(tmp)
        md = tmp_dir / "eq.md"
        docx = tmp_dir / "eq.docx"
        md.write_text(f"$$\n{latex}\n$$\n", encoding="utf-8")
        subprocess.run(["pandoc", str(md), "-o", str(docx)], check=True, capture_output=True)
        eq_doc = Document(docx)
        nodes = eq_doc._element.xpath("//m:oMathPara|//m:oMath")
        if not nodes:
            raise RuntimeError(f"Pandoc did not produce OMML for: {latex}")
        node = copy.deepcopy(nodes[0])
        # Equation alignment is handled by the containing table cell.
        if node.tag == qn("m:oMathPara"):
            for pr in node.findall(qn("m:oMathParaPr")):
                node.remove(pr)
        return node


def set_math_fonts(omml) -> None:
    for rpr in omml.iter(qn("m:rPr")):
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            rpr.insert(0, rfonts)
        for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
            rfonts.set(qn(f"w:{attr}"), MATH_FONT)


def add_equation(doc: Document, latex: str, number: str) -> None:
    table = doc.add_table(rows=1, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders_none(table)
    table.columns[0].width = Cm(13.1)
    table.columns[1].width = Cm(1.8)
    table.rows[0].cells[0].width = Cm(13.1)
    table.rows[0].cells[1].width = Cm(1.8)
    for cell in table.rows[0].cells:
        set_cell_margins(cell, top=35, start=20, bottom=35, end=20)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

    left = table.cell(0, 0).paragraphs[0]
    left.alignment = WD_ALIGN_PARAGRAPH.CENTER
    left.paragraph_format.first_line_indent = Cm(0)
    left.paragraph_format.space_before = Pt(2)
    left.paragraph_format.space_after = Pt(2)
    omml = latex_to_omml(latex)
    set_math_fonts(omml)
    left._p.append(omml)

    right = table.cell(0, 1).paragraphs[0]
    right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    right.paragraph_format.first_line_indent = Cm(0)
    right.paragraph_format.space_before = Pt(2)
    right.paragraph_format.space_after = Pt(2)
    run = right.add_run(f"（{number}）")
    set_run_font(run, size=Pt(12))


def add_figure(doc: Document, image_path: Path, caption: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(5)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(image_path), width=Cm(15.5))

    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.first_line_indent = Cm(0)
    cap.paragraph_format.line_spacing = 1.0
    cap.paragraph_format.space_before = Pt(0)
    cap.paragraph_format.space_after = Pt(6)
    cap.paragraph_format.keep_with_next = False
    run = cap.add_run(caption)
    set_run_font(run, size=Pt(10.5))


def populate_from_markdown(doc: Document) -> None:
    lines = SOURCE_MD.read_text(encoding="utf-8").splitlines()
    i = 0
    skip_caption = False
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("# "):
            add_heading(doc, line[2:].strip(), 1)
            i += 1
            continue
        if line.startswith("## "):
            add_heading(doc, line[3:].strip(), 2)
            i += 1
            continue
        if line.startswith("!["):
            match = re.match(r"!\[(.+?)\]\((.+?)\)", line)
            if not match:
                raise RuntimeError(f"Invalid figure markup: {line}")
            caption, rel_path = match.groups()
            add_figure(doc, FIG_DIR / Path(rel_path).name, caption)
            skip_caption = True
            i += 1
            continue
        if skip_caption and line.startswith("**图") and line.endswith("**"):
            skip_caption = False
            i += 1
            continue
        skip_caption = False
        if line == "$$":
            equation_lines = []
            i += 1
            while i < len(lines) and lines[i].strip() != "$$":
                equation_lines.append(lines[i].strip())
                i += 1
            if i >= len(lines):
                raise RuntimeError("Unclosed display equation in section-4.1.md")
            latex = " ".join(equation_lines)
            number_match = re.search(r"\\tag\{([^}]+)\}", latex)
            if not number_match:
                raise RuntimeError(f"Equation has no tag: {latex}")
            number = number_match.group(1)
            latex = re.sub(r"\s*\\tag\{[^}]+\}\s*", "", latex).strip()
            latex = re.sub(r"\s*\.\s*$", "", latex)
            add_equation(doc, latex, number)
            i += 1
            continue
        add_markdown_paragraph(doc, line)
        i += 1


def build() -> tuple[Path, Path]:
    doc = Document()
    configure_document(doc)
    populate_from_markdown(doc)

    props = doc.core_properties
    props.title = "4.1 问题描述与空地协同保障机制设计"
    props.subject = "路网约束下多无人机与移动药液补给车空地协同施药"
    props.keywords = "SR-MAPPO; 空地异构协同; 移动药液补给; 道路约束"
    props.comments = "M1 模型规格稿；公式为可编辑 Office Math 对象。"

    OUT_REPO.mkdir(parents=True, exist_ok=True)
    OUT_USER.mkdir(parents=True, exist_ok=True)
    repo_path = OUT_REPO / OUTPUT_NAME
    user_path = OUT_USER / OUTPUT_NAME
    doc.save(repo_path)
    shutil.copy2(repo_path, user_path)
    return repo_path, user_path


if __name__ == "__main__":
    for path in build():
        print(path)
