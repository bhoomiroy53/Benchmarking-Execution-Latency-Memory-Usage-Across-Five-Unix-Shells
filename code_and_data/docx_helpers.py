"""docx_helpers.py - Cureus-style formatting primitives for python-docx (no indents, single
line return between paragraphs, sentence-case major headings, italic title-case minor headings,
native Word (OMML) equations, cell-based tables with a bold header row)."""
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

M = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def new_document():
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(12)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    pf = st.paragraph_format
    pf.first_line_indent = Pt(0)
    pf.left_indent = Pt(0)
    pf.space_before = Pt(0)
    pf.space_after = Pt(12)
    pf.line_spacing = 1.15
    for s in doc.sections:
        s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Pt(72)
    return doc


def para(doc, text="", bold=False, italic=False, align=None, size=None, space_after=12):
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.space_after = Pt(space_after)
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if text:
        r = p.add_run(text)
        r.bold, r.italic = bold, italic
        if size:
            r.font.size = Pt(size)
    return p


def rich(doc, parts, space_after=12):
    """parts: list of (text, style) where style in {'', 'b', 'i', 'bi'}."""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    for text, style in parts:
        r = p.add_run(text)
        r.bold = "b" in style
        r.italic = "i" in style
    return p


def title(doc, text):
    para(doc, text, bold=True, size=16, space_after=12)


def major(doc, text):
    """Major subheader: sentence case, bold."""
    para(doc, text, bold=True, size=13, space_after=12)


def minor(doc, text):
    """Minor subheader: Title Case, italic."""
    para(doc, text, italic=True, bold=True, space_after=12)


def lead(doc, label, text):
    """Third-level subheader in sentence case leading off the paragraph, followed by a colon."""
    return rich(doc, [(label + ": ", "i"), (text, "")])


# ------------------------------------------------------------------ OMML equations
def _m(tag, **attrs):
    el = OxmlElement("m:" + tag)
    for k, v in attrs.items():
        el.set(qn("m:" + k), v)
    return el


def mr(text, italic=True):
    r = _m("r")
    if not italic:
        rpr = _m("rPr")
        sty = _m("sty", val="p")
        rpr.append(sty)
        r.append(rpr)
    t = _m("t")
    t.text = text
    t.set(qn("xml:space"), "preserve")
    r.append(t)
    return r


def sub(base, subscript):
    s = _m("sSub")
    e = _m("e"); [e.append(x) for x in (base if isinstance(base, list) else [base])]
    b = _m("sub"); [b.append(x) for x in (subscript if isinstance(subscript, list) else [subscript])]
    s.append(e); s.append(b)
    return s


def frac(num, den):
    f = _m("f")
    n = _m("num"); [n.append(x) for x in (num if isinstance(num, list) else [num])]
    d = _m("den"); [d.append(x) for x in (den if isinstance(den, list) else [den])]
    f.append(n); f.append(d)
    return f


def sqrt(inner):
    rad = _m("rad")
    pr = _m("radPr"); pr.append(_m("degHide", val="1")); rad.append(pr)
    rad.append(_m("deg"))
    e = _m("e"); [e.append(x) for x in (inner if isinstance(inner, list) else [inner])]
    rad.append(e)
    return rad


def bar(inner):
    b = _m("bar")
    pr = _m("barPr"); pr.append(_m("pos", val="top")); b.append(pr)
    e = _m("e"); [e.append(x) for x in (inner if isinstance(inner, list) else [inner])]
    b.append(e)
    return b


def equation(doc, elements, number):
    """Centered display equation followed by its number in parentheses."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(12)
    om = _m("oMath")
    for x in elements:
        om.append(x)
    p._p.append(om)
    p.add_run(f"     ({number})")
    return p


# ------------------------------------------------------------------ tables
def _shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), hexcolor)
    tcPr.append(sh)


def table(doc, caption, header, rows, legend, font=8):
    para(doc, caption, bold=True, space_after=6)
    t = doc.add_table(rows=1 + len(rows), cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, h in enumerate(header):
        c = t.rows[0].cells[j]
        c.text = ""
        r = c.paragraphs[0].add_run(str(h))
        r.bold = True
        r.font.size = Pt(font)
        c.paragraphs[0].paragraph_format.space_after = Pt(0)
        _shade(c, "E7E6E1")
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            c = t.rows[i].cells[j]
            c.text = ""
            r = c.paragraphs[0].add_run(str(val))
            r.font.size = Pt(font)
            c.paragraphs[0].paragraph_format.space_after = Pt(0)
    para(doc, legend, size=9, space_after=12)
    return t
