# -*- coding: utf-8 -*-
"""md2docx.py — 把 Markdown 文章骨架转为符合排版规范的 docx。

规范第十三条：正式文章、制度、报告等一律经本脚本生成骨架 + article_style.py
套用全部样式（含程序自动编号、标号零缩进与左侧导航目录）。

支持的 Markdown 子集（面向文章类骨架，够用即可，不做全 MD 方言）：
    # 文档主标题（Title 样式：居中、不进目录、不参与章节编号）
    ## 一级标题（对应 Heading 1，如「1 绪论」；也可省略前缀直接写「1 绪论」）
    ### 二级标题（对应 Heading 2，如「1.1 实验装置」）
    #### 三级标题（对应 Heading 3，如「1.1.1 参数校正」）
    层级以数字编号段数为准（1 段→H1、2 段→H2 …… 7 段→H7），`#` 前缀数
    不参与定级（`## 1.1 实验装置` 与 `### 1.1 实验装置` 同为二级）；无编号的
    `## `~`####### ` 行按「# 数 - 1」兜底定级。
    行首日期形态（如 `09.17 期数据` / `2026.10.08 上新`）不按标题识别，
    自动落为正文段，不挂章节编号（防日期与数字编号同构的误判）。
    普通段落（首行缩进 2 字符，两端对齐，宋体小四；`**重点**` 渲染为加粗）
    > 重点文字（加粗，首行缩进 2 字符）
    - 条目（正文标号，Word 程序自动编号，每个列表块独立从 1 开始；
      `**重点**` 同样渲染为加粗）
      七级形式依层级：1. / 1) / (1) / ① / a. / (a) / i.（嵌套行首不留空格）
    | 表头 | 表头 |
    | --- | --- |
    | 单元格 | 单元格 |      → 表格（Table Grid，表头加粗、无底色、无缩进）
    单独一行 `---`/`***`/`___` → 分隔横线；成对 ``` / ~~~ 围栏 → 原样代码段
    （块内不解析任何 Markdown 语法）；单独一行 `[[PAGEBREAK]]` → 硬分页符。

主标题（来自 `# ` 行或 --title 参数）单独用「Title」样式，不设大纲级别，
故不进入导航目录（规范：主标题不套用、不进入目录树）。

安全性：Markdown 内容一律从标准输入（stdin）读取，不读取任何命令行指定的
文件；输出路径相对基准目录（ARTICLE_OUT_DIR 或当前工作目录）解析，保留子目录
但拒绝 `..` 与逃出基线的绝对路径，杜绝路径穿越。

用法（内容走 stdin）：
    python md2docx.py out.docx --title "主标题" < 文章.md
    python md2docx.py out.docx < 文章.md
"""

import sys
import re
import os
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from article_style import (
    apply_article_style,
    add_auto_numbered_list,
    add_rich_runs,
    _set_font,
    _clear_first_line_indent,
    _style_body_paragraph,
)
import article_style as _as


def _font_h():
    """标题中文字体（实时读规格，随 profile 切换）。"""
    return _as.FONT_CN


def _font_b():
    """正文中文字体（实时读规格）。"""
    return _as.FONT_CN_BODY


def _font_w():
    """西文字体（实时读规格）。"""
    return _as.FONT_EN


def _size_title():
    """主标题字号（实时读规格）。"""
    return _as.FONT_SIZE_HEADING_TITLE_PT


def _bold_headings():
    """标题是否加粗（公文体层级标题不加粗）。"""
    return _as.BOLD_HEADINGS


def _live_spec():
    """取当前生效规格（随 article_style.set_profile 联动，不在 import 时固化）。

    此前模块级 _SPEC 在 import 时求值，导致同一进程切 profile 后
    md2docx 仍按旧规格生成骨架（标题层级上限、编号剥离、表格外观全不更新）。
    """
    return _as.SPEC


def max_heading_level():
    return int(_live_spec()["numbering_scheme"].get("heading_levels", 7))


def heading_auto_number():
    return bool(_live_spec()["numbering_scheme"].get("heading_auto_number", True))


def heading_gap_check():
    return str(_live_spec()["numbering_scheme"].get("heading_gap_check", "error")).lower()


def _table_spec():
    return _live_spec().get("table", {})


# 输出基准目录：优先取环境变量 ARTICLE_OUT_DIR，否则取当前工作目录。
# 这样脚本可被复制到任意项目使用，不再锁死到自身所在目录。
BASE = os.environ.get("ARTICLE_OUT_DIR") or os.getcwd()


def _resolve_out(filename):
    """把输出文件名解析为绝对路径，保留子目录、拒绝路径穿越。

    历史行为是只取 basename 强制落 cwd（v2.1 及之前），目的是杜绝路径穿越，
    但副作用是 `sub/out.docx` 被静默改到 `./out.docx`，脚本化调用会以为产物
    在子目录里、实际找不到。现在改为：子目录照常尊重，只拦截逃出 BASE 的路径
    （`..` 或绝对路径）。这样既保住防穿越，也不再有静默改道。
    """
    raw = str(filename)
    if os.path.isabs(raw):
        # 绝对路径：仅允许落在 BASE 之内
        target = os.path.abspath(raw)
        base_abs = os.path.abspath(BASE)
        try:
            inside = os.path.commonpath([target, base_abs]) == base_abs
        except ValueError:            # Windows 跨盘符
            inside = False
        if not inside:
            raise ValueError(
                f"输出路径必须位于输出目录内（BASE={base_abs}）：{target}\n"
                "如需写到别处，请改设 ARTICLE_OUT_DIR 或先 cd 到目标目录。")
        os.makedirs(os.path.dirname(target) or base_abs, exist_ok=True)
        return target
    # 相对路径：相对 BASE 解析后仍需留在 BASE 内（拦截 ../）
    target = os.path.abspath(os.path.join(BASE, raw))
    base_abs = os.path.abspath(BASE)
    try:
        inside = os.path.commonpath([target, base_abs]) == base_abs
    except ValueError:
        inside = False
    if not inside:
        raise ValueError(
            f"输出路径逃出输出目录（BASE={base_abs}）：{raw}\n"
            "可用 ./产物.docx 或 子目录/产物.docx。")
    os.makedirs(os.path.dirname(target) or base_abs, exist_ok=True)
    return target


# --------------------------------------------------------------------------- #
# 段内富文本解析：处理 **加粗**（统一走 article_style.add_rich_runs）             #
# --------------------------------------------------------------------------- #

def _body_paragraph(doc, text, bold=False):
    """新增一个正文段（两端对齐、首行缩进 2 字符、1.3 倍行距、宋体小四）。"""
    par = doc.add_paragraph()
    add_rich_runs(par, text, base_bold=bold)
    return par


# 源稿手写标题编号前缀：数字式（1 / 1.1）与中文式（一、/ （一）/ 第一章）。
# 剥离后编号交由 Word 自动多级编号显示，避免「1.1 1.1 实验装置」双重编号。
_NUM_PREFIX_RE = re.compile(r"^(\d+(?:\.\d+){0,6})\s+(.+)$")
_CN_PREFIX_PATTERNS = (
    re.compile(r"^第[一二三四五六七八九十百零〇\d]+[章节篇部分]\s*(.+)$"),
    re.compile(r"^[一二三四五六七八九十百零〇]+[、.．]\s*(.+)$"),
    re.compile(r"^[（(][一二三四五六七八九十百零〇]+[）)]\s*(.+)$"),
    re.compile(r"^[（(]\d+[）)]\s*(.+)$"),
    re.compile(r"^[①-⑳]\s*(.+)$"),
)


def _strip_heading_prefix(text):
    """剥离行首手写章节编号，返回纯题名。识别不了原样返回。"""
    m = _NUM_PREFIX_RE.match(text)
    if m and not _is_date_like_number(m.group(1)):
        return m.group(2)
    for pat in _CN_PREFIX_PATTERNS:
        m = pat.match(text)
        if m:
            return m.group(1).strip()
    return text


_CN_DIGITS = "一二三四五六七八九十百零〇"
# 中文式章节标题形态：只认「一、」「（一）」「第X章/篇」「第X节」。
# 刻意不含「(1)」「①」这类——它们在正文里是列举标号，不是章节标题
# （实测事故：thesis profile 下正文列举「(1) 三级条目」被误判成三级标题，
#  触发 heading_gap_check 跳级报错，整篇转换中止）。
_CN_LEVEL_PATTERNS = (
    (re.compile(rf"^第[{_CN_DIGITS}\d]+[章篇]\s*\S"), 1),
    (re.compile(rf"^第[{_CN_DIGITS}\d]+[节]\s*\S"), 2),
    (re.compile(rf"^[{_CN_DIGITS}]+、\s*\S"), 1),
    (re.compile(rf"^[（(][{_CN_DIGITS}]+[）)]\s*\S"), 2),
)


def _cn_heading_level(text):
    """中文/公文体编号形态 → 标题层级（1~4）；不匹配返回 0。

    只在 profile 声明 heading_kind 为中文体系时启用（见 _heading_cn_enabled），
    避免通用文章里「一、」这类正文列举被误判为标题。
    """
    if not _heading_cn_enabled():
        return 0
    stripped = text.strip()
    for pat, level in _CN_LEVEL_PATTERNS:
        if pat.match(stripped):
            return level
    return 0


def _heading_cn_enabled():
    """当前 profile 是否启用中文式章节编号（公文体、法律文书等）。"""
    kind = str(_live_spec().get("numbering_scheme", {})
               .get("heading_kind", "numeric") or "numeric")
    return kind in ("chinese", "chapter", "chinese-numeric")


def _heading(doc, text, level):
    """按层级标题列出对应内置 Heading 样式（1-7 级，左侧导航由大纲级别驱动）。

    heading_auto_number 开启时剥离源稿手写编号前缀（数字式与中文式都剥），
    编号由 Word 自动多级编号显示（增删章节自动重排），避免双重编号；
    关闭时保留原文本（历史行为）。
    """
    level = max(1, min(level, max_heading_level()))
    if heading_auto_number():
        text = _strip_heading_prefix(text)
    par = doc.add_paragraph(text, style=f"Heading {level}")
    cn = _as._heading_font_for_level(level)
    for run in par.runs:
        _set_font(run, cn, _font_w(), None, bold=_bold_headings())
    return par


def _title(doc, text):
    """文档主标题：用 Title 样式，不设大纲级别（不进入导航目录）。"""
    try:
        par = doc.add_paragraph(text, style="Title")
    except KeyError:
        par = doc.add_paragraph()
        if par.runs:
            par.runs[0].text = text
        else:
            par.add_run(text)
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in par.runs:
        _set_font(run, _font_h(), _font_w(), _size_title(), bold=_bold_headings())
    return par


def _is_date_like_number(num_text):
    """判断「编号」文本是否为日期形态（月.日 / 年.月.日）。

    标题定级按数字编号段数（`1.1`→二级），而 `09.17`、`2026.10.08` 这类日期
    在形态上与章节编号同构——正文段行首的日期会被误挂二级标题与自动编号
    （实测事故：以「09.17 期…」开头的分析段被判为二级标题并挂上章节编号）。
    这里只拦截「明确日期形态」，不扩大误伤面：

    ① 首段为 4 位数字（年份）：2026.10.08 / 2026.9；
    ② 任一段带前导零：09.17 / 10.08 / 09——章节编号不写前导零。

    两段均无前导零的（如 9.17）与章节编号无法从形态区分，不在此拦截；
    此类行如需作为标题，显式加 `#` 前缀即可（`#` 行有独立兜底逻辑）。
    """
    parts = num_text.split(".")
    if len(parts[0]) == 4 and parts[0].isdigit():
        return True
    return any(len(seg) > 1 and seg.startswith("0") for seg in parts)


# --------------------------------------------------------------------------- #
# Markdown 表格                                                                 #
# --------------------------------------------------------------------------- #

def _is_table_line(line):
    s = line.strip()
    return s.startswith("|") and s.endswith("|")


def _split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_separator_row(cells):
    return all(re.match(r"^:?-{3,}:?$", c or "") for c in cells)


_SHADING_WARNED = False


def _apply_three_line_borders(table):
    """把表格改为三线表：只留顶线、栏目线（表头下）、底线，无竖线与内横线。

    学术论文与学位论文的标准表形（三线表）；线宽按惯例顶底 1.5 磅、
    栏目线 0.75 磅（GB/T 7713.2 与各高校学位论文要求通用口径）。
    由 article-format.yaml 的 table.style=three-line 触发。
    """
    tbl_pr = table._tbl.tblPr
    old = tbl_pr.find(qn("w:tblBorders"))
    if old is not None:
        tbl_pr.remove(old)
    borders = OxmlElement("w:tblBorders")
    # 顶线与底线：single 1.5 磅（sz 为 1/8 磅，12 = 1.5 磅）
    for tag in ("w:top", "w:bottom"):
        el = OxmlElement(tag)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "12")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "000000")
        borders.append(el)
    # 左右与内部横竖线：none
    for tag in ("w:left", "w:right", "w:insideH", "w:insideV"):
        el = OxmlElement(tag)
        el.set(qn("w:val"), "none")
        el.set(qn("w:sz"), "0")
        el.set(qn("w:space"), "0")
        borders.append(el)
    tbl_pr.append(borders)

    # 栏目线：表头行的下边框 0.75 磅（sz 6）
    if len(table.rows) > 0:
        for cell in table.rows[0].cells:
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_borders = tc_pr.find(qn("w:tcBorders"))
            if tc_borders is None:
                tc_borders = OxmlElement("w:tcBorders")
                tc_pr.append(tc_borders)
            bottom = OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "6")
            bottom.set(qn("w:space"), "0")
            bottom.set(qn("w:color"), "000000")
            tc_borders.append(bottom)


def _add_table(doc, rows):
    """rows 为二维列表，[0] 为表头。

    外观读 article-format.yaml 的 table 节（规范九：宋体小四、表头加粗、
    无底色、无缩进、1.3 倍行距）。单元格段落显式左对齐＋缩进清零，不依赖
    样式继承——正文 Normal 为两端对齐且首行缩进 2 字符，窄列两端对齐会
    拉大字距、继承缩进会让单元格文字不齐（均为已踩过的坑）。
    """
    global _SHADING_WARNED
    if not rows:
        return
    tbl = _table_spec()
    table_shading = bool(tbl.get("shading", False))
    table_first_line_indent = bool(tbl.get("first_line_indent", False))
    table_line_spacing = float(tbl.get("line_spacing", 1.3))
    table_header_bold = bool(tbl.get("header_bold", True))
    table_font_size = float(tbl.get("font_size_pt", 12))
    if (table_shading or table_first_line_indent) and not _SHADING_WARNED:
        sys.stderr.write(
            "[md2docx] 提示：规范表格为无底色、不缩进（规则九），table 节中 "
            "shading=true / first_line_indent=true 不受支持、已按规范处理。\n")
        _SHADING_WARNED = True
    ncols = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=ncols)
    try:
        table.style = "Table Grid"
    except KeyError:
        pass
    for i, row in enumerate(rows):
        for j in range(ncols):
            cell = table.cell(i, j)
            par = cell.paragraphs[0]
            # 清掉段落残留 run（cell.text 赋值会留一个未设字号的空 run）
            for r in list(par.runs):
                r._element.getparent().remove(r._element)
            pPr = par._p.get_or_add_pPr()
            _clear_first_line_indent(pPr)          # 不缩进（firstLineChars 一并清零）
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
            par.paragraph_format.line_spacing = table_line_spacing
            text = row[j] if j < len(row) else ""
            add_rich_runs(par, text, base_bold=(i == 0) and table_header_bold,
                          size_pt=table_font_size)
    # 三线表（学术/学位论文）：table.style=three-line 时改表格边框
    if str(tbl.get("style", "")).lower() in ("three-line", "three_line", "三线表"):
        _apply_three_line_borders(table)
    return table


# --------------------------------------------------------------------------- #
# 分隔线、代码围栏与硬分页（2026-10-09 与 adc-standards 仓对齐时按本机 v1.8 移植）#
# --------------------------------------------------------------------------- #

# 分隔线：单独一行三个及以上 -、* 或 _（可含空格）；代码围栏：行首三个及以上
# 反引号或波浪号（可带语言标注）；硬分页：单独一行 [[PAGEBREAK]]。
_HR_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
_PAGEBREAK_RE = re.compile(r"\[\[\s*PAGEBREAK\s*\]\]", re.IGNORECASE)


def _add_hr(doc):
    """分隔线：空段 + 段落下边框，视觉上一条横线，不留字面字符。"""
    par = doc.add_paragraph()
    _style_body_paragraph(par, first_line_indent=False)
    pPr = par._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "auto")
    pBdr.append(bottom)
    # pBdr 须按 ECMA-376 顺序插位（numPr 之后、shd/spacing 之前），append 会违规
    pPr.insert_element_before(
        pBdr, "w:shd", "w:tabs", "w:suppressAutoHyphens", "w:kinsoku",
        "w:wordWrap", "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE",
        "w:autoSpaceDN", "w:bidi", "w:adjustRightInd", "w:snapToGrid",
        "w:spacing", "w:ind", "w:contextualSpacing", "w:mirrorIndents",
        "w:suppressOverlap", "w:jc", "w:textDirection", "w:textAlignment",
        "w:textboxTightWrap", "w:outlineLvl", "w:divId", "w:cnfStyle",
        "w:rPr", "w:sectPr", "w:pPrChange")
    return par


def _add_code_block(doc, lines):
    """代码围栏块：逐行按字面输出（等宽 Consolas），块内不解析任何语法。"""
    for text in lines:
        par = doc.add_paragraph()
        par.style = doc.styles["Normal"]
        _style_body_paragraph(par, first_line_indent=False)
        run = par.add_run(text)
        _set_font(run, _font_b(), "Consolas", _as.FONT_SIZE_BODY_PT, bold=False)
    return doc


# --------------------------------------------------------------------------- #
# 解析全文                                                                     #
# --------------------------------------------------------------------------- #

def parse_markdown(md_text):
    """把 md 文本解析成结构化指令。返回 list[dict]。"""
    lines = md_text.splitlines()
    out = []
    i = 0
    pending_list = []

    def flush_list():
        nonlocal pending_list
        if pending_list:
            out.append({"type": "list", "items": pending_list})
            pending_list = []

    while i < len(lines):
        raw = lines[i]
        line = raw.strip()

        # 代码围栏：整块按字面收集，块内不再解析任何 Markdown 语法
        m_fence = _FENCE_RE.match(raw)
        if m_fence:
            flush_list()
            fence = m_fence.group(1)
            marker_char = fence[0]
            body = []
            i += 1
            while i < len(lines):
                m_close = _FENCE_RE.match(lines[i])
                if (m_close and m_close.group(1)[0] == marker_char
                        and len(m_close.group(1)) >= len(fence)
                        and not m_close.group(2).strip()):
                    i += 1
                    break
                body.append(lines[i])
                i += 1
            out.append({"type": "code", "lines": body})
            continue

        # 分隔线：单独一行 --- / *** / ___，输出横线而非字面文本
        if _HR_RE.match(line):
            flush_list()
            out.append({"type": "hr"})
            i += 1
            continue

        if _is_table_line(line) and i + 1 < len(lines) and \
                _is_separator_row(_split_row(lines[i + 1].strip())):
            flush_list()
            rows = [_split_row(line)]
            i += 2
            while i < len(lines) and _is_table_line(lines[i].strip()) and \
                    not _is_separator_row(_split_row(lines[i].strip())):
                rows.append(_split_row(lines[i].strip()))
                i += 1
            out.append({"type": "table", "rows": rows})
            continue

        # 标题：层级以「数字编号段数」为准（1 段→H1、2 段→H2 …… 7 段→H7），
        # `#` 前缀数不参与定级（`## 1 绪论` 与 `1 绪论` 同为一级）。
        #   ① 单个 `# ` 行且无编号 → 文档主标题（Title 样式，不进目录、不编号）
        #   ② `#`~`########` 行带编号（`## 1 绪论` / `### 1.1 实验装置`）→ 按段数定级
        #   ③ 编号独立成行（`1 绪论` / `1.1 实验装置`，无 `#`）→ 同上
        #      （编号为日期形态时不作编号处理，见 _is_date_like_number）
        #   ④ 中文式编号（`一、` / `（一）` / `第一章`）→ 按形式定级，供公文体 profile
        m_level = max_heading_level()
        num_re = rf"^(\d+(?:\.\d+){{0,{m_level - 1}}})\s+(.+)$"
        m = re.match(rf"^(#{{1,{m_level + 1}}})\s+(.*)$", line)
        if m:
            flush_list()
            n_hash = len(m.group(1))
            content = m.group(2).strip()
            mn = re.match(num_re, content)
            cn_level = _cn_heading_level(content)
            if mn and not _is_date_like_number(mn.group(1)):
                level = min(mn.group(1).count(".") + 1, m_level)
                out.append({"type": "h", "level": level, "text": content,
                            "line": i + 1})
            elif cn_level:
                out.append({"type": "h", "level": cn_level, "text": content,
                            "line": i + 1})
            elif n_hash == 1:
                out.append({"type": "title", "text": content, "line": i + 1})
            else:
                # 无编号的 `## `~`####### ` 行：按「# 数 - 1」兜底（## → H1）
                level = min(n_hash - 1, m_level)
                out.append({"type": "h", "level": level, "text": content,
                            "line": i + 1})
            i += 1
            continue

        m_num = re.match(num_re, line)
        if m_num and not _is_date_like_number(m_num.group(1)):
            flush_list()
            n_dots = m_num.group(1).count(".")
            level = min(n_dots + 1, m_level)   # 1段→1, 2段→2, …, 7段→7
            text = line                              # 保留原编号文本（含「1 绪论」）
            out.append({"type": "h", "level": level, "text": text, "line": i + 1})
            i += 1
            continue

        # 无 `#` 的中文式编号行（`一、总体要求` / `（一）工作目标`）→ 标题
        cn_level = _cn_heading_level(line)
        if cn_level:
            flush_list()
            out.append({"type": "h", "level": cn_level, "text": line, "line": i + 1})
            i += 1
            continue

        # 正文标号（规范第七条）：形式随层级为 1. / 1) / (1) / ① / a. / (a) / i.
        #   层级由前缀形式决定；`-` `*` `+` 按缩进空格兜底。嵌套标号行行首不留空格。
        list_match = re.match(
            r"^(\s*)(\(\d+\)|\d+[.\)]|\([a-z]+\)|[a-z]+[.]|[①-⑳]|[-*+])\s+(.*)$",
            raw)
        if list_match:
            indent = len(list_match.group(1))
            marker = list_match.group(2)
            text = list_match.group(3).strip()
            ch = marker[0]
            if "①" <= ch <= "⑳":                     # ① → 4级（带圈数字）
                level = 4
            elif ch == "(":                           # (1) → 3级；(a) → 6级
                level = 3 if marker[1].isdigit() else 6
            elif ch.isdigit():                        # 1) → 2级；1. → 1级
                level = 2 if marker.endswith(")") else 1
            elif ch.isalpha():                        # i. ii. iii. → 7级；其余字母 → 5级
                level = 7 if re.fullmatch(
                    r"(?:i{1,3}|iv|v|vi{0,3}|ix|x)", marker[:-1]) else 5
            else:                                     # - * + → 按缩进
                level = 3 if indent >= 4 else (2 if indent >= 2 else 1)
            pending_list.append({"level": level, "text": text})
            i += 1
            continue

        if line.startswith(">"):
            flush_list()
            out.append({"type": "quote", "text": line.lstrip(">").strip()})
            i += 1
            continue

        # 硬分页：单独一行 [[PAGEBREAK]]
        if _PAGEBREAK_RE.fullmatch(line):
            flush_list()
            out.append({"type": "pagebreak"})
            i += 1
            continue

        if not line:
            flush_list()
            i += 1
            continue

        flush_list()
        out.append({"type": "p", "text": line})
        i += 1

    flush_list()
    return out


def check_heading_gaps(parsed):
    """检查标题层级连续性：不允许向下跳级（本标题层级 > 上一标题层级 + 1）。

    返回违规列表 [{"line", "prev_level", "level", "text"}]；首个标题不校验
    （文档可以任意层级起头，如直接以二级节开头的骨架）。
    """
    gaps = []
    prev = None
    for node in parsed:
        if node.get("type") != "h":
            continue
        level = node["level"]
        if prev is not None and level > prev["level"] + 1:
            gaps.append({"line": node.get("line"), "prev_level": prev["level"],
                         "level": level, "text": node["text"]})
        prev = node
    return gaps


def render_to_docx(doc, parsed, use_title=None):
    """把 parsed 结构渲染进 docx。use_title 为文档主标题或 None。

    `# 主标题` 行（title 节点）默认渲染为 Title；若 --title 已给或已出现过
    主标题，则该行降级为一级标题（不丢内容）。
    """
    has_title = bool(use_title)
    if use_title:
        _title(doc, use_title)
    for node in parsed:
        t = node["type"]
        if t == "title":
            if has_title:
                _heading(doc, node["text"], 1)
            else:
                _title(doc, node["text"])
                has_title = True
        elif t == "h":
            _heading(doc, node["text"], node["level"])
        elif t == "p":
            _body_paragraph(doc, node["text"])
        elif t == "quote":
            _body_paragraph(doc, node["text"], bold=True)
        elif t == "pagebreak":
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        elif t == "hr":
            _add_hr(doc)
        elif t == "code":
            _add_code_block(doc, node["lines"])
        elif t == "table":
            _add_table(doc, node["rows"])
        elif t == "list":
            items = node["items"]
            by_level = {}
            for it in items:
                by_level.setdefault(it["level"], []).append(it["text"])
            for lvl in sorted(by_level):
                add_auto_numbered_list(doc, by_level[lvl], level=lvl)
    return doc


def _find_keep_anchor(doc, marker):
    """在底模里找 `--keep-until` 指定的锚点段落，返回其索引；找不到返回 None。

    匹配规则：段落文本去空白后包含 marker（大小写敏感）。这是刻意从简的
    约定——底模作者在封面/声明页末尾留一行标记文字，脚本据此切分。
    """
    target = str(marker).strip()
    if not target:
        return None
    for idx, par in enumerate(doc.paragraphs):
        if target in (par.text or ""):
            return idx
    return None


def _clear_after_anchor(doc, anchor_idx):
    """删除锚点段落之后的所有 body 内容（含表格），保留锚点及其以上部分。"""
    body = doc.element.body
    anchor_par = doc.paragraphs[anchor_idx]._p
    # 收集锚点之后、sectPr 之前的全部子元素
    seen_anchor = False
    to_remove = []
    for child in list(body):
        if child is anchor_par:
            seen_anchor = True
            continue
        if not seen_anchor:
            continue
        if child.tag == qn("w:sectPr"):
            break
        to_remove.append(child)
    for el in to_remove:
        body.remove(el)
    return len(to_remove)


def render_into_template(template_path, parsed, use_title=None, keep_until=None):
    """把文章灌入用户提供的底模 docx，保留封面/声明页等前置部件。

    这是 `--base-template` 的实现。解决的问题：公文红头、学位论文封面与
    原创性声明页、单位发文机关标志这类部件脚本无法凭空生成，只能由用户
    提供含这些部件的模板，脚本负责把正文接在后面。

    keep_until：模板里的一行标记文字。脚本删掉该行之后的所有内容，正文从
    该处续写；不传则内容追加到模板末尾。标记行本身保留（通常它就是封面
    与正文之间的分界，如「摘要」前的空行或「目录」标题）。

    样式处理：底模自带样式体系（学校/单位模板往往有自己的 Normal、Heading），
    直接 apply_article_style 会覆盖它们。这里先套用本技能样式以保证版式合规，
    底模的封面部件因使用独立样式或直接格式而不受影响。
    """
    doc = Document(template_path)
    if keep_until:
        anchor = _find_keep_anchor(doc, keep_until)
        if anchor is None:
            raise ValueError(
                f"底模中找不到锚点文字「{keep_until}」。\n"
                "请确认该文字确实存在于模板的某个段落里（脚本按段落文本包含匹配）。")
        removed = _clear_after_anchor(doc, anchor)
        if removed == 0:
            sys.stderr.write(
                f"[md2docx] 提示：锚点「{keep_until}」之后本就没有内容，"
                "正文将直接接在其后。\n")
    render_to_docx(doc, parsed, use_title=use_title)
    apply_article_style(doc)
    return doc



def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Markdown → 排版规范 docx")
    parser.add_argument("first", nargs="?",
                        help="输入 .md 文件；或 stdin 模式下的输出文件名")
    parser.add_argument("second", nargs="?",
                        help="输出文件名（提供 first 为 .md 时）")
    parser.add_argument("--title", default=None,
                        help="文档主标题（可选，不进入左侧目录树）")
    parser.add_argument("--profile", "-p", default=None,
                        help="文体 profile（必填，如 gov-official / thesis / news）；"
                             "也可用环境变量 ARTICLE_FORMAT_PROFILE")
    parser.add_argument("--list-profiles", action="store_true",
                        help="列出全部可用 profile 后退出")
    parser.add_argument("--base-template", default=None, metavar="模板.docx",
                        help="用指定 docx 作底模：保留其封面/声明页等前置部件，"
                             "正文接在其后（解决红头、印章、单位封面脚本无法生成的问题）")
    parser.add_argument("--keep-until", default=None, metavar="文字",
                        help="配合 --base-template：删掉底模中该文字所在段落之后的"
                             "全部内容，正文从该处续写。按段落文本包含匹配")
    ns = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if ns.list_profiles:
        from spec_loader import list_profiles
        for name in list_profiles():
            print(name)
        return 0

    # 本技能不使用默认排版：必须按文章性质指定文体
    if not ns.profile and not _as._PROFILE_SELECTED:
        from spec_loader import list_profiles
        sys.stderr.write(
            "错误：未指定文体 profile。本技能不使用默认排版，必须按文章性质选择。\n"
            "可选：\n  " + "\n  ".join(list_profiles()) + "\n"
            "用法：python md2docx.py in.md out.docx --profile <名>\n"
            "或设环境变量 ARTICLE_FORMAT_PROFILE=<名>。\n")
        return 2

    if ns.first is None:
        parser.error("需要输入文件名（或 --list-profiles）")

    if ns.profile:
        from spec_loader import ProfileNotFound, list_profiles
        try:
            _as.set_profile(ns.profile)
        except ProfileNotFound as exc:
            sys.stderr.write(f"错误：{exc}" + "\n")
            return 2

    if ns.second is not None:
        # 文件参数模式：in.md out.docx（输出相对 BASE，保留子目录）
        with open(ns.first, encoding="utf-8") as fh:
            md_text = fh.read()
        try:
            out_path = _resolve_out(ns.second)
        except ValueError as exc:
            sys.stderr.write(f"错误：{exc}\n")
            return 2
    else:
        # stdin 模式：out.docx < 文章.md（内容走标准输入，无可注入路径）
        md_text = sys.stdin.read()
        try:
            out_path = _resolve_out(ns.first)
        except ValueError as exc:
            sys.stderr.write(f"错误：{exc}\n")
            return 2

    parsed = parse_markdown(md_text)
    # 标题层级连续性校验（heading_gap_check）：跳级在转换阶段显式拦截，
    # 不再「写错序列照常套样式」静默产出。
    gap_check = heading_gap_check()
    gaps = check_heading_gaps(parsed)
    if gaps and gap_check != "off":
        for g in gaps:
            head = g["text"][:40]
            msg = (f"[标题层级跳级] 第 {g['line']} 行：上一标题 {g['prev_level']} 级，"
                   f"本标题 {g['level']} 级 → {head}")
            if gap_check == "error":
                sys.stderr.write(msg + "\n")
            else:
                sys.stderr.write("警告：" + msg + "\n")
        if gap_check == "error":
            sys.stderr.write(
                "转换中止：修正上述标题层级，或在 article-format.yaml 将 "
                "numbering_scheme.heading_gap_check 改为 warn/off。\n")
            return 1
    if ns.base_template:
        if not os.path.exists(ns.base_template):
            sys.stderr.write(f"错误：底模不存在：{ns.base_template}\n")
            return 2
        try:
            doc = render_into_template(ns.base_template, parsed,
                                      use_title=ns.title,
                                      keep_until=ns.keep_until)
        except ValueError as exc:
            sys.stderr.write(f"错误：{exc}\n")
            return 2
        except Exception as exc:
            sys.stderr.write(
                f"错误：无法用底模生成：{ns.base_template}\n"
                f"  原因：{type(exc).__name__}: {exc}\n"
                "  底模须是有效的 .docx（.doc/.dot 需先另存为 docx）。\n")
            return 2
    else:
        if ns.keep_until:
            sys.stderr.write(
                "提示：--keep-until 仅在配合 --base-template 时生效，已忽略。\n")
        doc = Document()
        render_to_docx(doc, parsed, use_title=ns.title)
        apply_article_style(doc)
    doc.save(out_path)
    print(f"已生成 {out_path}（套用排版规范）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
