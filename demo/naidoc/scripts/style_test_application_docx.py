#!/usr/bin/env python3
"""Apply accessible response styling to Pandoc-generated application DOCX files.

This deliberately uses only the Python standard library. DOCX files are ZIP
archives containing WordprocessingML, so no office-document Python dependency
is needed.
"""

from __future__ import annotations

import argparse
import os
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
W = f"{{{W_NS}}}"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"

# One palette for the whole document: navy structure, near-black labels,
# ink-blue "filled in by the applicant" answers on a light blue-grey panel.
HEADING_COLOUR = "1F3864"
QUESTION_COLOUR = "262626"
ANSWER_COLOUR = "17365D"
ANSWER_FILL = "EFF4FA"
ANSWER_EDGE = "2F5C8F"
ANSWER_RULE = "C7D7E8"
SCAFFOLD_COLOUR = "767676"
FORM_FONT = "Arial"


def text_of(element: ET.Element) -> str:
    return "".join(node.text or "" for node in element.findall(".//w:t", NS)).strip()


def ensure_child(parent: ET.Element, tag: str) -> ET.Element:
    child = parent.find(f"w:{tag}", NS)
    if child is None:
        child = ET.SubElement(parent, f"{W}{tag}")
    return child


def style_name_of(paragraph: ET.Element) -> str:
    paragraph_properties = paragraph.find("w:pPr", NS)
    if paragraph_properties is None:
        return ""
    paragraph_style = paragraph_properties.find("w:pStyle", NS)
    if paragraph_style is None:
        return ""
    return paragraph_style.get(f"{W}val", "").replace(" ", "").lower()


def is_applicant_response(paragraph: ET.Element) -> bool:
    if style_name_of(paragraph) == "applicantresponse":
        return True

    # Backwards compatibility for DOCX files made by the previous generator.
    return text_of(paragraph).startswith("APPLICANT ANSWER -")


def is_form_question(paragraph: ET.Element) -> bool:
    return style_name_of(paragraph) == "formquestion"


def is_form_scaffold(paragraph: ET.Element) -> bool:
    return style_name_of(paragraph) == "formscaffold"


def style_form_scaffold(paragraph: ET.Element) -> None:
    for run in paragraph.findall(".//w:r", NS):
        run_properties = run.find("w:rPr", NS)
        if run_properties is None:
            run_properties = ET.Element(f"{W}rPr")
            run.insert(0, run_properties)
        color = ensure_child(run_properties, "color")
        color.set(f"{W}val", SCAFFOLD_COLOUR)
        for size_tag in ("sz", "szCs"):
            size = ensure_child(run_properties, size_tag)
            size.set(f"{W}val", "20")  # 10 pt


def style_form_question(paragraph: ET.Element) -> None:
    paragraph_properties = paragraph.find("w:pPr", NS)
    if paragraph_properties is None:
        paragraph_properties = ET.Element(f"{W}pPr")
        paragraph.insert(0, paragraph_properties)

    ensure_child(paragraph_properties, "keepNext")
    ensure_child(paragraph_properties, "keepLines")
    spacing = ensure_child(paragraph_properties, "spacing")
    spacing.set(f"{W}before", "200")
    spacing.set(f"{W}after", "60")

    for run in paragraph.findall(".//w:r", NS):
        run_properties = run.find("w:rPr", NS)
        if run_properties is None:
            run_properties = ET.Element(f"{W}rPr")
            run.insert(0, run_properties)
        bold = ensure_child(run_properties, "b")
        bold.set(f"{W}val", "1")
        color = ensure_child(run_properties, "color")
        color.set(f"{W}val", QUESTION_COLOUR)
        for size_tag in ("sz", "szCs"):
            size = ensure_child(run_properties, size_tag)
            size.set(f"{W}val", "22")  # 11 pt


def set_border(
    borders: ET.Element,
    side: str,
    *,
    colour: str,
    size: str,
    space: str,
) -> None:
    border = ensure_child(borders, side)
    border.set(f"{W}val", "single")
    border.set(f"{W}color", colour)
    border.set(f"{W}sz", size)
    border.set(f"{W}space", space)


def remove_legacy_answer_label(paragraph: ET.Element) -> None:
    if not text_of(paragraph).startswith("APPLICANT ANSWER -"):
        return
    remaining = "APPLICANT ANSWER -"
    for text_node in paragraph.findall(".//w:t", NS):
        if not remaining:
            break
        text = text_node.text or ""
        matching_length = 0
        for expected, actual in zip(remaining, text):
            if expected != actual:
                break
            matching_length += 1
        if matching_length:
            text_node.text = text[matching_length:].lstrip()
            remaining = remaining[matching_length:]


def keep_lead_in_with_response(
    paragraph: ET.Element,
    parent_by_child: dict[ET.Element, ET.Element],
) -> None:
    parent = parent_by_child.get(paragraph)
    if parent is None:
        return

    siblings = list(parent)
    position = siblings.index(paragraph)
    for sibling in reversed(siblings[:position]):
        if sibling.tag != f"{W}p":
            continue
        properties = sibling.find("w:pPr", NS)
        if properties is None:
            properties = ET.Element(f"{W}pPr")
            sibling.insert(0, properties)
        ensure_child(properties, "keepNext")
        spacing = ensure_child(properties, "spacing")
        spacing.set(f"{W}after", "40")
        return


def style_table(table: ET.Element) -> None:
    """Answer tables (budget, co-contribution breakdown): light grid, shaded header."""
    table_properties = table.find("w:tblPr", NS)
    if table_properties is None:
        table_properties = ET.Element(f"{W}tblPr")
        table.insert(0, table_properties)
    borders = ensure_child(table_properties, "tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        set_border(borders, side, colour=ANSWER_RULE, size="4", space="0")

    for row_index, row in enumerate(table.findall("w:tr", NS)):
        for cell in row.findall("w:tc", NS):
            if row_index == 0:
                cell_properties = cell.find("w:tcPr", NS)
                if cell_properties is None:
                    cell_properties = ET.Element(f"{W}tcPr")
                    cell.insert(0, cell_properties)
                shading = ensure_child(cell_properties, "shd")
                shading.set(f"{W}val", "clear")
                shading.set(f"{W}color", "auto")
                shading.set(f"{W}fill", ANSWER_FILL)

            for run in cell.findall(".//w:r", NS):
                run_properties = run.find("w:rPr", NS)
                if run_properties is None:
                    run_properties = ET.Element(f"{W}rPr")
                    run.insert(0, run_properties)
                color = ensure_child(run_properties, "color")
                color.set(f"{W}val", ANSWER_COLOUR)
                # Word stores font size in half-points: 21 = 10.5 pt.
                for size_tag in ("sz", "szCs"):
                    size = ensure_child(run_properties, size_tag)
                    size.set(f"{W}val", "21")
                if row_index == 0:
                    bold_tag = ensure_child(run_properties, "b")
                    bold_tag.set(f"{W}val", "1")


def style_document_xml(xml_bytes: bytes) -> bytes:
    ET.register_namespace("w", W_NS)
    root = ET.fromstring(xml_bytes)
    parent_by_child = {child: parent for parent in root.iter() for child in parent}

    # Each inline answer is a custom-styled paragraph placed immediately after
    # its form field. A restrained response panel distinguishes supplied data
    # without repeating a label on every answer or relying on colour alone.
    # Form questions are bolded so each field label reads as a unit with the
    # response panel below it.
    for paragraph in root.findall(".//w:p", NS):
        if is_form_question(paragraph):
            style_form_question(paragraph)
            continue
        if is_form_scaffold(paragraph):
            style_form_scaffold(paragraph)
            continue
        if not is_applicant_response(paragraph):
            continue

        remove_legacy_answer_label(paragraph)
        keep_lead_in_with_response(paragraph, parent_by_child)

        paragraph_properties = paragraph.find("w:pPr", NS)
        if paragraph_properties is None:
            paragraph_properties = ET.Element(f"{W}pPr")
            paragraph.insert(0, paragraph_properties)

        shading = ensure_child(paragraph_properties, "shd")
        shading.set(f"{W}val", "clear")
        shading.set(f"{W}color", "auto")
        shading.set(f"{W}fill", ANSWER_FILL)

        indentation = ensure_child(paragraph_properties, "ind")
        indentation.set(f"{W}left", "360")
        indentation.set(f"{W}right", "180")

        spacing = ensure_child(paragraph_properties, "spacing")
        spacing.set(f"{W}before", "80")
        spacing.set(f"{W}after", "180")
        spacing.set(f"{W}line", "276")
        spacing.set(f"{W}lineRule", "auto")

        borders = ensure_child(paragraph_properties, "pBdr")
        set_border(borders, "left", colour=ANSWER_EDGE, size="20", space="7")
        set_border(borders, "top", colour=ANSWER_RULE, size="4", space="5")
        set_border(borders, "bottom", colour=ANSWER_RULE, size="4", space="5")

        ensure_child(paragraph_properties, "keepLines")

        for run in paragraph.findall(".//w:r", NS):
            run_properties = run.find("w:rPr", NS)
            if run_properties is None:
                run_properties = ET.Element(f"{W}rPr")
                run.insert(0, run_properties)
            color = ensure_child(run_properties, "color")
            color.set(f"{W}val", ANSWER_COLOUR)
            for size_tag in ("sz", "szCs"):
                size = ensure_child(run_properties, size_tag)
                size.set(f"{W}val", "22")  # 11 pt

    for table in root.findall(".//w:tbl", NS):
        style_table(table)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def style_styles_xml(xml_bytes: bytes) -> bytes:
    """Give every heading level the document's single structural colour."""
    ET.register_namespace("w", W_NS)
    root = ET.fromstring(xml_bytes)
    for style in root.findall("w:style", NS):
        style_id = style.get(f"{W}styleId", "")
        if not (style_id.startswith("Heading") or style_id == "Title"):
            continue
        run_properties = style.find("w:rPr", NS)
        if run_properties is None:
            run_properties = ET.SubElement(style, f"{W}rPr")
        color = ensure_child(run_properties, "color")
        color.set(f"{W}val", HEADING_COLOUR)
        for theme_attribute in ("themeColor", "themeTint", "themeShade"):
            color.attrib.pop(f"{W}{theme_attribute}", None)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def style_theme_xml(xml_bytes: bytes) -> bytes:
    """Use one sans-serif family for headings and body text alike.

    Pandoc's reference document takes its fonts from the theme (Calibri Light
    headings, Calibri body — substituted with a serif/sans mismatch on Linux),
    so retargeting the theme's latin fonts restyles the whole document.
    """
    ET.register_namespace("a", A_NS)
    root = ET.fromstring(xml_bytes)
    for font_group in ("majorFont", "minorFont"):
        for latin in root.findall(f".//a:{font_group}/a:latin", {"a": A_NS}):
            latin.set("typeface", FORM_FONT)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def style_docx(path: Path) -> None:
    path = path.resolve()
    with zipfile.ZipFile(path, "r") as source:
        replacements = {
            "word/document.xml": style_document_xml(source.read("word/document.xml")),
            "word/styles.xml": style_styles_xml(source.read("word/styles.xml")),
        }
        if "word/theme/theme1.xml" in source.namelist():
            replacements["word/theme/theme1.xml"] = style_theme_xml(
                source.read("word/theme/theme1.xml")
            )

        with tempfile.NamedTemporaryFile(
            prefix=f".{path.stem}-", suffix=".docx", dir=path.parent, delete=False
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)

        try:
            with zipfile.ZipFile(temporary_path, "w") as target:
                for item in source.infolist():
                    data = replacements.get(item.filename, None)
                    target.writestr(
                        item, data if data is not None else source.read(item.filename)
                    )
            os.replace(temporary_path, path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("docx", nargs="+", type=Path)
    args = parser.parse_args()
    for path in args.docx:
        style_docx(path)


if __name__ == "__main__":
    main()
