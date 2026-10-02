"""Editorial DOCX and Book Publication Exporter for Juvion.

Produces industry-standard formatted books and manuscripts matching professional
editorial standards and the author's custom reference template (copiamodelnovo.docx):

Front Matter (Páginas Pré-Textuais):
1. Página 1: Falsa Folha de Rosto (Half-title: Título em destaque, Subtítulo / Série / Volume)
2. Página 2: Página em branco (Verso da falsa folha de rosto)
3. Página 3: Contra Capa / Folha de Rosto (Title page: Título, Subtítulo, Autor)
4. Página 4: Página de Créditos e ISBN (Autor, Design da capa, Editora, Edição, Ano, ISBN, © Direitos)
5. Página 5: Prévia de dados bibliográficos em quadro delimitado
6. Página 6: Dedicatória / Epígrafe (Alinhada à direita, itálico, no terço inferior)
7. Página 7: Sumário (Table of Contents formatado com os capítulos)

Miolo da Obra (Body Matter):
- Seção desvinculada para miolo
- Título do livro centralizado em caixa alta no cabeçalho (opcional)
- Numeração de página nativa no rodapé (opcional)
- Capítulos iniciam em nova página com título em destaque
- Cenas NÃO possuem título da cena, apenas conteúdo com indicador de separação elegante
- Recuo na primeira linha garantido em todos os parágrafos do texto (1,25 cm)
- Formatos de livro: 16x23 cm, 14x21 cm, 19x26 cm (modelo do autor), A4
"""

import os
import re
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


# ---------------------------------------------------------------------------
# BOOK SIZES & MARGIN DEFINITIONS
# ---------------------------------------------------------------------------
BOOK_SIZES: Dict[str, Dict[str, Any]] = {
    "16x23": {
        "label": "16 × 23 cm (Padrão Romance / Tradicional)",
        "width": Cm(16.0),
        "height": Cm(23.0),
        "top_margin": Cm(2.0),
        "bottom_margin": Cm(2.0),
        "left_margin": Cm(2.3),
        "right_margin": Cm(1.8),
    },
    "14x21": {
        "label": "14 × 21 cm (Pocket / Livro de Bolso)",
        "width": Cm(14.0),
        "height": Cm(21.0),
        "top_margin": Cm(1.8),
        "bottom_margin": Cm(1.8),
        "left_margin": Cm(2.0),
        "right_margin": Cm(1.6),
    },
    "19x26": {
        "label": "19 × 26 cm (Formato Grande / Crônicas do Trovão Carmesim)",
        "width": Cm(19.58),
        "height": Cm(26.60),
        "top_margin": Cm(2.3),
        "bottom_margin": Cm(2.3),
        "left_margin": Cm(2.0),
        "right_margin": Cm(2.1),
    },
    "A4": {
        "label": "A4 - 21 × 29.7 cm (Manuscrito ABNT)",
        "width": Cm(21.0),
        "height": Cm(29.7),
        "top_margin": Cm(2.5),
        "bottom_margin": Cm(2.5),
        "left_margin": Cm(2.5),
        "right_margin": Cm(2.5),
    },
}


def _apply_section_geometry(section, book_size_key: str = "16x23"):
    """Applies width, height, and margins based on selected book size."""
    cfg = BOOK_SIZES.get(book_size_key, BOOK_SIZES["16x23"])
    section.page_width = cfg["width"]
    section.page_height = cfg["height"]
    section.top_margin = cfg["top_margin"]
    section.bottom_margin = cfg["bottom_margin"]
    section.left_margin = cfg["left_margin"]
    section.right_margin = cfg["right_margin"]


def _add_page_number_to_footer(paragraph, font_name: str = "Georgia", font_size: float = 9.0):
    """Adds a native Word PAGE field code to a paragraph."""
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fldSimple = OxmlElement("w:fldSimple")
    fldSimple.set(qn("w:instr"), "PAGE")

    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")

    rFont = OxmlElement("w:rFonts")
    rFont.set(qn("w:ascii"), font_name)
    rFont.set(qn("w:hAnsi"), font_name)
    rPr.append(rFont)

    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), str(int(font_size * 2)))
    rPr.append(sz)

    color = OxmlElement("w:color")
    color.set(qn("w:val"), "555555")
    rPr.append(color)

    r.append(rPr)
    fldSimple.append(r)
    paragraph._p.append(fldSimple)


def _set_cell_border(cell, color: str = "888888", sz: str = "6"):
    """Applies a subtle rectangular border to a Word table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        b = OxmlElement(f"w:{edge}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), sz)
        b.set(qn("w:space"), "0")
        b.set(qn("w:color"), color)
        tcBorders.append(b)
    tcPr.append(tcBorders)


# ---------------------------------------------------------------------------
# MAIN EXPORT ENTRYPOINT
# ---------------------------------------------------------------------------
def export_project_to_docx(
    output_path: str,
    title: str,
    author: str,
    project_structure: dict,
    model=None,
    font_name: str = "Georgia",
    font_size: int = 12,
    line_spacing: float = 1.25,
    book_size: str = "16x23",
    include_page_number: bool = True,
    include_header_title: bool = True,
    include_front_matter: bool = True,
    scene_separator: str = "——— / ———",
    first_line_indent_cm: float = 1.25,
    cover_image_path: Optional[str] = None,
    genre: str = "",
    synopsis: str = "",
    subtitle: str = "",
    series: str = "",
    volume: str = "",
    cover_designer: str = "",
    publisher: str = "",
    edition: str = "",
    publication_year: str = "",
    isbn_print: str = "",
    isbn_digital: str = "",
    copyright_text: str = "",
    dedication: str = "",
) -> str:
    """Generate a clean, professional, publication-ready DOCX book file."""
    doc = Document()

    # Section 1: Front Matter (or the whole document if front matter is disabled)
    sec_front = doc.sections[0]
    _apply_section_geometry(sec_front, book_size)
    sec_front.different_first_page_header_footer = True

    # Clear headers/footers in Section 1 so front matter remains clean
    for p in sec_front.header.paragraphs:
        p.text = ""
    for p in sec_front.footer.paragraphs:
        p.text = ""

    # Set default Normal style font
    style_normal = doc.styles["Normal"]
    style_normal.font.name = font_name
    style_normal.font.size = Pt(font_size)
    style_normal.font.color.rgb = RGBColor(0x11, 0x11, 0x11)

    # Resolve metadata fallbacks from model if not passed
    if model and hasattr(model, "settings"):
        work = model.settings.get("work", {})
        pub = model.settings.get("publication", {})
        if not subtitle:
            subtitle = pub.get("subtitle", "")
        if not series:
            series = work.get("series", "")
        if not volume:
            volume = work.get("volume", "")
        if not cover_designer:
            cover_designer = pub.get("cover_designer", "")
        if not publisher:
            publisher = pub.get("publisher", "Publicação Independente")
        if not edition:
            edition = pub.get("edition", "1ª edição")
        if not publication_year:
            publication_year = pub.get("publication_year", "2026")
        if not isbn_print:
            isbn_print = pub.get("isbn_print", "")
        if not isbn_digital:
            isbn_digital = pub.get("isbn_digital", "")
        if not copyright_text:
            copyright_text = pub.get("copyright", "Todos os direitos reservados.")
        if not dedication:
            dedication = pub.get("dedication", "")
        if not synopsis:
            synopsis = work.get("synopsis", "")
        if not genre:
            genre = work.get("categories", "")

    # =========================================================================
    # FRONT MATTER (PÁGINAS PRÉ-TEXTUAIS)
    # =========================================================================
    if include_front_matter:
        # ---------------------------------------------------------------------
        # PÁGINA 1: FALSA FOLHA DE ROSTO (Half Title)
        # ---------------------------------------------------------------------
        for _ in range(6):
            doc.add_paragraph()

        p_p1 = doc.add_paragraph()
        p_p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_p1.paragraph_format.space_before = Pt(20)
        p_p1.paragraph_format.space_after = Pt(12)
        r_p1 = p_p1.add_run(title.upper())
        r_p1.bold = True
        r_p1.font.name = font_name
        r_p1.font.size = Pt(font_size + 8)

        if series or subtitle:
            p_sub = doc.add_paragraph()
            p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_sub.paragraph_format.space_after = Pt(6)
            sub_text = series or subtitle
            if volume:
                sub_text += f" — Vol. {volume}"
            r_sub = p_sub.add_run(sub_text)
            r_sub.font.name = font_name
            r_sub.font.size = Pt(font_size + 1)
            r_sub.italic = True

        doc.add_page_break()

        # ---------------------------------------------------------------------
        # PÁGINA 2: PÁGINA EM BRANCO (Verso da falsa folha de rosto)
        # ---------------------------------------------------------------------
        p_blank = doc.add_paragraph()
        p_blank.paragraph_format.space_before = Pt(100)
        doc.add_page_break()

        # ---------------------------------------------------------------------
        # PÁGINA 3: CONTRA CAPA / FOLHA DE ROSTO (Full Title Page)
        # ---------------------------------------------------------------------
        for _ in range(5):
            doc.add_paragraph()

        p_t3 = doc.add_paragraph()
        p_t3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_t3.paragraph_format.space_before = Pt(20)
        p_t3.paragraph_format.space_after = Pt(12)
        r_t3 = p_t3.add_run(title.upper())
        r_t3.bold = True
        r_t3.font.name = font_name
        r_t3.font.size = Pt(font_size + 8)

        if subtitle:
            p_s3 = doc.add_paragraph()
            p_s3.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_s3.paragraph_format.space_after = Pt(6)
            r_s3 = p_s3.add_run(subtitle)
            r_s3.font.name = font_name
            r_s3.font.size = Pt(font_size + 2)
            r_s3.italic = True

        if series:
            p_ser = doc.add_paragraph()
            p_ser.alignment = WD_ALIGN_PARAGRAPH.CENTER
            ser_txt = series + (f" • Vol. {volume}" if volume else "")
            r_ser = p_ser.add_run(ser_txt)
            r_ser.font.name = font_name
            r_ser.font.size = Pt(font_size)

        for _ in range(4):
            doc.add_paragraph()

        p_a3 = doc.add_paragraph()
        p_a3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_a3.paragraph_format.space_after = Pt(24)
        r_a3 = p_a3.add_run(author)
        r_a3.bold = True
        r_a3.font.name = font_name
        r_a3.font.size = Pt(font_size + 2)

        doc.add_page_break()

        # ---------------------------------------------------------------------
        # PÁGINA 4: PÁGINA COM O ISBN E CRÉDITOS
        # ---------------------------------------------------------------------
        for _ in range(12):
            doc.add_paragraph()

        p_cr = doc.add_paragraph()
        p_cr.paragraph_format.line_spacing = 1.15
        p_cr.paragraph_format.space_after = Pt(4)
        p_cr.paragraph_format.first_line_indent = Pt(0)

        r_cr = p_cr.add_run(f"Autor: {author}\n")
        r_cr.font.name = font_name
        r_cr.font.size = Pt(font_size - 2)

        if cover_designer:
            r_cd = p_cr.add_run(f"Design da capa: {cover_designer}\n")
            r_cd.font.name = font_name
            r_cd.font.size = Pt(font_size - 2)
        else:
            r_cd = p_cr.add_run(f"Design da capa: {author}\n")
            r_cd.font.name = font_name
            r_cd.font.size = Pt(font_size - 2)

        if publisher:
            r_pub = p_cr.add_run(f"Editora / Selo: {publisher}\n")
            r_pub.font.name = font_name
            r_pub.font.size = Pt(font_size - 2)

        edition_year = f"{edition} — {publication_year}" if edition else publication_year
        if edition_year:
            r_ed = p_cr.add_run(f"Edição: {edition_year}\n")
            r_ed.font.name = font_name
            r_ed.font.size = Pt(font_size - 2)

        active_isbns = []
        if isbn_print:
            active_isbns.append(f"ISBN Impresso: {isbn_print}")
        if isbn_digital:
            active_isbns.append(f"ISBN Digital: {isbn_digital}")
        if active_isbns:
            r_isbn = p_cr.add_run("\n".join(active_isbns) + "\n")
            r_isbn.font.name = font_name
            r_isbn.font.size = Pt(font_size - 2)
        else:
            r_isbn = p_cr.add_run("ISBN:\n")
            r_isbn.font.name = font_name
            r_isbn.font.size = Pt(font_size - 2)

        p_copy = doc.add_paragraph()
        p_copy.paragraph_format.first_line_indent = Pt(0)
        p_copy.paragraph_format.space_before = Pt(8)
        r_cp = p_copy.add_run(f"© {publication_year} {author}. {copyright_text}")
        r_cp.font.name = font_name
        r_cp.font.size = Pt(font_size - 2)

        doc.add_page_break()

        # ---------------------------------------------------------------------
        # PÁGINA 5: FICHA CATALOGRÁFICA (CIP)
        # ---------------------------------------------------------------------
        for _ in range(8):
            doc.add_paragraph()

        # Build CIP Box Table (1x1 table with clean border)
        cip_table = doc.add_table(rows=1, cols=1)
        cip_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        cip_cell = cip_table.cell(0, 0)
        cip_cell.width = Cm(13.2)
        _set_cell_border(cip_cell, color="888888", sz="6")

        # Author surname formatting for CIP
        author_parts = author.strip().split()
        if len(author_parts) > 1:
            cip_surname = f"{author_parts[-1].upper()}, {' '.join(author_parts[:-1])}"
        else:
            cip_surname = author.upper()

        p_cip_h = cip_cell.paragraphs[0]
        p_cip_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cip_h.paragraph_format.space_after = Pt(4)
        p_cip_h.paragraph_format.line_spacing = 1.0
        r_ch = p_cip_h.add_run("Prévia de dados bibliográficos — Juvion")
        r_ch.font.name = font_name
        r_ch.font.size = Pt(8.0)
        r_ch.bold = True

        p_cip_b = cip_cell.add_paragraph()
        p_cip_b.paragraph_format.first_line_indent = Pt(0)
        p_cip_b.paragraph_format.line_spacing = 1.15
        p_cip_b.paragraph_format.space_after = Pt(4)

        full_work_title = f"{title}: {subtitle}" if subtitle else title
        cip_lines = [
            f"{cip_surname}.",
            f"   {full_work_title} / {author}. — {edition or '1. ed.'} — {publisher or 'Publicação Independente'}, {publication_year or '2026'}.",
            f"   ISBN {isbn_print or isbn_digital}" if isbn_print or isbn_digital else "   ISBN: não informado",
            f"   1. {genre or 'Literatura Brasileira'}  2. Ficção  I. Título.",
            "   Classificação bibliográfica: a preencher",
            f"Índices para catálogo sistemático:",
            f"1. Ficção : Literatura brasileira  869.3",
        ]
        r_cb = p_cip_b.add_run("\n".join(cip_lines))
        r_cb.font.name = font_name
        r_cb.font.size = Pt(8.5)

        doc.add_page_break()

        # ---------------------------------------------------------------------
        # PÁGINA 6: DEDICATÓRIA / EPÍGRAFE
        # ---------------------------------------------------------------------
        for _ in range(12):
            doc.add_paragraph()

        ded_text = dedication.strip()

        p_ded = doc.add_paragraph()
        p_ded.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_ded.paragraph_format.line_spacing = 1.2
        p_ded.paragraph_format.first_line_indent = Pt(0)
        p_ded.paragraph_format.space_after = Pt(0)

        for line in ded_text.split("\n"):
            r_d = p_ded.add_run(line + "\n")
            r_d.italic = True
            r_d.font.name = font_name
            r_d.font.size = Pt(font_size)

        doc.add_page_break()

        # ---------------------------------------------------------------------
        # PÁGINA 7: SUMÁRIO (TABLE OF CONTENTS)
        # ---------------------------------------------------------------------
        p_toc = doc.add_paragraph()
        p_toc.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_toc.paragraph_format.space_before = Pt(36)
        p_toc.paragraph_format.space_after = Pt(28)
        p_toc.paragraph_format.first_line_indent = Pt(0)
        r_toc = p_toc.add_run("SUMÁRIO")
        r_toc.bold = True
        r_toc.font.name = font_name
        r_toc.font.size = Pt(font_size + 4)

        acts_list = project_structure.get("acts", [])
        for act in acts_list:
            if len(acts_list) > 1:
                p_act_toc = doc.add_paragraph()
                p_act_toc.paragraph_format.space_before = Pt(12)
                p_act_toc.paragraph_format.space_after = Pt(4)
                p_act_toc.paragraph_format.first_line_indent = Pt(0)
                r_at = p_act_toc.add_run(act.get("name", "Ato").upper())
                r_at.bold = True
                r_at.font.name = font_name
                r_at.font.size = Pt(font_size)

            for ch in act.get("chapters", []):
                p_ch_toc = doc.add_paragraph()
                p_ch_toc.paragraph_format.space_before = Pt(3)
                p_ch_toc.paragraph_format.space_after = Pt(3)
                p_ch_toc.paragraph_format.first_line_indent = Pt(0)
                r_ct = p_ch_toc.add_run(ch.get("name", "Capítulo"))
                r_ct.font.name = font_name
                r_ct.font.size = Pt(font_size - 0.5)

        doc.add_page_break()

    # =========================================================================
    # MIOLO DA OBRA (BODY SECTION)
    # =========================================================================
    # Create separate section for the book body so headers & footers run here
    sec_body = doc.add_section()
    _apply_section_geometry(sec_body, book_size)
    sec_body.header.is_linked_to_previous = False
    sec_body.footer.is_linked_to_previous = False

    # Running Header with Book Title (centered, small caps / uppercase)
    if include_header_title and title:
        p_hdr = sec_body.header.paragraphs[0]
        p_hdr.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_hdr = p_hdr.add_run(title.upper())
        r_hdr.font.name = font_name
        r_hdr.font.size = Pt(8.5)
        r_hdr.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
        rPr = r_hdr._r.get_or_add_rPr()
        rPr.append(OxmlElement("w:caps"))

    # Running Footer with native Page Number
    if include_page_number:
        p_ftr = sec_body.footer.paragraphs[0]
        _add_page_number_to_footer(p_ftr, font_name, Pt(9.0))
        # Start numbering from 1 on the book body
        pgNumType = OxmlElement("w:pgNumType")
        pgNumType.set(qn("w:start"), "1")
        sec_body._sectPr.append(pgNumType)

    # Output Acts -> Chapters -> Scenes
    acts = project_structure.get("acts", [])
    has_multiple_acts = len(acts) > 1
    chapter_count = 0

    for act_idx, act in enumerate(acts):
        act_name = act.get("name", f"Ato {act_idx + 1}")
        if has_multiple_acts:
            # Act break page
            if chapter_count > 0:
                doc.add_page_break()
            p_act = doc.add_paragraph()
            p_act.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_act.paragraph_format.space_before = Pt(72)
            p_act.paragraph_format.space_after = Pt(28)
            p_act.paragraph_format.first_line_indent = Pt(0)
            r_act = p_act.add_run(act_name.upper())
            r_act.bold = True
            r_act.font.name = font_name
            r_act.font.size = Pt(font_size + 6)

        chapters = act.get("chapters", [])
        for ch_idx, chapter in enumerate(chapters):
            ch_name = chapter.get("name", f"Capítulo {ch_idx + 1}")

            # Each chapter begins on a fresh page
            if chapter_count > 0 or has_multiple_acts:
                doc.add_page_break()
            chapter_count += 1

            p_ch = doc.add_paragraph()
            p_ch.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_ch.paragraph_format.space_before = Pt(54)
            p_ch.paragraph_format.space_after = Pt(28)
            p_ch.paragraph_format.first_line_indent = Pt(0)
            r_ch = p_ch.add_run(ch_name)
            r_ch.bold = True
            r_ch.font.name = font_name
            r_ch.font.size = Pt(font_size + 4)

            scenes = chapter.get("scenes", [])
            for sc_idx, scene in enumerate(scenes):
                sc_name = scene.get("name", f"Cena {sc_idx + 1}")

                # RULE: Scenes do NOT show scene titles.
                # Only insert a centered scene separator between scenes.
                if sc_idx > 0 and scene_separator.strip():
                    p_sep = doc.add_paragraph()
                    p_sep.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p_sep.paragraph_format.space_before = Pt(16)
                    p_sep.paragraph_format.space_after = Pt(16)
                    p_sep.paragraph_format.first_line_indent = Pt(0)
                    r_sep = p_sep.add_run(scene_separator)
                    r_sep.font.name = font_name
                    r_sep.font.size = Pt(font_size)

                # Load and write scene text content
                content_html = ""
                if model:
                    hierarchy = [act_name, ch_name, sc_name]
                    content_html = model.load_scene_content(hierarchy) or ""

                _append_html_to_docx(
                    doc=doc,
                    html_content=content_html,
                    font_name=font_name,
                    font_size=font_size,
                    line_spacing=line_spacing,
                    first_line_indent_cm=first_line_indent_cm,
                )

        # Standalone scenes directly in Act
        standalone_scenes = act.get("scenes", [])
        for sc_idx, scene in enumerate(standalone_scenes):
            sc_name = scene.get("name", f"Cena {sc_idx + 1}")
            if sc_idx > 0 or chapters:
                if scene_separator.strip():
                    p_sep = doc.add_paragraph()
                    p_sep.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p_sep.paragraph_format.space_before = Pt(16)
                    p_sep.paragraph_format.space_after = Pt(16)
                    p_sep.paragraph_format.first_line_indent = Pt(0)
                    r_sep = p_sep.add_run(scene_separator)
                    r_sep.font.name = font_name
                    r_sep.font.size = Pt(font_size)

            content_html = ""
            if model:
                hierarchy = [act_name, sc_name]
                content_html = model.load_scene_content(hierarchy) or ""

            _append_html_to_docx(
                doc=doc,
                html_content=content_html,
                font_name=font_name,
                font_size=font_size,
                line_spacing=line_spacing,
                first_line_indent_cm=first_line_indent_cm,
            )

    doc.save(output_path)
    return output_path


# ---------------------------------------------------------------------------
# HTML PARSING AND WORD PARAGRAPH FORMATTING
# ---------------------------------------------------------------------------
def _append_html_to_docx(
    doc: Document,
    html_content: str,
    font_name: str,
    font_size: int,
    line_spacing: float,
    first_line_indent_cm: float,
):
    """Converts HTML paragraphs from the editor to styled Word body paragraphs."""
    if not html_content or not html_content.strip():
        return

    # Strip prompt/action beat artifacts
    if "__________" in html_content:
        html_content = re.sub(r"_{10,}.*?_{10,}", "", html_content, flags=re.DOTALL)

    soup = BeautifulSoup(html_content, "html.parser")
    paragraphs = soup.find_all(["p", "div"])

    if not paragraphs:
        # Fallback to plain-text line split
        raw_lines = [l.strip() for l in soup.get_text().split("\n") if l.strip()]
        for line in raw_lines:
            p = doc.add_paragraph()
            _apply_body_paragraph_style(p, line_spacing, first_line_indent_cm)
            r = p.add_run(line)
            r.font.name = font_name
            r.font.size = Pt(font_size)
        return

    for p_elem in paragraphs:
        text = p_elem.get_text(strip=True)
        if not text:
            continue

        p = doc.add_paragraph()
        _apply_body_paragraph_style(p, line_spacing, first_line_indent_cm)

        # Parse formatted runs (bold, italic, strong, em)
        if not p_elem.find_all(["b", "strong", "i", "em", "span"]):
            r = p.add_run(p_elem.get_text())
            r.font.name = font_name
            r.font.size = Pt(font_size)
        else:
            for child in p_elem.contents:
                if isinstance(child, str):
                    if child:
                        r = p.add_run(child)
                        r.font.name = font_name
                        r.font.size = Pt(font_size)
                else:
                    tag_name = child.name.lower() if child.name else ""
                    child_text = child.get_text()
                    if child_text:
                        r = p.add_run(child_text)
                        r.font.name = font_name
                        r.font.size = Pt(font_size)
                        if tag_name in ("b", "strong"):
                            r.bold = True
                        if tag_name in ("i", "em"):
                            r.italic = True


def _apply_body_paragraph_style(paragraph, line_spacing: float, indent_cm: float):
    """Enforces standard book formatting: justified, line spacing, and 1.25 cm first-line indent."""
    paragraph.paragraph_format.line_spacing = line_spacing
    paragraph.paragraph_format.first_line_indent = Cm(indent_cm)
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
