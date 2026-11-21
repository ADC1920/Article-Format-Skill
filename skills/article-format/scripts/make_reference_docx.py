# -*- coding: utf-8 -*-
"""
pandoc 参考模板生成器：从 article-format.yaml 生成 pandoc 可用的 reference.docx。

用途：需要「任意 Markdown → docx」的通用转换时，用同一份规格配置生成 Word 模板，
     再交给 pandoc --reference-doc 使用，保证两条输出通道样式一致。

用法：
    # 1) 生成模板（首次或规格变更后）
    python make_reference_docx.py [输出路径]        # 默认 <skill>/reference.docx

    # 2) 用模板转换
    pandoc input.md --reference-doc=reference.docx -o output.docx

局限（务必知悉）：
- pandoc 只把「正文段落 / 标题 / 表格」映射到模板样式，**不生成 Word 程序自动编号**
  （md 的 `1.` 会被当普通文本或 pandoc 自己的列表处理），也不做「标号顶格」这类精细控制。
- 因此**精确排版仍以 article_style.py 为准**；本模板用于通用转换与样式基线对齐。
- 模板中的 Heading 1-3 同时写入 outlineLvl，保证 pandoc 输出在 Word 导航窗格可见。
"""
import os
import subprocess
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

from spec_loader import load_spec

SPEC = load_spec()
FONT_HEADING = SPEC["fonts"]["heading"]
FONT_BODY = SPEC["fonts"]["body"]
FONT_WESTERN = SPEC["fonts"]["western"]
SIZES = SPEC["sizes_pt"]
SPACING = SPEC["spacing"]
INDENT = SPEC["indent"]
LINE_SPACING = SPACING["line"]
_hex = str(SPEC["color"]["text"]).lstrip("#")
TEXT_COLOR = RGBColor(int(_hex[0:2], 16), int(_hex[2:4], 16), int(_hex[4:6], 16))


def _set_style_font(style, cn_font, size_pt, bold=None):
    """设置样式的中西文字体与字号（含 eastAsia）"""
    style.font.name = FONT_WESTERN
    style.font.size = Pt(size_pt)
    if bold is not None:
        style.font.bold = bold
    style.font.color.rgb = TEXT_COLOR
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), FONT_WESTERN)
    rfonts.set(qn("w:hAnsi"), FONT_WESTERN)
    rfonts.set(qn("w:eastAsia"), cn_font)


def _set_style_spacing(style, before_pt=None, after_pt=None, line=None):
    pf = style.paragraph_format
    if before_pt is not None:
        pf.space_before = Pt(before_pt)
    if after_pt is not None:
        pf.space_after = Pt(after_pt)
    if line is not None:
        pf.line_spacing = line


def _ensure_outline_level(style, level):
    """写入 outlineLvl，使 Word/WPS 导航窗格可见（与 article_style.py 行为一致）"""
    ppr = style.element.get_or_add_pPr()
    ol = ppr.find(qn("w:outlineLvl"))
    if ol is None:
        ol = OxmlElement("w:outlineLvl")
        ppr.append(ol)
    ol.set(qn("w:val"), str(level))


def _ensure_first_line_indent(style, chars):
    """样式级首行缩进（按字符），供 pandoc 的正文样式使用"""
    ppr = style.element.get_or_add_pPr()
    ind = ppr.find(qn("w:ind"))
    if ind is None:
        ind = OxmlElement("w:ind")
        ppr.append(ind)
    ind.set(qn("w:firstLineChars"), str(int(chars * 100)))
    ind.set(qn("w:firstLine"), "0")


def build(reference_base, out_path):
    """基于 pandoc 默认模板改写样式；reference_base 为 pandoc 自带模板路径"""
    doc = Document(reference_base)

    # 正文类样式：pandoc 会把普通段落映射到 Normal / Body Text / First Paragraph，
    # 三者都要写同一套规格，否则输出字体不一致（实测未设时回落 pandoc 默认，正文变样）。
    # Compact 用于列表项，只统一字体字号，不加首行缩进（否则列表会错位）。
    body_names = {s.name for s in doc.styles}
    for name in ["Normal", "Body Text", "First Paragraph"]:
        if name not in body_names:
            continue
        st = doc.styles[name]
        _set_style_font(st, FONT_BODY, SIZES["body"])
        _set_style_spacing(st, before_pt=0, after_pt=0, line=LINE_SPACING)
        _ensure_first_line_indent(st, INDENT["body_first_line_chars"])

    for name in ["Compact", "List Paragraph"]:
        if name not in body_names:
            continue
        st = doc.styles[name]
        _set_style_font(st, FONT_BODY, SIZES["body"])
        _set_style_spacing(st, before_pt=0, after_pt=0, line=LINE_SPACING)

    # 标题层级：一级黑体小三居中，二三级黑体四号
    for level, key, align in (
        (1, "h1", WD_ALIGN_PARAGRAPH.CENTER),
        (2, "h2", WD_ALIGN_PARAGRAPH.JUSTIFY),
        (3, "h3", WD_ALIGN_PARAGRAPH.JUSTIFY),
    ):
        try:
            st = doc.styles[f"Heading {level}"]
        except KeyError:
            continue
        _set_style_font(st, FONT_HEADING, SIZES[key], bold=True)
        st.paragraph_format.alignment = align
        gap = SPACING["h1_before_after_pt"] if level == 1 else SPACING["h2_before_after_pt"]
        _set_style_spacing(st, before_pt=gap, after_pt=gap, line=LINE_SPACING)
        _ensure_outline_level(st, level - 1)

    # 文档主标题（pandoc 的 Title 样式）
    if "Title" in [s.name for s in doc.styles]:
        title = doc.styles["Title"]
        _set_style_font(title, FONT_HEADING, SIZES["doc_title"], bold=True)
        title.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_style_spacing(title, line=LINE_SPACING)

    # 表格样式（若模板带 Table 样式）
    try:
        tbl = doc.styles["Table"]
        _set_style_font(tbl, FONT_BODY, SIZES["table"])
    except KeyError:
        pass

    doc.save(out_path)
    return out_path


def get_pandoc_default(output_path):
    """导出 pandoc 自带 reference.docx 作为改写基底"""
    with open(output_path, "wb") as f:
        proc = subprocess.run(
            ["pandoc", "--print-default-data-file", "reference.docx"],
            stdout=f, stderr=subprocess.PIPE,
        )
    if proc.returncode != 0:
        raise RuntimeError(f"pandoc 导出模板失败: {proc.stderr.decode(errors='replace')}")
    return output_path


def main():
    skill_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(skill_root, "reference.docx")
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_pandoc_base.docx")
    try:
        get_pandoc_default(base)
        build(base, out_path)
    finally:
        if os.path.exists(base):
            os.remove(base)
    print(f"已生成 pandoc 参考模板: {out_path}")
    print(f"用法: pandoc input.md --reference-doc={os.path.basename(out_path)} -o output.docx")


if __name__ == "__main__":
    main()
