"""Convert thesis .docx to .md for easier reading."""
import re
from docx import Document
from docx.oxml.ns import qn

import sys

if len(sys.argv) >= 3:
    SRC, DST = sys.argv[1], sys.argv[2]
else:
    SRC = "/Users/macbookpro/Desktop/viorama-website-new/thesis/perancangan_pengujian_dan_evaluasi_sistem.docx"
    DST = "/Users/macbookpro/Desktop/viorama-website-new/thesis/perancangan_pengujian_dan_evaluasi_sistem.md"


def runs_to_md(paragraph):
    """Serialize runs into markdown, preserving bold/italic.
    Merges consecutive runs with the same formatting so we don't emit
    ugly sequences like **A****B**.
    """
    # First pass: collect (text, bold, italic) tuples
    segments = []
    for run in paragraph.runs:
        text = run.text
        if text is None or text == "":
            continue
        b = bool(run.bold)
        i = bool(run.italic)
        if segments and segments[-1][1] == b and segments[-1][2] == i:
            segments[-1] = (segments[-1][0] + text, b, i)
        else:
            segments.append((text, b, i))

    # Second pass: render. Strip whitespace from formatted segments so
    # markdown delimiters hug the actual text (avoids "** word **").
    parts = []
    for text, b, i in segments:
        if b or i:
            leading = len(text) - len(text.lstrip())
            trailing = len(text) - len(text.rstrip())
            lead_ws = text[:leading]
            trail_ws = text[len(text) - trailing:] if trailing else ""
            core = text[leading:len(text) - trailing] if trailing else text[leading:]
            if not core:
                parts.append(text)
                continue
            if b and i:
                wrapped = f"***{core}***"
            elif b:
                wrapped = f"**{core}**"
            else:
                wrapped = f"*{core}*"
            parts.append(lead_ws + wrapped + trail_ws)
        else:
            parts.append(text)
    return "".join(parts).strip()


def heading_level(paragraph):
    """Return heading level 1-6 if paragraph is a heading style, else 0."""
    name = (paragraph.style.name or "").lower()
    m = re.match(r"heading\s+(\d+)", name)
    if m:
        return int(m.group(1))
    if name == "title":
        return 1
    return 0


def is_list_item(paragraph):
    """Detect if paragraph is part of a numbered/bulleted list."""
    pPr = paragraph._p.find(qn("w:pPr"))
    if pPr is None:
        return None
    numPr = pPr.find(qn("w:numPr"))
    if numPr is None:
        return None
    ilvl_el = numPr.find(qn("w:ilvl"))
    numId_el = numPr.find(qn("w:numId"))
    ilvl = int(ilvl_el.get(qn("w:val"))) if ilvl_el is not None else 0
    numId = numId_el.get(qn("w:val")) if numId_el is not None else "0"
    return (ilvl, numId)


def table_to_md(table):
    rows = []
    for r_idx, row in enumerate(table.rows):
        cells = []
        for cell in row.cells:
            cell_text = " ".join(
                runs_to_md(p) for p in cell.paragraphs if runs_to_md(p)
            ).replace("\n", " ").replace("|", "\\|")
            cells.append(cell_text or " ")
        rows.append("| " + " | ".join(cells) + " |")
        if r_idx == 0:
            rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
    return "\n".join(rows)


def iter_block_items(parent):
    """Yield paragraphs and tables in document order."""
    from docx.document import Document as _Doc
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    if isinstance(parent, _Doc):
        parent_elm = parent.element.body
    else:
        parent_elm = parent

    for child in parent_elm.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, parent)
        elif child.tag == qn("w:tbl"):
            yield Table(child, parent)


def main():
    doc = Document(SRC)
    out_lines = []
    list_counters = {}  # numId -> running counter at level 0

    for block in iter_block_items(doc):
        # Table
        if block.__class__.__name__ == "Table":
            out_lines.append("")
            out_lines.append(table_to_md(block))
            out_lines.append("")
            continue

        p = block
        text = runs_to_md(p)

        # Skip empty paragraphs but preserve as blank line
        if not text:
            if out_lines and out_lines[-1] != "":
                out_lines.append("")
            continue

        # Heading
        lvl = heading_level(p)
        if lvl:
            out_lines.append("")
            out_lines.append(f"{'#' * min(lvl, 6)} {text}")
            out_lines.append("")
            continue

        # List item
        list_info = is_list_item(p)
        if list_info is not None:
            ilvl, numId = list_info
            indent = "  " * ilvl
            # Heuristic: bullet vs numbered — try bullet by default, but use number
            # if the paragraph text starts with a digit pattern (rare here since Word
            # strips it). We'll use numbered list for most cases.
            counter_key = (numId, ilvl)
            list_counters[counter_key] = list_counters.get(counter_key, 0) + 1
            n = list_counters[counter_key]
            out_lines.append(f"{indent}{n}. {text}")
            continue
        else:
            # reset counters when leaving a list
            list_counters = {}

        # Centered / quote heuristic via alignment
        out_lines.append(text)
        out_lines.append("")

    # Collapse multiple blank lines
    cleaned = []
    blank = False
    for ln in out_lines:
        if ln == "":
            if not blank:
                cleaned.append(ln)
            blank = True
        else:
            cleaned.append(ln)
            blank = False

    with open(DST, "w", encoding="utf-8") as f:
        f.write("\n".join(cleaned).strip() + "\n")

    print(f"Saved: {DST}")
    print(f"Lines: {len(cleaned)}")


if __name__ == "__main__":
    main()
