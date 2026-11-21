# -*- coding: utf-8 -*-
"""article_style.py — 文章类文档排版规范（全局默认）。

由「排版规范十三条」驱动。本文件是样式内核，专门负责把一份 docx
文档按规范套用全部样式：标题层级、正文、标号自动编号、表格、页脚页码、
左侧导航目录（Heading 1/2/3 大纲级别）。

设计原则
--------
1. 样式通过改 python-docx 的**内置样式对象**实现（Normal / Heading 1/2/3 /
   Title），这样 Word/WPS 的「导航窗格」能靠大纲级别自动生成左侧目录，
   不用套用外部目录域。
2. 正文标号 1. / 1) / (1) 用**新建的抽象编号（abstractNum）+ 实例（num）**，
   写入 numbering.xml，保证每级列表独立从 1 开始、编号缩进与文本缩进归 0、
   顶格排版、编号与文字之间空一格。
3. 所有字体（中文 + 西文/Times New Roman）/ 字号 / 行距 / 缩进 / 对齐统一
   收敛为常量，一处改、全局改。

用法
----
    from article_style import apply_article_style, add_auto_numbered_list
    from docx import Document
    doc = Document()
    apply_article_style(doc)          # 套用全部样式
    add_auto_numbered_list(doc, ["甲", "乙"], level=1)   # 1. 1. 1. ...
    doc.save("out.docx")

也可作为独立工具：
    python article_style.py <in.docx> <out.docx>   # 对已生成骨架的文档套用样式
"""

import copy
import re
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, Cm

from spec_loader import load_spec, resolve_profile

# 规格唯一权威源：技能根目录 article-format.yaml（默认 profile）或 profiles/<文体>.yaml。
# 改 yaml 即改规格，无需改本文件常量。常量由 _init_spec_constants() 统一赋值，
# 可在同一进程内用 set_profile() 切换文体（重新套用另一套规格）。
SPEC = load_spec()
PROFILE = resolve_profile()


# --------------------------------------------------------------------------- #
# 常量区：全部排版参数（与排版规范十三条一一对应）                                #
# --------------------------------------------------------------------------- #

# 字号（磅）。Word 记字号为半磅，python-docx Pt() 直接是磅。
# 常量由 _apply_spec_constants() 统一赋值，set_profile() 可在同进程内切换文体。
FONT_SIZE_HEADING_TITLE_PT = SPEC["sizes_pt"]["doc_title"]   # 主标题：黑体小二 18 磅
FONT_SIZE_HEADING1_PT = SPEC["sizes_pt"]["h1"]               # 一级标题：黑体小三 15 磅
FONT_SIZE_HEADING2_PT = SPEC["sizes_pt"]["h2"]               # 二级标题：黑体四号 14 磅
FONT_SIZE_HEADING3_PT = SPEC["sizes_pt"]["h3"]               # 三级标题：黑体四号 14 磅
FONT_SIZE_HEADING4_PT = SPEC["sizes_pt"]["h4"]               # 四级标题：黑体小四 12 磅
FONT_SIZE_HEADING5_PT = SPEC["sizes_pt"]["h5"]               # 五级标题：黑体小四 12 磅
FONT_SIZE_HEADING6_PT = SPEC["sizes_pt"]["h6"]               # 六级标题：黑体五号 10.5 磅
FONT_SIZE_HEADING7_PT = SPEC["sizes_pt"]["h7"]               # 七级标题：黑体五号 10.5 磅
FONT_SIZE_BODY_PT = SPEC["sizes_pt"]["body"]                 # 正文/表格/重点：宋体小四 12 磅
FONT_SIZE_PAGE_NUM_PT = SPEC["sizes_pt"]["footer"]           # 页脚页码：宋体小四 12 磅（v1.5.4 用户指令改；原 10.5）

# 页面（纸型与页边距）：读 article-format.yaml 的 page 节，缺省回落 A4 + 2.54cm。
# 此前脚本不设纸型，成品随 python-docx 默认模板落到 Letter（8.5×11in）。
PAGE_WIDTH_CM = float(SPEC.get("page", {}).get("width_cm", 21.0))
PAGE_HEIGHT_CM = float(SPEC.get("page", {}).get("height_cm", 29.7))
PAGE_MARGIN_CM = float(SPEC.get("page", {}).get("margin_cm", 2.54))

# 中文字体名（为避免依赖本机字库名，直接按 Word 常用名写）。
FONT_CN = SPEC["fonts"]["heading"]          # 标题中文字体
FONT_CN_BODY = SPEC["fonts"]["body"]        # 正文字体
FONT_EN = SPEC["fonts"]["western"]          # 所有英文/数字的西文字体
# 按层级分别指定标题中文字体（公文 GB/T 9704：第一层黑体、第二层楷体、
# 第三层及以下仿宋）。配置形状：heading_by_level: {1: 黑体, 2: 楷体, 3: 仿宋}，
# 未列出的层级回落到 fonts.heading。
FONT_CN_BY_LEVEL = SPEC.get("fonts", {}).get("heading_by_level") or {}


def _heading_font_for_level(level):
    """返回某级标题应使用的中文字体（按 profile 的 heading_by_level 覆盖）。"""
    if isinstance(FONT_CN_BY_LEVEL, dict):
        raw = FONT_CN_BY_LEVEL.get(level, FONT_CN_BY_LEVEL.get(str(level)))
        if raw:
            return str(raw)
    return FONT_CN

# 行距倍数。
LINE_SPACING = SPEC["spacing"]["line"]      # 全文统一 1.3 倍行距
# 固定行距（公文体按国标行网格：每页 22 行 ≈ 28.9 磅）。line_rule=exact 时生效，
# 覆盖倍数行距；值为空则按 LINE_SPACING 走倍数。
LINE_RULE = str(SPEC.get("spacing", {}).get("line_rule", "auto") or "auto").lower()
LINE_PT = SPEC.get("spacing", {}).get("line_pt")
# 标题是否加粗（公文体层次标题不加粗，靠字体区分层级）
BOLD_HEADINGS = bool(SPEC.get("bold", {}).get("headings", True))

# 段前段后（磅）。
SPACE_HEADING1_PT = SPEC["spacing"]["h1_before_after_pt"]    # 一级标题段前段后 17 磅
SPACE_HEADING2_PT = SPEC["spacing"]["h2_before_after_pt"]    # 二级标题段前段后 13 磅
SPACE_HEADING3_PT = SPEC["spacing"]["h2_before_after_pt"]    # 三级标题段前段后 13 磅
SPACE_HEADING4_PT = SPEC["spacing"]["h4_before_after_pt"]    # 四/五级标题段前段后 6 磅
SPACE_HEADING6_PT = SPEC["spacing"]["h6_before_after_pt"]    # 六/七级标题段前段后 3 磅
SPACE_BODY_LINES = SPEC["spacing"]["body_before_after_lines"]  # 正文段前段后（行）
# 磅值近似：Word 优先采用 *Lines 行单位，此值仅在行单位不支持时生效，
# 故按「1 行 ≈ 12 磅」粗略换算，保持与 SPACE_BODY_LINES 同向。
SPACE_BODY_PT = round(float(SPACE_BODY_LINES) * 12, 2)

# 缩进。
INDENT_HEADING_CM = 0                # 标题无首行缩进
INDENT_BODY_CHARS = SPEC["indent"]["body_first_line_chars"]   # 正文首行缩进 2 个字符
INDENT_BODY_CM = Cm(0.74)            # 2 个字符≈0.74cm（小四 12 磅宽≈0.37cm*2）

# 文字颜色（读 color.text）：默认 000000；social-media 等 profile 用 333333。
TEXT_COLOR = str(SPEC.get("color", {}).get("text", "000000") or "000000")

# 对齐：读 article-format.yaml 的 alignment 节，字段缺失回落内置默认。
_ALIGN_ENUM = {
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
}

def _apply_line_spacing(pf):
    """按规格设置行距：line_rule=exact 时用固定磅值（公文体行网格），
    否则用倍数行距（默认 1.3 倍）。"""
    if LINE_RULE == "exact" and LINE_PT:
        try:
            pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
            pf.line_spacing = Pt(float(LINE_PT))
            return
        except (TypeError, ValueError):
            pass
    pf.line_spacing = LINE_SPACING


def _spec_align(key, default):
    raw = SPEC.get("alignment", {}).get(key)
    if raw is None:
        return default
    return _ALIGN_ENUM.get(str(raw).lower(), default)

ALIGN_TITLE = _spec_align("title", WD_ALIGN_PARAGRAPH.CENTER)          # 主标题居中
ALIGN_HEADING1 = _spec_align("h1", WD_ALIGN_PARAGRAPH.CENTER)          # 一级标题居中
ALIGN_HEADING_JUSTIFY = _spec_align("h2", WD_ALIGN_PARAGRAPH.JUSTIFY)  # 二~七级标题两端对齐
ALIGN_BODY = _spec_align("body", WD_ALIGN_PARAGRAPH.JUSTIFY)           # 正文两端对齐

# 编号相关。
NUM_START_ID = 100                   # 新建 abstractNum / num 起始 id（避开默认 0-99）
# 标题自动编号专用 id：固定 90，避开正文列表段（abstractNum 100/102/…/112，
# 正文 num 实例由 _max_num_id 动态分配，会自动避开 90）。numId 与 abstractNumId
# 属不同命名空间，互用同值不冲突。
HEADING_ABSTRACT_NUM_ID = 90
HEADING_NUM_ID = 90

# 标号格式说明（表格内文字不缩进）。
TABLE_TEXT_NO_INDENT = True          # 表格内文字不缩进

# 表格跨页规则（v1.5.5）：首行重复标题行（w:tblHeader，2026-09-21 用户指令）与
# 行不拆页（w:cantSplit），两开关吃 article-format.yaml table 节。
TABLE_HEADER_REPEAT = bool(SPEC.get("table", {}).get("header_repeat", True))
TABLE_CANT_SPLIT = bool(SPEC.get("table", {}).get("cant_split", True))

# 正文列表编号定义（七级）：(numFmt, lvlText)。默认即规范七条的
# 1. / 1) / (1) / ① / a. / (a) / i.；profile 可用 list.level_defs 整体替换
# （如公文体用「一、」「（一）」「1.」）。
_LIST_LEVEL_DEFS_BUILTIN = [
    ("decimal", "%1."),                 # 1.
    ("decimal", "%1)"),                 # 1)
    ("decimal", "(%1)"),                # (1)
    ("decimalEnclosedCircle", "%1"),    # ①
    ("lowerLetter", "%1."),             # a.
    ("lowerLetter", "(%1)"),            # (a)
    ("lowerRoman", "%1."),              # i.
]


def _list_level_defs():
    """正文列表七级编号定义。profile 的 list.level_defs 优先，缺省用内置七级。"""
    raw = SPEC.get("list", {}).get("level_defs")
    if isinstance(raw, list) and len(raw) > 0:
        defs = []
        for item in raw[:7]:
            if isinstance(item, dict):
                defs.append((str(item.get("fmt", "decimal")),
                             str(item.get("text", "%1."))))
            else:
                defs.append(("decimal", str(item)))
        while len(defs) < 7:
            defs.append(_LIST_LEVEL_DEFS_BUILTIN[len(defs)])
        return defs
    return list(_LIST_LEVEL_DEFS_BUILTIN)


# 标题多级编号体系：numeric=1/1.1/1.1.1（默认）、chinese=一、/（一）/1.、
# chapter=第一章/1.1、none=不加章节编号（标题即纯文本）。
HEADING_NUMBER_KIND = str(
    SPEC.get("numbering_scheme", {}).get("heading_kind", "numeric") or "numeric")
# 页码格式：dash=- N -（默认）、plain=N、none=不插页码
PAGE_NUMBER_FORMAT = str(
    SPEC.get("footer", {}).get("number_format", "dash") or "dash").lower()


def set_profile(profile):
    """在同一进程内切换文体 profile（重载规格并刷新全部模块常量）。

    脚本 --profile 参数与测试用；import 时已按 ARTICLE_FORMAT_PROFILE
    环境变量初始化，常规流程无需调用。
    """
    global SPEC, PROFILE
    SPEC = load_spec(profile=profile)
    PROFILE = resolve_profile(profile)
    _refresh_spec_constants()
    return SPEC


def _refresh_spec_constants():
    """按当前 SPEC 重算模块级规格常量（set_profile 用）。"""
    g = globals()
    default = load_spec(profile="default")
    merged = SPEC
    for key, value in (
        ("FONT_SIZE_HEADING_TITLE_PT", merged["sizes_pt"]["doc_title"]),
        ("FONT_SIZE_HEADING1_PT", merged["sizes_pt"]["h1"]),
        ("FONT_SIZE_HEADING2_PT", merged["sizes_pt"]["h2"]),
        ("FONT_SIZE_HEADING3_PT", merged["sizes_pt"]["h3"]),
        ("FONT_SIZE_HEADING4_PT", merged["sizes_pt"]["h4"]),
        ("FONT_SIZE_HEADING5_PT", merged["sizes_pt"]["h5"]),
        ("FONT_SIZE_HEADING6_PT", merged["sizes_pt"]["h6"]),
        ("FONT_SIZE_HEADING7_PT", merged["sizes_pt"]["h7"]),
        ("FONT_SIZE_BODY_PT", merged["sizes_pt"]["body"]),
        ("FONT_SIZE_PAGE_NUM_PT", merged["sizes_pt"]["footer"]),
        ("PAGE_WIDTH_CM", float(merged.get("page", {}).get("width_cm", 21.0))),
        ("PAGE_HEIGHT_CM", float(merged.get("page", {}).get("height_cm", 29.7))),
        ("PAGE_MARGIN_CM", float(merged.get("page", {}).get("margin_cm", 2.54))),
        ("FONT_CN", merged["fonts"]["heading"]),
        ("FONT_CN_BODY", merged["fonts"]["body"]),
        ("FONT_EN", merged["fonts"]["western"]),
        ("FONT_CN_BY_LEVEL", merged.get("fonts", {}).get("heading_by_level") or {}),
        ("LINE_SPACING", merged["spacing"]["line"]),
        ("LINE_RULE", str(merged.get("spacing", {}).get("line_rule", "auto") or "auto").lower()),
        ("LINE_PT", merged.get("spacing", {}).get("line_pt")),
        ("BOLD_HEADINGS", bool(merged.get("bold", {}).get("headings", True))),
        ("SPACE_HEADING1_PT", merged["spacing"]["h1_before_after_pt"]),
        ("SPACE_HEADING2_PT", merged["spacing"]["h2_before_after_pt"]),
        ("SPACE_HEADING3_PT", merged["spacing"]["h2_before_after_pt"]),
        ("SPACE_HEADING4_PT", merged["spacing"]["h4_before_after_pt"]),
        ("SPACE_HEADING6_PT", merged["spacing"]["h6_before_after_pt"]),
        ("SPACE_BODY_LINES", merged["spacing"]["body_before_after_lines"]),
        ("SPACE_BODY_PT", round(float(merged["spacing"]["body_before_after_lines"]) * 12, 2)),
        ("INDENT_BODY_CHARS", merged["indent"]["body_first_line_chars"]),
        ("TEXT_COLOR", str(merged.get("color", {}).get("text", "000000") or "000000")),
        ("TABLE_HEADER_REPEAT", bool(merged.get("table", {}).get("header_repeat", True))),
        ("TABLE_CANT_SPLIT", bool(merged.get("table", {}).get("cant_split", True))),
        ("ALIGN_TITLE", _spec_align("title", WD_ALIGN_PARAGRAPH.CENTER)),
        ("ALIGN_HEADING1", _spec_align("h1", WD_ALIGN_PARAGRAPH.CENTER)),
        ("ALIGN_HEADING_JUSTIFY", _spec_align("h2", WD_ALIGN_PARAGRAPH.JUSTIFY)),
        ("ALIGN_BODY", _spec_align("body", WD_ALIGN_PARAGRAPH.JUSTIFY)),
        ("HEADING_NUMBER_KIND", str(merged.get("numbering_scheme", {})
                                    .get("heading_kind", "numeric") or "numeric")),
        ("PAGE_NUMBER_FORMAT", str(merged.get("footer", {})
                                   .get("number_format", "dash") or "dash").lower()),
    ):
        g[key] = value
    return merged


# --------------------------------------------------------------------------- #
# 底层工具：字体 / 样式对象 / 编号                                         #
# --------------------------------------------------------------------------- #

def _set_font(run, cn_font, en_font, size_pt, bold=False):
    """给一个 run 设置中西文字体、字号、加粗。

    中文字体需要设置 w:eastAsia，西文 w:ascii + w:hAnsi。
    size_pt 可为 None，表示不修改字号（保留样式自带字号）。
    """
    run.font.name = en_font                       # w:ascii 与 w:hAnsi
    if size_pt is not None:
        run.font.size = Pt(size_pt)
    run.font.bold = bold
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), en_font)
    rFonts.set(qn("w:hAnsi"), en_font)
    rFonts.set(qn("w:eastAsia"), cn_font)
    rFonts.set(qn("w:cs"), en_font)


def add_rich_runs(par, text, base_bold=False, size_pt=None,
                  cn=None, en=None):
    """把一个段落文本按 `**重点**` 拆成多个 run 写入 par，重点段加粗。

    段落富文本的统一入口（正文段、引文、表格单元格、编号列表共用）。
    此前仅正文段与表格单元格解析 `**`，编号列表整段按纯文本写入，
    导致列表里的 `**已定**` 以字面星号出现在成品文档里。

    三个样式参数缺省为 None 时实时读当前 SPEC（默认参数会在函数定义时
    求值，写死会导致切 profile 后字体字号不更新）。
    """
    if size_pt is None:
        size_pt = FONT_SIZE_BODY_PT
    if cn is None:
        cn = FONT_CN_BODY
    if en is None:
        en = FONT_EN
    parts = re.split(r"(\*\*.*?\*\*)", text)
    for seg in parts:
        if not seg:
            continue
        bold = base_bold
        content = seg
        if seg.startswith("**") and seg.endswith("**") and len(seg) >= 4:
            bold = True
            content = seg[2:-2]
        run = par.add_run(content)
        _set_font(run, cn, en, size_pt, bold=bold)


def _force_black(rPr):
    """把颜色设为规格值（默认 000000），并清除模板继承的 themeColor/themeShade。

    规范未定义颜色时正式文档默认黑；python-docx 默认模板的 Title / Heading
    带蓝色主题色（accent1），不清除会继承出蓝色标题。

    颜色取 article-format.yaml 的 color.text——此前该字段从未被读取，
    一律硬编码 000000，导致 social-media 这类正文用 #333333 的 profile
    配置无效（实测：正文颜色仍是纯黑）。
    """
    color = rPr.find(qn("w:color"))
    if color is None:
        color = OxmlElement("w:color")
        rPr.append(color)
    color.set(qn("w:val"), TEXT_COLOR)
    for attr in ("w:themeColor", "w:themeShade", "w:themeTint"):
        if color.get(qn(attr)) is not None:
            del color.attrib[qn(attr)]


def _set_body_color(style):
    """给正文样式的默认 run 属性设文字颜色（读 color.text）。"""
    rPr = style.element.get_or_add_rPr()
    _force_black(rPr)


def _strip_paragraph_border(pPr):
    """删除段落边框（默认 Title 样式带一条蓝色下边框，规范未定义）。"""
    pBdr = pPr.find(qn("w:pBdr"))
    if pBdr is not None:
        pPr.remove(pBdr)


def _clear_first_line_indent(pPr):
    """彻底清除首行缩进。

    标题基于 Normal，而 Normal 设了 firstLineChars=200；OOXML 中
    firstLineChars 优先级高于 firstLine，只写 firstLine=0 仍会继承 2 字符缩进，
    必须同时把 firstLineChars 归零。
    """
    ind = pPr.find(qn("w:ind"))
    if ind is None:
        ind = OxmlElement("w:ind")
        pPr.append(ind)
    ind.set(qn("w:firstLine"), "0")
    ind.set(qn("w:firstLineChars"), "0")
    ind.set(qn("w:left"), "0")
    ind.set(qn("w:leftChars"), "0")


def _set_spacing(style_or_par, before_pt=None, after_pt=None, line=None):
    """设置段前段后与行距。line 为倍数（如 1.3）。"""
    pf = style_or_par.paragraph_format
    if before_pt is not None:
        pf.space_before = Pt(before_pt)
    if after_pt is not None:
        pf.space_after = Pt(after_pt)
    if line is not None:
        pf.line_spacing = line               # python-docx 支持倍数
        # 明确设置为倍数（MULTIPLE），避免被解释成固定值。
        pPr = style_or_par.paragraph_format.element if hasattr(
            style_or_par.paragraph_format, "element") else None
        if pPr is not None:
            spacing = pPr.find(qn("w:spacing"))
            if spacing is not None:
                spacing.set(qn("w:lineRule"), "auto")


def _set_outline_level(paragraph, level):
    """给段落设置大纲级别（0=正文之外的最高级标题，用于导航窗格）。"""
    pPr = paragraph._p.get_or_add_pPr()
    outlineLvl = pPr.find(qn("w:outlineLvl"))
    if outlineLvl is None:
        outlineLvl = OxmlElement("w:outlineLvl")
        pPr.append(outlineLvl)
    # Word 大纲级别：0 对应 Heading 1（最高），往下递增。
    outlineLvl.set(qn("w:val"), str(level - 1))   # Heading 1 → 0, Heading 2 → 1, ...


def _insert_abstract_num_ordered(numbering_element, abstract_num):
    """按 schema 顺序插入 abstractNum：必须位于所有 w:num 之前（CT_Numbering）。

    numbering.xml 子元素强制顺序为 numPicBullet* → abstractNum* → num*
    → numIdMacAtCleanup?；裸 append 会落到 num 之后，严格校验器（OpenXML SDK /
    OfficeCLI）报 "unexpected child element 'abstractNum'"。
    """
    for child in numbering_element:
        if child.tag in (qn("w:num"), qn("w:numIdMacAtCleanup")):
            child.addprevious(abstract_num)
            return
    numbering_element.append(abstract_num)


# pPr 中必须排在 numPr 之后的元素（ECMA-376 §17.3.1.26，CT_PPrBase 顺序）。
_PPR_AFTER_NUMPR = frozenset((
    qn("w:suppressLineNumbers"), qn("w:pBdr"), qn("w:shd"), qn("w:tabs"),
    qn("w:suppressAutoHyphens"), qn("w:kinsoku"), qn("w:wordWrap"),
    qn("w:overflowPunct"), qn("w:topLinePunct"), qn("w:autoSpaceDE"),
    qn("w:autoSpaceDN"), qn("w:bidi"), qn("w:adjustRightInd"),
    qn("w:snapToGrid"), qn("w:spacing"), qn("w:ind"),
    qn("w:contextualSpacing"), qn("w:mirrorIndents"), qn("w:suppressOverlap"),
    qn("w:jc"), qn("w:textDirection"), qn("w:textAlignment"),
    qn("w:textboxTightWrap"), qn("w:outlineLvl"), qn("w:divId"),
    qn("w:cnfStyle"), qn("w:rPr"), qn("w:sectPr"), qn("w:pPrChange"),
))


def _insert_numpr_ordered(pPr, numPr):
    """按 ECMA-376 顺序插入 numPr（须位于 spacing/ind/jc/outlineLvl 等之前）。"""
    for child in pPr:
        if child.tag in _PPR_AFTER_NUMPR:
            child.addprevious(numPr)
            return
    pPr.append(numPr)


def _add_abstract_num(numbering_part, abstract_id, fmt, level_text):
    """新建一个 w:abstractNum，描述某级自动编号的外观。

    fmt: 编号格式，如 'decimal'（1 2 3）或 'decimal' 但用括号包裹。
    level_text: 本级的编号文本模板，如下拉列表：
        1)  →  在其 lvlText 里写 '%1.' 之外，如需末尾加点，见注释。
    说明：python-docx 的 abstractNum 是空泛的，我们要精确控制每条 lvl 的
    pPr（编号缩进/文本缩进归 0、顶格）与 lvlText（编号与文字空一格）。
    """
    abstractNum = OxmlElement("w:abstractNum")
    abstractNum.set(qn("w:abstractNumId"), str(abstract_id))

    # 只对我们要用的级别（0,1,2 对应列表 1./1)/ (1)）填 full；其余留模板默认。
    lvl = OxmlElement("w:lvl")
    lvl.set(qn("w:ilvl"), "0")
    # start
    start = OxmlElement("w:start"); start.set(qn("w:val"), "1"); lvl.append(start)
    # numFmt
    numFmt = OxmlElement("w:numFmt"); numFmt.set(qn("w:val"), fmt); lvl.append(numFmt)
    # suff —— 编号与文字之间用半角空格（Word 默认是制表符，会造成宽间隙）。
    suff = OxmlElement("w:suff"); suff.set(qn("w:val"), "space"); lvl.append(suff)
    # lvlText —— 编号文本模板
    lvlText = OxmlElement("w:lvlText")
    lvlText.set(qn("w:val"), level_text)
    lvl.append(lvlText)
    # lvlJc
    lvlJc = OxmlElement("w:lvlJc"); lvlJc.set(qn("w:val"), "left"); lvl.append(lvlJc)
    # pPr —— 编号缩进与文本缩进均归 0，整体顶格排版
    pPr = OxmlElement("w:pPr")
    ind = OxmlElement("w:ind")
    ind.set(qn("w:left"), "0")
    ind.set(qn("w:firstLine"), "0")
    pPr.append(ind)
    lvl.append(pPr)
    # rPr(可选) —— 这里不设字体，交给 run 及样式，防止覆盖正文宋体小四。

    abstractNum.append(lvl)
    _insert_abstract_num_ordered(numbering_part.element, abstractNum)
    return abstract_id


def _add_num(numbering_part, abstract_id, num_id, start_override=1):
    """新建一个 w:num 实例，绑定上面的 abstractNum。

    每个列表块使用**独立的 num 实例**（共享同一 abstractNum），并写入
    w:lvlOverride/w:startOverride 强制该实例从 1 重新计数——仅换 numId
    不够：OOXML 规定多个 num 引用同一 abstractNum 时编号会**延续**
    （实测第二个列表块显示 3. 4.，即此坑）。

    start_override=None 时不写覆盖（保留延续行为，本规范不用）。
    """
    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(num_id))
    abstractNumId = OxmlElement("w:abstractNumId")
    abstractNumId.set(qn("w:val"), str(abstract_id))
    num.append(abstractNumId)
    if start_override is not None:
        # 注意子元素顺序：w:abstractNumId 之后才是 w:lvlOverride。
        lvlOverride = OxmlElement("w:lvlOverride")
        lvlOverride.set(qn("w:ilvl"), "0")
        startOverride = OxmlElement("w:startOverride")
        startOverride.set(qn("w:val"), str(start_override))
        lvlOverride.append(startOverride)
        num.append(lvlOverride)
    # 编号会绑定 paragraph 的 numPr，需要保持独立实例。
    numbering_part.element.append(num)
    return num_id


def _max_num_id(numbering_part):
    """返回 numbering.xml 中当前最大的 numId（无则返回 NUM_START_ID-1）。"""
    ids = []
    for num in numbering_part.element.findall(qn("w:num")):
        nid = num.get(qn("w:numId"))
        if nid is not None and nid.isdigit():
            ids.append(int(nid))
    return max(ids) if ids else NUM_START_ID - 1


def _ensure_abstract_nums(doc):
    """确保七级 abstractNum 存在（幂等），返回 {level: abstract_id}。

    编号格式取 _list_level_defs()：默认 profile 为规范七条的
    1./1)/(1)/①/a./(a)/i.；其他文体 profile 可整体替换（如公文体「一、」「（一）」）。
    """
    numbering_part = doc.part.numbering_part
    specs = _list_level_defs()
    existing_abs = {
        ab.get(qn("w:abstractNumId"))
        for ab in numbering_part.element.findall(qn("w:abstractNum"))
    }
    abs_defs = {}
    for idx, (fmt, text) in enumerate(specs, start=1):
        abs_id = NUM_START_ID + (idx - 1) * 2
        if str(abs_id) not in existing_abs:
            _add_abstract_num(numbering_part, abs_id, fmt, text)
        abs_defs[idx] = abs_id
    return abs_defs


def _new_num_for_level(doc, level):
    """为「一个列表块」新建独立 num 实例（计数器从 1 开始）。"""
    numbering_part = doc.part.numbering_part
    abs_defs = _ensure_abstract_nums(doc)
    num_id = _max_num_id(numbering_part) + 1
    _add_num(numbering_part, abs_defs[level], num_id)
    return num_id


def _ensure_numbering(doc):
    """确保 doc 有 numbering part 与七级 abstractNum，返回 {level: abstract_id}。

    仅创建 abstractNum（编号外观定义），不再预建 num 实例——每个列表块
    通过 _new_num_for_level 单独建 num，保证「每块独立从 1 开始」。
    """
    return _ensure_abstract_nums(doc)


# 标题多级编号的 lvlText / numFmt 模板。键为 HEADING_NUMBER_KIND，
# 值为 7 级 (numFmt, lvlText) 列表；%1~%7 为各级计数器占位。
_HEADING_NUMBER_SCHEMES = {
    # 1 / 1.1 / 1.1.1 ……（默认，规范十二条）
    "numeric": [("decimal", "%1")] +
               [("decimal", ".".join(f"%{n}" for n in range(1, i + 2)))
                for i in range(1, 7)],
    # 一、/ （一）/ 1. / (1) / ① —— 党政机关公文 GB/T 9704 层次序数
    "chinese": [
        ("chineseCounting", "%1、"),
        ("chineseCounting", "（%1）"),
        ("decimal", "%1."),
        ("decimal", "（%1）"),
        ("decimalEnclosedCircle", "%1"),
        ("decimal", "%1)"),
        ("lowerLetter", "%1."),
    ],
    # 第一章 / 1.1 / 1.1.1 —— 学位论文、图书章节（二级以下不含章号）
    "chapter": [("chineseCounting", "第%1章"), ("decimal", "%2"),
                ("decimal", "%2.%3"), ("decimal", "%2.%3.%4"),
                ("decimal", "%2.%3.%4.%5"), ("decimal", "%2.%3.%4.%5.%6"),
                ("decimal", "%2.%3.%4.%5.%6.%7")],
    # 一 / 一.一 / 一.一.一 —— 传统中文层级（部分古籍与年鉴）
    "chinese-numeric": [("chineseCounting", "%1")] +
                       [("chineseCounting",
                         ".".join(f"%{n}" for n in range(1, i + 2)))
                        for i in range(1, 7)],
}


def _heading_number_scheme():
    """返回当前 profile 的标题编号 (numFmt, lvlText) 七级列表；none 返回空列表。"""
    kind = HEADING_NUMBER_KIND
    if kind in ("none", "off", ""):
        return []
    return _HEADING_NUMBER_SCHEMES.get(kind, _HEADING_NUMBER_SCHEMES["numeric"])


def _add_heading_multilevel_abstract(numbering_part, abstract_id, max_level=7):
    """新建「标题多级编号」abstractNum，按 profile 的体系生成各级 lvl。

    默认 numeric：1 / 1.1 / … / 1.1.1.1.1.1.1；chinese：一、/（一）/1./（1）/①；
    chapter：第一章 / 1.1 / …。每级 start=1、suff=space（序数与题名空一格）、
    缩进归 0（标题顶格）。
    """
    scheme = _heading_number_scheme()
    abstractNum = OxmlElement("w:abstractNum")
    abstractNum.set(qn("w:abstractNumId"), str(abstract_id))
    multi = OxmlElement("w:multiLevelType")
    multi.set(qn("w:val"), "multilevel")
    abstractNum.append(multi)
    for ilvl in range(min(max_level, len(scheme))):
        num_fmt, lvl_text = scheme[ilvl]
        lvl = OxmlElement("w:lvl")
        lvl.set(qn("w:ilvl"), str(ilvl))
        start = OxmlElement("w:start"); start.set(qn("w:val"), "1"); lvl.append(start)
        numFmt = OxmlElement("w:numFmt")
        numFmt.set(qn("w:val"), num_fmt); lvl.append(numFmt)
        suff = OxmlElement("w:suff"); suff.set(qn("w:val"), "space"); lvl.append(suff)
        lvlText = OxmlElement("w:lvlText")
        lvlText.set(qn("w:val"), lvl_text)
        lvl.append(lvlText)
        lvlJc = OxmlElement("w:lvlJc"); lvlJc.set(qn("w:val"), "left"); lvl.append(lvlJc)
        pPr = OxmlElement("w:pPr")
        ind = OxmlElement("w:ind")
        ind.set(qn("w:left"), "0")
        ind.set(qn("w:firstLine"), "0")
        pPr.append(ind)
        lvl.append(pPr)
        abstractNum.append(lvl)
    _insert_abstract_num_ordered(numbering_part.element, abstractNum)


def _ensure_heading_auto_number(doc, max_level=7):
    """给 Heading 1-7 样式绑定 Word 多级列表编号（标题编号自动重排）。

    样式级绑定（样式 pPr 写 numPr），所有 Heading 段落自动获得编号，
    Word/WPS 中增删章节编号自动重排——源稿不再需要手写编号，md2docx
    渲染标题时同步剥离手写编号前缀，避免「1.1 1.1 实验装置」双重编号。
    幂等：abstractNum / num 已存在则跳过，样式 numPr 重建覆盖。
    """
    numbering_part = doc.part.numbering_part
    element = numbering_part.element
    abs_existing = {
        ab.get(qn("w:abstractNumId"))
        for ab in element.findall(qn("w:abstractNum"))
    }
    if str(HEADING_ABSTRACT_NUM_ID) not in abs_existing:
        _add_heading_multilevel_abstract(
            numbering_part, HEADING_ABSTRACT_NUM_ID, max_level)
    num_existing = {
        num.get(qn("w:numId"))
        for num in element.findall(qn("w:num"))
    }
    if str(HEADING_NUM_ID) not in num_existing:
        num = OxmlElement("w:num")
        num.set(qn("w:numId"), str(HEADING_NUM_ID))
        abstractNumId = OxmlElement("w:abstractNumId")
        abstractNumId.set(qn("w:val"), str(HEADING_ABSTRACT_NUM_ID))
        num.append(abstractNumId)
        element.append(num)
    # Heading 1-7 样式对象绑定 numPr（先删旧再建，保证 ilvl/numId 子元素顺序）
    for lvl in range(1, max_level + 1):
        style = doc.styles[f"Heading {lvl}"]
        pPr = style.element.get_or_add_pPr()
        old = pPr.find(qn("w:numPr"))
        if old is not None:
            pPr.remove(old)
        numPr = OxmlElement("w:numPr")
        ilvl = OxmlElement("w:ilvl"); ilvl.set(qn("w:val"), str(lvl - 1))
        numId = OxmlElement("w:numId"); numId.set(qn("w:val"), str(HEADING_NUM_ID))
        numPr.append(ilvl); numPr.append(numId)
        _insert_numpr_ordered(pPr, numPr)


def add_auto_numbered_list(doc, items, level=1):
    """把 items 渲染为一个 Word 自动编号项列表（每个列表块独立从 1 开始）。

    适用规范第七条：正文标号 1./1)/(1)/①/a./(a)/i.，用程序自动编号，增删自动重排。
    编号缩进与文本缩进均归 0，顶格排版，编号与文字空一格，无首行缩进，
    字体字号行距与正文一致（宋体小四、Times New Roman 数字、两端对齐、
    段前段后 0.1 行、1.3 倍行距）。

    level: 1→'1.' 2→'1)' 3→'(1)' 4→'①' 5→'a.' 6→'(a)' 7→'i.'。
    每次调用视为一个独立列表块，编号从 1 重新开始。
    """
    level = max(1, min(level, 7))
    num_id = _new_num_for_level(doc, level)

    for item in items:
        # 直接创建一段，用 style 但额外附加 numPr。
        p = doc.add_paragraph()
        # 关键：套用正文样式，保证末级归一（宋体小四、两端对齐、1.3 倍行距等）。
        p.style = doc.styles["Normal"]
        _style_body_paragraph(p, first_line_indent=False)
        # 加编号（程序自动编号）。
        # 每级使用独立 abstractNum（100/102/104/…/112），其 lvl 定义在 ilvl=0，
        # 故段落统一引用 ilvl=0；若按 level-1 引用未定义层级，Word 会回退导致同层不递增。
        pPr = p._p.get_or_add_pPr()
        numPr = OxmlElement("w:numPr")
        ilvl = OxmlElement("w:ilvl"); ilvl.set(qn("w:val"), "0")
        numId = OxmlElement("w:numId"); numId.set(qn("w:val"), str(num_id))
        numPr.append(ilvl); numPr.append(numId)
        _insert_numpr_ordered(pPr, numPr)
        # 正文（run）加文字：走富文本入口，`**重点**` 解析为加粗 run。
        add_rich_runs(p, item)
    return doc


# --------------------------------------------------------------------------- #
# 样式套用主体                                                                  #
# --------------------------------------------------------------------------- #

def _set_lines_spacing(pPr, before_lines=None, after_lines=None):
    """按「行」设置段前段后（w:beforeLines / w:afterLines，单位 1/100 行）。

    规范第六条要求正文段前段后各 0.1 行；python-docx 的 space_before 只能按磅
    设置，这里直接写 OOXML 属性，Word/WPS 会优先采用 *Lines 值。

    缺省（None）时读规格 spacing.body_before_after_lines——不能写死 0.1，
    否则 social-media 这类 0.3 行的 profile 会被静默压回 0.1。
    """
    if before_lines is None:
        before_lines = SPACE_BODY_LINES
    if after_lines is None:
        after_lines = SPACE_BODY_LINES
    spacing = pPr.find(qn("w:spacing"))
    if spacing is None:
        spacing = OxmlElement("w:spacing")
        pPr.append(spacing)
    spacing.set(qn("w:beforeLines"), str(int(round(before_lines * 100))))
    spacing.set(qn("w:afterLines"), str(int(round(after_lines * 100))))


def _set_first_line_chars(pPr, chars=2):
    """按「字符」设置首行缩进（w:firstLineChars，单位 1/100 字符）。"""
    ind = pPr.find(qn("w:ind"))
    if ind is None:
        ind = OxmlElement("w:ind")
        pPr.append(ind)
    ind.set(qn("w:firstLineChars"), str(int(round(chars * 100))))


def _style_body_paragraph(par, first_line_indent=True):
    """把一段设为正文外观：两端对齐、首行缩进 2 字符、段前段后 0.1 行、1.3 倍。

    first_line_indent=False 时清除首行缩进（列表项用，规范第七条要求顶格）。
    """
    pf = par.paragraph_format
    par.alignment = ALIGN_BODY
    pf.space_before = Pt(SPACE_BODY_PT)
    pf.space_after = Pt(SPACE_BODY_PT)
    _apply_line_spacing(pf)
    # 精确化：段前段后 0.1 行（覆盖上面的磅近似值）。
    pPr = par._p.get_or_add_pPr()
    _set_lines_spacing(pPr)
    if first_line_indent:
        pf.first_line_indent = INDENT_BODY_CM
        _set_first_line_chars(pPr, INDENT_BODY_CHARS)
    else:
        pf.first_line_indent = Pt(0)
        _set_first_line_chars(pPr, 0)
        ind = pPr.find(qn("w:ind"))
        if ind is not None:
            ind.set(qn("w:firstLine"), "0")


def _disinherit_from_normal(style):
    """剥离样式对正文（Normal）的继承链（v1.5.3 修复）。

    背景：Normal 为落实「正文段前段后 0.1 行」承载行单位属性
    （w:beforeLines/afterLines=10），OOXML 规定行单位优先于磅值——标题样式
    若基于 Normal，自身写入的段前段后磅值（17/13/6/3 磅）会被继承来的行值
    静默顶掉，实际渲染成 0.1 行（测试页目检事故：标题与上下文贴紧）。
    标题样式的全部正式属性（字体/字号/加粗/对齐/段距/行距/缩进）均由本模块
    显式设置、自包含，故可安全剥离继承链；对无 basedOn 的样式幂等。
    """
    el = style.element
    bO = el.find(qn("w:basedOn"))
    if bO is not None:
        el.remove(bO)


def _style_heading(style, level, size_pt, align, space_pt, bold=True,
                   heading_cn=None, heading_en=None):
    """修改一个内置标题样式对象的全部外观。level 用于大纲级别。

    heading_cn / heading_en 缺省为 None 时实时读当前 SPEC——不能用
    默认参数写死 FONT_CN（默认参数在函数定义时求值，切 profile 后不更新）。
    """
    if heading_cn is None:
        heading_cn = FONT_CN
    if heading_en is None:
        heading_en = FONT_EN
    # 段距磅值必须先于任何行单位属性生效：剥离对 Normal 的继承链（见函数注释）
    _disinherit_from_normal(style)
    style.font.name = heading_en
    style.font.size = Pt(size_pt)
    style.font.bold = bold
    # 默认模板 Heading 4/6/7 等自带斜体，规范要求标题正体，显式关闭。
    style.font.italic = False
    rPr = style.element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), heading_en)
    rFonts.set(qn("w:hAnsi"), heading_en)
    rFonts.set(qn("w:eastAsia"), heading_cn)
    rFonts.set(qn("w:cs"), heading_en)
    # 规范未定义标题颜色 → 强制黑色，清除默认模板的蓝色主题色。
    _force_black(rPr)
    # 对齐
    style.paragraph_format.alignment = align
    style.paragraph_format.space_before = Pt(space_pt)
    style.paragraph_format.space_after = Pt(space_pt)
    _apply_line_spacing(style.paragraph_format)
    # 标题无首行缩进（必须清 firstLineChars，否则继承 Normal 的 2 字符缩进）
    style.paragraph_format.first_line_indent = Pt(0)
    # 大纲级别：Heading 1→0, Heading 2→1, Heading 3→2
    pPr = style.element.get_or_add_pPr()
    _strip_paragraph_border(pPr)
    _clear_first_line_indent(pPr)
    outlineLvl = pPr.find(qn("w:outlineLvl"))
    if outlineLvl is None:
        outlineLvl = OxmlElement("w:outlineLvl")
        pPr.append(outlineLvl)
    outlineLvl.set(qn("w:val"), str(level - 1))
    # 标题与下段同页（v1.5.5）：防标题孤立在页底、后续表格被分页隔开
    # （渲染验收事故：页底只有标题+空表头的孤行，数据行整体被推到下一页）。
    style.paragraph_format.keep_with_next = True


def _style_title_style(doc):
    """主标题样式（规范一）：黑体小二 18 磅、加粗、居中、不进入导航目录。

    必须清掉默认模板 Title 样式的蓝色主题色与蓝色下边框，否则正式文档会
    出现蓝字 + 蓝色横线（规范未定义颜色与边框）。
    """
    style = doc.styles["Title"]
    # 主标题段后 17 磅同样不得被 Normal 的行单位值顶替（v1.5.3）
    _disinherit_from_normal(style)
    style.font.name = FONT_EN
    style.font.size = Pt(FONT_SIZE_HEADING_TITLE_PT)
    style.font.bold = True
    rPr = style.element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), FONT_EN)
    rFonts.set(qn("w:hAnsi"), FONT_EN)
    rFonts.set(qn("w:eastAsia"), FONT_CN)
    rFonts.set(qn("w:cs"), FONT_EN)
    _force_black(rPr)
    pf = style.paragraph_format
    pf.alignment = ALIGN_TITLE
    pf.first_line_indent = Pt(0)
    _apply_line_spacing(pf)
    pf.space_before = Pt(0)
    pf.space_after = Pt(SPACE_HEADING1_PT)
    pPr = style.element.get_or_add_pPr()
    _strip_paragraph_border(pPr)
    _clear_first_line_indent(pPr)
    # 主标题不设大纲级别：显式写 outlineLvl=9（body text）以防继承进目录。
    outlineLvl = pPr.find(qn("w:outlineLvl"))
    if outlineLvl is None:
        outlineLvl = OxmlElement("w:outlineLvl")
        pPr.append(outlineLvl)
    outlineLvl.set(qn("w:val"), "9")


def _set_table_cross_page(doc):
    """表格跨页规则（v1.5.5）：首行重复标题行 + 数据行不拆页。

    ①首行加 w:tblHeader：表格跨页时表头在每页自动重复（2026-09-21 用户指令
    「表格默认冻结表头」的 docx 等价实现，本机 v1.8 特性，10-09 对齐时丢失后
    回归移植）；②每行加 w:cantSplit：行内容不跨页拆断，防单元格文字被页边界
    切成两半（同类问题的行级修法）。两开关均可由 article-format.yaml 的
    table.header_repeat / table.cant_split 关闭。幂等：已有对应元素的跳过；
    tblHeader 借 insert_element_before 按 ECMA-376 的 w:trPr 子元素顺序落位，
    避免严格解析器（officecli validate）判 schema 错序。
    """
    for table in doc.tables:
        if not len(table.rows):
            continue
        if TABLE_HEADER_REPEAT:
            trPr = table.rows[0]._tr.get_or_add_trPr()
            if trPr.find(qn("w:tblHeader")) is None:
                trPr.insert_element_before(
                    OxmlElement("w:tblHeader"),
                    "w:tblCellSpacing", "w:jc", "w:hidden",
                    "w:ins", "w:del", "w:trPrChange")
            # 表头行与下一行同页（v1.5.5）：防表头孤立在页底、数据行整体
            # 被推到下一页（渲染验收事故：页底只见空表头）。
            for c in table.rows[0].cells:
                for p in c.paragraphs:
                    p.paragraph_format.keep_with_next = True
        if TABLE_CANT_SPLIT:
            for row in table.rows:
                trPr = row._tr.get_or_add_trPr()
                if trPr.find(qn("w:cantSplit")) is None:
                    # cantSplit 在 CT_TrPr 序列中位于 tblHeader 之前。
                    trPr.insert_element_before(
                        OxmlElement("w:cantSplit"),
                        "w:tblHeader", "w:tblCellSpacing", "w:jc", "w:hidden",
                        "w:ins", "w:del", "w:trPrChange")
    return doc


def apply_article_style(doc):
    """对整篇文档套用排版规范十三条规定。返回 doc（同对象）。

    幂等：可重复调用。适合 md2docx.py 生成骨架后调用，也适合对已有 docx
    重新套样式。
    """
    # ---- 正文 Normal ---- #
    normal = doc.styles["Normal"]
    normal.font.name = FONT_EN
    normal.font.size = Pt(FONT_SIZE_BODY_PT)
    rPr = normal.element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), FONT_EN)
    rFonts.set(qn("w:hAnsi"), FONT_EN)
    rFonts.set(qn("w:eastAsia"), FONT_CN_BODY)
    rFonts.set(qn("w:cs"), FONT_EN)
    normal.paragraph_format.alignment = ALIGN_BODY
    normal.paragraph_format.space_before = Pt(SPACE_BODY_PT)
    normal.paragraph_format.space_after = Pt(SPACE_BODY_PT)
    _apply_line_spacing(normal.paragraph_format)
    normal.paragraph_format.first_line_indent = INDENT_BODY_CM
    # 精确化：段前段后 0.1 行、首行缩进 2 字符（覆盖上面的磅/cm 近似值）。
    normal_pPr = normal.element.get_or_add_pPr()
    _set_lines_spacing(normal_pPr)
    _set_first_line_chars(normal_pPr, INDENT_BODY_CHARS)
    # 正文文字颜色（color.text）：默认黑色；social-media 等 profile 用 #333333
    _set_body_color(normal)

    # ---- 标题样式 ---- #
    heading_specs = {
        # (样式名, 级别, 字号, 对齐, 段前段后磅)
        "Heading 1": (1, FONT_SIZE_HEADING1_PT, ALIGN_HEADING1, SPACE_HEADING1_PT),
        "Heading 2": (2, FONT_SIZE_HEADING2_PT, ALIGN_HEADING_JUSTIFY, SPACE_HEADING2_PT),
        "Heading 3": (3, FONT_SIZE_HEADING3_PT, ALIGN_HEADING_JUSTIFY, SPACE_HEADING3_PT),
        "Heading 4": (4, FONT_SIZE_HEADING4_PT, ALIGN_HEADING_JUSTIFY, SPACE_HEADING4_PT),
        "Heading 5": (5, FONT_SIZE_HEADING5_PT, ALIGN_HEADING_JUSTIFY, SPACE_HEADING4_PT),
        "Heading 6": (6, FONT_SIZE_HEADING6_PT, ALIGN_HEADING_JUSTIFY, SPACE_HEADING6_PT),
        "Heading 7": (7, FONT_SIZE_HEADING7_PT, ALIGN_HEADING_JUSTIFY, SPACE_HEADING6_PT),
    }
    for name, (lvl, size, align, space) in heading_specs.items():
        _style_heading(doc.styles[name], lvl, size, align, space,
                       bold=BOLD_HEADINGS,
                       heading_cn=_heading_font_for_level(lvl))

    # ---- 主标题 Title（规范一：黑体小二 18 磅、加粗、居中、不进目录） ---- #
    _style_title_style(doc)

    # ---- 表格跨页规则（首行重复标题行 + 行不拆页，v1.5.5） ---- #
    _set_table_cross_page(doc)

    # ---- 段前段后：标题各自独立（在 _style_heading 里已设），再补首行 0。 ---- #

    # ---- 页面（纸型 A4 / 页边距 2.54cm，读 article-format.yaml page 节） ---- #
    _apply_page_setup(doc)

    # ---- 页脚页码 ---- #
    _set_page_number_footer(doc)

    # ---- 保证 numbering 存在（供 add_auto_numbered_list 使用） ---- #
    _ensure_numbering(doc)

    # ---- 标题自动多级编号（规范十二 heading_auto_number，yaml 开关） ---- #
    if SPEC.get("numbering_scheme", {}).get("heading_auto_number", True):
        _ensure_heading_auto_number(doc)
    return doc


def _apply_page_setup(doc):
    """把每一节的纸型与页边距设为规格值（默认 A4 + 四边 2.54cm）。

    纸型属排版规格：不改会随 python-docx 默认模板落到 Letter，
    打印与归档（中文办公场景）不符。

    页边距支持两种写法：`margin_cm` 单值（四边同距）或
    `margin_top_cm / margin_bottom_cm / margin_left_cm / margin_right_cm`
    分边覆盖（公文 GB/T 9704 用上 3.7 / 下 3.5 / 左 2.8 / 右 2.6）。
    """
    page = SPEC.get("page", {})
    base = float(page.get("margin_cm", 2.54))

    def _edge(key):
        raw = page.get(key)
        try:
            return float(raw) if raw is not None else base
        except (TypeError, ValueError):
            return base

    top = _edge("margin_top_cm")
    bottom = _edge("margin_bottom_cm")
    left = _edge("margin_left_cm")
    right = _edge("margin_right_cm")
    for section in doc.sections:
        section.page_width = Cm(PAGE_WIDTH_CM)
        section.page_height = Cm(PAGE_HEIGHT_CM)
        section.top_margin = Cm(top)
        section.bottom_margin = Cm(bottom)
        section.left_margin = Cm(left)
        section.right_margin = Cm(right)
    return doc


def _set_page_number_footer(doc):
    """在页脚底端居中插入自动页码字段。字体宋体小四（12 磅，读规格）黑色。

    页码显示格式「- N -」（v1.5.4 用户指令）：PAGE 域左侧「- 」、右侧「 -」。
    """
    section = doc.sections[0]
    footer = section.footer
    footer.is_linked_to_previous = False
    # 清空默认 footer（可能有空段落）
    for para in list(footer.paragraphs):
        p = para
        break
    # 用第一个段落作为页码段落
    par = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    # 先清空该段内容
    for child in list(par._element):
        par._element.remove(child)
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    # 页码前后缀：dash=- N -（默认，v1.5.4）；plain=N；none=不插页码
    if PAGE_NUMBER_FORMAT in ("none", "off"):
        return doc
    prefix = "- " if PAGE_NUMBER_FORMAT == "dash" else ""
    suffix = " -" if PAGE_NUMBER_FORMAT == "dash" else ""
    if prefix:
        pre = par.add_run(prefix)
        _set_font(pre, FONT_CN_BODY, FONT_EN, FONT_SIZE_PAGE_NUM_PT, bold=False)
    # 插入分页域：PAGE
    run = par.add_run()
    _set_font(run, FONT_CN_BODY, FONT_EN, FONT_SIZE_PAGE_NUM_PT, bold=False)
    fldChar1 = OxmlElement("w:fldChar"); fldChar1.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText"); instrText.set(qn("xml:space"), "preserve")
    instrText.text = "PAGE"
    fldChar2 = OxmlElement("w:fldChar"); fldChar2.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t"); t.text = "1"
    fldChar3 = OxmlElement("w:fldChar"); fldChar3.set(qn("w:fldCharType"), "end")
    run._element.append(fldChar1)
    run._element.append(instrText)
    run._element.append(fldChar2)
    run._element.append(t)
    run._element.append(fldChar3)
    # 后缀「 -」（v1.5.4）
    if suffix:
        post = par.add_run(suffix)
        _set_font(post, FONT_CN_BODY, FONT_EN, FONT_SIZE_PAGE_NUM_PT, bold=False)


# --------------------------------------------------------------------------- #
# 独立运行入口：对现有 docx 套用样式                                        #
# --------------------------------------------------------------------------- #

def main(argv=None):
    import sys
    args = list(sys.argv[1:] if argv is None else argv)
    profile = None
    rest = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--profile", "-p") and i + 1 < len(args):
            profile = args[i + 1]
            i += 2
            continue
        if a.startswith("--profile="):
            profile = a.split("=", 1)[1]
            i += 1
            continue
        if a in ("--list-profiles",):
            from spec_loader import list_profiles
            for name in list_profiles():
                print(name)
            return 0
        rest.append(a)
        i += 1

    if len(rest) < 2:
        sys.stderr.write(
            __doc__ + "\n用法: python article_style.py <in.docx> <out.docx> "
            "[--profile <文体>]\n")
        return 2
    in_path, out_path = rest[0], rest[1]
    if profile:
        set_profile(profile)
    doc = Document(in_path)
    apply_article_style(doc)
    doc.save(out_path)
    print(f"已套用文章排版规范（profile={PROFILE}） → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
