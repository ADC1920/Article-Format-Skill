# -*- coding: utf-8 -*-
"""verify_article_style.py — 逐条核验 docx 是否符合当前 profile 的排版规范。

用法：
    python verify_article_style.py <待检查.docx> [--profile <文体>]

默认 profile 是通用文章规范（article-format.yaml 十三条）；加 --profile
则按该文体的 yaml 口径核验（字体/字号/段距/纸型/页边距/编号体系/页码格式
全部取自规格，不再是写死数值）。

只读检查，不修改文件。退出码 0 = 全部通过，1 = 有失败项。
"""

import re
import sys
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

from spec_loader import load_spec, resolve_profile

FAILS = []
PASSES = []


def check(name, cond, detail=""):
    (PASSES if cond else FAILS).append(name)
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name}" + (f"  <- {detail}" if detail and not cond else ""))


def _style_xml(doc, name):
    return doc.styles[name].element.xml


def _find(xml, pattern):
    m = re.search(pattern, xml)
    return m.group(0) if m else None


def _effective_color(style_xml):
    m = re.search(r'<w:color w:val="([0-9A-Fa-f]{6})"', style_xml)
    return m.group(1) if m else None


def _sz_half(value):
    """磅值 → OOXML 半磅字符串（12 → "24"）。"""
    return str(int(round(float(value) * 2)))


def _pt_to_twips(value):
    """磅值 → 二十分之一磅字符串（17 → "340"）。"""
    return str(int(round(float(value) * 20)))


def _line_twips(multiple):
    """行距倍数 → OOXML w:line 值（1.3 → "312"，240 为单倍行距基准）。"""
    return str(int(round(float(multiple) * 240)))


def main(path, profile=None):
    doc = Document(path)
    spec = load_spec(profile=profile)
    prof = resolve_profile(profile)

    fonts = spec.get("fonts", {})
    sizes = spec.get("sizes_pt", {})
    spacing = spec.get("spacing", {})
    indent = spec.get("indent", {})
    page = spec.get("page", {})
    alignment = spec.get("alignment", {})
    num_scheme = spec.get("numbering_scheme", {})
    footer_spec = spec.get("footer", {})
    # 表格规格真源（article-format.yaml table 节）：字号/行距断言随配置口径
    _tbl = spec.get("table", {})
    table_font_pt = float(_tbl.get("font_size_pt", 12))
    table_ls = float(_tbl.get("line_spacing", 1.3))
    table_header_repeat = bool(_tbl.get("header_repeat", True))
    table_cant_split = bool(_tbl.get("cant_split", True))
    table_style_three_line = str(_tbl.get("style", "")).lower() in (
        "three-line", "three_line", "三线表")

    font_h = fonts.get("heading", "黑体")
    font_b = fonts.get("body", "宋体")
    font_w = fonts.get("western", "Times New Roman")
    size_title = sizes.get("doc_title", 18)
    size_body = sizes.get("body", 12)
    size_footer = sizes.get("footer", 12)
    line_val = _line_twips(spacing.get("line", 1.3))
    line_rule = str(spacing.get("line_rule", "auto") or "auto").lower()
    line_pt = spacing.get("line_pt")
    fixed_line = line_rule == "exact" and line_pt
    if fixed_line:
        # 固定行距：w:line 等于磅值×20，lineRule=exact
        line_val = str(int(round(float(line_pt) * 20)))
        line_rule_xml = "exact"
    else:
        line_rule_xml = "auto"
    bold_headings = bool(spec.get("bold", {}).get("headings", True))
    TEXT_COLOR = str(spec.get("color", {}).get("text", "000000") or "000000")
    font_by_level = fonts.get("heading_by_level") or {}

    def _font_h_for(level):
        if isinstance(font_by_level, dict):
            raw = font_by_level.get(level, font_by_level.get(str(level)))
            if raw:
                return str(raw)
        return font_h
    body_indent_chars = int(round(float(indent.get("body_first_line_chars", 2)) * 100))

    def _align_val(key, default):
        return {"center": "center", "justify": "both", "left": "left",
                "right": "right"}.get(str(alignment.get(key, default)).lower(),
                                      default)

    styles = {n: _style_xml(doc, n) for n in
              ["Title", "Heading 1", "Heading 2", "Heading 3", "Normal"]}

    print(f"[信息] profile={prof}  规格来源={spec.get('version', '-')}")

    # ---- 规范一：主标题（规格驱动：字号/加粗/对齐/字体/不进目录/黑色） ---- #
    t = styles["Title"]
    check(f"一 主标题字号{size_title:g}磅",
          f'w:val="{_sz_half(size_title)}"' in t, _find(t, r'<w:sz[^/]*/>') or "")
    check("一 主标题加粗", "<w:b/>" in t or '<w:b w:val="1"/>' in t)
    check("一 主标题对齐", f'w:jc w:val="{_align_val("title", "center")}"' in t)
    check(f"一 主标题中文字体{font_h}", f'w:eastAsia="{font_h}"' in t)
    check("一 主标题不进入目录(outlineLvl=9)", 'w:outlineLvl w:val="9"' in t)
    check("一 主标题无边框", "<w:pBdr" not in t)
    check(f"一 主标题颜色{TEXT_COLOR}", _effective_color(t) == TEXT_COLOR, _effective_color(t) or "")

    # ---- 规范二~七：一至七级标题（字号/段距/对齐/字体逐级按规格） ---- #
    h_space = {
        1: spacing.get("h1_before_after_pt", 17),
        2: spacing.get("h2_before_after_pt", 13),
        3: spacing.get("h2_before_after_pt", 13),
        4: spacing.get("h4_before_after_pt", 6),
        5: spacing.get("h4_before_after_pt", 6),
        6: spacing.get("h6_before_after_pt", 3),
        7: spacing.get("h6_before_after_pt", 3),
    }
    labels = {1: "二 一级标题", 2: "三 二级标题", 3: "四 三级标题",
              4: "五级标题", 5: "五级标题", 6: "六级标题", 7: "七级标题"}
    for lvl in range(1, 8):
        key = f"Heading {lvl}"
        if key not in doc.styles:
            continue
        h = _style_xml(doc, key)
        size_lvl = sizes.get(f"h{lvl}", size_body)
        al = _align_val(f"h{lvl}", "justify")
        lab = labels[lvl]
        check(f"{lab} 字号{size_lvl:g}磅",
              f'w:val="{_sz_half(size_lvl)}"' in h, _find(h, r'<w:sz[^/]*/>') or "")
        if bold_headings:
            check(f"{lab} 加粗", "<w:b/>" in h or '<w:b w:val="1"/>' in h)
        else:
            check(f"{lab} 不加粗",
                  "<w:b/>" not in h and '<w:b w:val="1"/>' not in h)
        check(f"{lab} 对齐({al})", f'w:jc w:val="{al}"' in h)
        lvl_font = _font_h_for(lvl)
        check(f"{lab} 中文字体{lvl_font}", f'w:eastAsia="{lvl_font}"' in h)
        check(f"{lab} 段前{float(h_space[lvl]):g}磅",
              f'w:before="{_pt_to_twips(h_space[lvl])}"' in h)
        check(f"{lab} 段后{float(h_space[lvl]):g}磅",
              f'w:after="{_pt_to_twips(h_space[lvl])}"' in h)
        line_label = (f"固定行距{float(line_pt):g}磅" if fixed_line
                      else f"行距{float(spacing.get('line', 1.3)):g}倍")
        check(f"{lab} {line_label}",
              f'w:line="{line_val}"' in h and f'lineRule="{line_rule_xml}"' in h,
              _find(h, r'<w:spacing[^/]*/>') or "")
        check(f"{lab} 颜色{TEXT_COLOR}", _effective_color(h) == TEXT_COLOR, _effective_color(h) or "")

    # ---- 规范五：标题英文字体（各标题样式） ---- #
    for key, label in (("Title", "五 主标题"), ("Heading 1", "五 一级"),
                       ("Heading 2", "五 二级"), ("Heading 3", "五 三级")):
        if key in styles:
            check(f"{label}英文{font_w}", f'w:ascii="{font_w}"' in styles[key])

    # ---- 规范六：正文（规格驱动） ---- #
    n = styles["Normal"]
    check(f"六 正文字号{size_body:g}磅", f'w:val="{_sz_half(size_body)}"' in n,
          _find(n, r'<w:sz[^/]*/>') or "")
    check(f"六 正文中文字体{font_b}", f'w:eastAsia="{font_b}"' in n)
    check(f"六 正文西文字体{font_w}", f'w:ascii="{font_w}"' in n)
    check(f"六 正文对齐({_align_val('body', 'justify')})",
          f'w:jc w:val="{_align_val("body", "justify")}"' in n)
    if body_indent_chars > 0:
        check(f"六 正文首行缩进{body_indent_chars / 100:g}字符",
              f'w:firstLineChars="{body_indent_chars}"' in n)
    else:
        check("六 正文无首行缩进", 'w:firstLineChars="0"' in n)
    body_lines = spacing.get("body_before_after_lines", 0.1)
    if float(body_lines) > 0:
        bl = str(int(round(float(body_lines) * 100)))
        check(f"六 正文段前{body_lines:g}行", f'w:beforeLines="{bl}"' in n)
        check(f"六 正文段后{body_lines:g}行", f'w:afterLines="{bl}"' in n)
    check(f"六 正文行距{float(spacing.get('line', 1.3)):g}倍" if not fixed_line
          else f"六 正文固定行距{float(line_pt):g}磅",
          f'w:line="{line_val}"' in n and f'lineRule="{line_rule_xml}"' in n)

    # ---- 规范七：列表自动编号（按 profile 的 level_defs 逐级核验） ---- #
    np = doc.part.numbering_part
    abs_nums = np.element.findall(qn("w:abstractNum"))
    lvl_texts = []
    for ab in abs_nums:
        for lvl in ab.findall(qn("w:lvl")):
            lt = lvl.find(qn("w:lvlText"))
            if lt is not None:
                lvl_texts.append(lt.get(qn("w:val")))
    list_defs = spec.get("list", {}).get("level_defs")
    if isinstance(list_defs, list) and list_defs:
        expected = []
        for item in list_defs[:3]:
            expected.append(item.get("text", "%1.") if isinstance(item, dict)
                            else str(item))
    else:
        expected = ["%1.", "%1)", "(%1)"]
    heading_kind = str(num_scheme.get("heading_kind", "numeric") or "numeric")
    if heading_kind in ("none", "off"):
        # 无章节编号体系（技术文档/profile 显式关闭）→ 不应有标题编号绑定
        check("七 profile 未启用章节编号", True)
    else:
        for want in expected:
            check(f"七 编号模板 {want}", want in lvl_texts, str(lvl_texts[:10]))
    # suff=space
    suffs = []
    for ab in abs_nums:
        for lvl in ab.findall(qn("w:lvl")):
            s = lvl.find(qn("w:suff"))
            if s is not None:
                suffs.append(s.get(qn("w:val")))
    check("七 编号与文字空一格(suff=space)", all(x == "space" for x in suffs) and len(suffs) > 0, str(suffs))
    # 列表段落顶格 + 引用 ilvl=0
    list_paras = []
    for p in doc.paragraphs:
        pPr = p._p.find(qn("w:pPr"))
        if pPr is None:
            continue
        npr = pPr.find(qn("w:numPr"))
        if npr is None:
            continue
        ilvl = npr.find(qn("w:ilvl")).get(qn("w:val"))
        nid = npr.find(qn("w:numId")).get(qn("w:val"))
        ind = pPr.find(qn("w:ind"))
        flc = ind.get(qn("w:firstLineChars")) if ind is not None else None
        left = ind.get(qn("w:left")) if ind is not None else None
        list_paras.append((nid, ilvl, flc, left, p.text))
    # 无列表项的文档（纯段落稿、只含标题与正文）合法——此时列表类断言
    # 不适用，记 skipped 而非 fail。此前无条件要求「列表段落存在」，
    # 任何不含列表的文档都会假失败（实测：发布副本用无列表样例测出 3 项 FAIL）。
    if not list_paras:
        check("七 本文档无列表项，列表规范不适用", True)
    else:
        check("七 列表段落存在", len(list_paras) > 0)
        check("七 列表统一引用 ilvl=0", all(x[1] == "0" for x in list_paras))
        check("七 列表顶格(firstLineChars=0)", all(x[2] == "0" for x in list_paras),
              str([x[2] for x in list_paras]))
        check("七 列表左缩进为0", all(x[3] in ("0", None) for x in list_paras),
              str([x[3] for x in list_paras]))
        # 「每个列表块独立从 1 开始」——必须查 w:lvlOverride/w:startOverride。
        # 只比对 numId 不同是不够的：多个 num 引用同一 abstractNum 时编号会延续
        # （实测第二个列表块显示 3. 4.，仅靠 numId 断言会漏判成假绿）。
        num_ids = []
        for num in np.element.findall(qn("w:num")):
            nid = num.get(qn("w:numId"))
            override = num.find(qn("w:lvlOverride"))
            has_start = override is not None and override.find(
                qn("w:startOverride")) is not None
            if nid in {x[0] for x in list_paras}:
                num_ids.append((nid, has_start))
        check("七 每个列表块有独立 num 实例",
              len(set(n for n, _ in num_ids)) == len(num_ids) and len(num_ids) > 0,
              str(num_ids))
        check("七 每个列表块带 startOverride=1（强制从1重启）",
              all(hs for _, hs in num_ids) and len(num_ids) > 0, str(num_ids))

    # ---- 规范九：表格 表头加粗 字号/行距/对齐 无底色 ---- #
    # 字号与行距吃 article-format.yaml 的 table 节（改 yaml 即改断言口径）；
    # 左对齐与缩进清零为出稿实现约定（防窄列两端对齐拉字距、防继承正文缩进）。
    for ti, table in enumerate(doc.tables):
        hdr_bold = False
        for c in table.rows[0].cells:
            for p in c.paragraphs:
                for r in p.runs:
                    if r.font.bold:
                        hdr_bold = True
        check(f"九 表{ti} 表头加粗", hdr_bold)

        sizes, ls_vals, off_left = [], [], []
        for row in table.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    ls_vals.append(p.paragraph_format.line_spacing)
                    if p.alignment != WD_ALIGN_PARAGRAPH.LEFT:
                        off_left.append(p.text[:12])
                    for r in p.runs:
                        sizes.append(r.font.size.pt if r.font.size is not None else None)
        check(f"九 表{ti} 字号{table_font_pt:g}磅",
              bool(sizes) and all(s is not None and abs(s - table_font_pt) < 0.01
                                  for s in sizes),
              str(sizes[:4]))
        check(f"九 表{ti} 行距{table_ls:g}倍",
              bool(ls_vals) and all(v is not None and abs(v - table_ls) < 0.01
                                    for v in ls_vals),
              str(ls_vals[:4]))
        check(f"九 表{ti} 单元格左对齐", not off_left, str(off_left[:3]))

        shd_found = False
        for row in table.rows:
            for c in row.cells:
                tcPr = c._tc.find(qn("w:tcPr"))
                if tcPr is not None and tcPr.find(qn("w:shd")) is not None:
                    fill = tcPr.find(qn("w:shd")).get(qn("w:fill"))
                    if fill and fill not in ("auto", "FFFFFF"):
                        shd_found = True
        check(f"九 表{ti} 无底色/隔行着色", not shd_found)

        # 跨页规则（v1.5.5）：首行重复标题行 + 行不拆页，随 yaml 开关联动
        if table_header_repeat:
            trPr = table.rows[0]._tr.find(qn("w:trPr"))
            has_hdr = trPr is not None and trPr.find(qn("w:tblHeader")) is not None
            check(f"九 表{ti} 首行重复标题行(tblHeader)", has_hdr)
        if table_cant_split:
            no_split = all(
                r._tr.find(qn("w:trPr")) is not None
                and r._tr.find(qn("w:trPr")).find(qn("w:cantSplit")) is not None
                for r in table.rows)
            check(f"九 表{ti} 行不拆页(cantSplit)", no_split)

        # 三线表（学术/学位论文）：顶底 1.5 磅、栏目线 0.75 磅、无竖线与内横线
        if table_style_three_line:
            bd = table._tbl.tblPr.find(qn("w:tblBorders"))
            got = {}
            if bd is not None:
                for tag in ("w:top", "w:bottom", "w:left", "w:right",
                            "w:insideH", "w:insideV"):
                    el = bd.find(qn(tag))
                    got[tag.split(":")[1]] = (el.get(qn("w:val")),
                                              el.get(qn("w:sz"))) if el is not None else None
            check(f"九 表{ti} 三线表 顶线1.5磅",
                  got.get("top") == ("single", "12"), str(got.get("top")))
            check(f"九 表{ti} 三线表 底线1.5磅",
                  got.get("bottom") == ("single", "12"), str(got.get("bottom")))
            check(f"九 表{ti} 三线表 无竖线与内横线",
                  all((got.get(k) or ("none", ""))[0] == "none"
                      for k in ("left", "right", "insideH", "insideV")),
                  str({k: got.get(k) for k in ("left", "right", "insideH", "insideV")}))
            hdr_tc = table.rows[0].cells[0]._tc.find(qn("w:tcPr"))
            hdr_bd = hdr_tc.find(qn("w:tcBorders")) if hdr_tc is not None else None
            col_line = (hdr_bd.find(qn("w:bottom")) if hdr_bd is not None else None)
            check(f"九 表{ti} 三线表 栏目线0.75磅",
                  col_line is not None
                  and col_line.get(qn("w:val")) == "single"
                  and col_line.get(qn("w:sz")) == "6",
                  "无栏目线" if col_line is None else
                  f"{col_line.get(qn('w:val'))}/{col_line.get(qn('w:sz'))}")

    # ---- 规范十：页脚 PAGE 域（字号/字体/对齐/页码格式按规格） ---- #
    footer = doc.sections[0].footer
    fx = footer._element.xml
    number_format = str(footer_spec.get("number_format", "dash")).lower()
    if number_format in ("none", "off"):
        check("十 页码已按规格关闭（无 PAGE 域）", "PAGE" not in fx)
    else:
        check("十 页脚含PAGE域", "PAGE" in fx)
        f_align = str(footer_spec.get("alignment", "center")).lower()
        check(f"十 页脚对齐({f_align})", f'w:jc w:val="{f_align}"' in fx)
        check(f"十 页脚字号{size_footer:g}磅",
              f'w:val="{_sz_half(size_footer)}"' in fx, _find(fx, r'<w:sz[^/]*/>') or "")
        par0 = footer.paragraphs[0] if footer.paragraphs else None
        runs_text = [r.text for r in par0.runs] if par0 is not None else []
        if number_format == "dash":
            check("十 页码格式「- N -」",
                  bool(runs_text) and runs_text[0] == "- " and runs_text[-1] == " -",
                  str(runs_text))
        else:
            # 纯数字模式：不得出现前后缀文本（PAGE 域自身的占位数字不算前后缀）
            check("十 页码无前后缀",
                  not any(t in ("- ", " -") for t in runs_text), str(runs_text))

    # ---- 附：OOXML schema 顺序合规（防 numPr / abstractNum 乱序回归） ---- #
    # ECMA-376：pPr 内 numPr 必须排在 spacing/ind/jc/outlineLvl 等之前；
    # numbering.xml 中 abstractNum 必须全部先于 num。
    _AFTER_NUMPR = {qn(t) for t in (
        "w:suppressLineNumbers", "w:pBdr", "w:shd", "w:tabs",
        "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap",
        "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN",
        "w:bidi", "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind",
        "w:contextualSpacing", "w:mirrorIndents", "w:suppressOverlap", "w:jc",
        "w:textDirection", "w:textAlignment", "w:textboxTightWrap",
        "w:outlineLvl", "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr",
        "w:pPrChange",
    )}

    def _numpr_misplaced(pPr):
        kids = list(pPr)
        for i, child in enumerate(kids):
            if child.tag == qn("w:numPr"):
                return any(k.tag in _AFTER_NUMPR for k in kids[:i])
        return False

    style_bad = []
    for st in doc.styles:
        el = getattr(st, "element", None)
        if el is None:
            continue
        pPr = el.find(qn("w:pPr"))
        if pPr is not None and _numpr_misplaced(pPr):
            style_bad.append(st.name)
    para_bad = []
    for p in doc.paragraphs:
        pPr = p._p.find(qn("w:pPr"))
        if pPr is not None and _numpr_misplaced(pPr):
            para_bad.append(p.text[:20])
    check("附 schema 顺序 numPr 位置合规（样式+段落）",
          not style_bad and not para_bad,
          f"styles={style_bad} paras={para_bad}")

    num_after_abs = 0
    seen_num = False
    for child in np.element:
        if child.tag == qn("w:num"):
            seen_num = True
        elif child.tag == qn("w:abstractNum") and seen_num:
            num_after_abs += 1
    check("附 schema 顺序 numbering 中 abstractNum 先于 num",
          num_after_abs == 0, f"错位 abstractNum 数={num_after_abs}")

    # ---- 附：标题样式不得继承正文（防「段前段后磅值」被正文行单位值顶掉） ---- #
    # v1.5.3 教训：Normal 的 beforeLines/afterLines（0.1 行）经 basedOn 继承到标题
    # 样式后，OOXML「行单位优先于磅值」会把标题段距静默压成 0.1 行；旧断言只查
    # 磅值属性是否存在（存在性≠生效性），全 PASS 但渲染贴紧。此处查继承链。
    inherit_bad = []
    for name in ("Title", "Heading 1", "Heading 2", "Heading 3",
                 "Heading 4", "Heading 5", "Heading 6", "Heading 7"):
        st = doc.styles[name]
        bO = st.element.find(qn("w:basedOn"))
        if bO is not None:
            inherit_bad.append(f"{name}->{bO.get(qn('w:val'))}")
    check("附 标题样式无 basedOn（防段距被正文行单位顶替）", not inherit_bad,
          str(inherit_bad))

    # ---- 纸型与页边距（按规格，支持分边页边距） ---- #
    sec = doc.sections[0]
    w_cm = sec.page_width.cm if sec.page_width else 0
    h_cm = sec.page_height.cm if sec.page_height else 0
    want_w = float(page.get("width_cm", 21.0))
    want_h = float(page.get("height_cm", 29.7))
    check(f"纸型 {page.get('size', 'A4')}（{want_w:g}×{want_h:g}cm）",
          abs(w_cm - want_w) < 0.05 and abs(h_cm - want_h) < 0.05,
          f"{w_cm:.2f}×{h_cm:.2f}cm")
    base_margin = float(page.get("margin_cm", 2.54))

    def _want_edge(key):
        raw = page.get(key)
        try:
            return float(raw) if raw is not None else base_margin
        except (TypeError, ValueError):
            return base_margin

    want_margins = (_want_edge("margin_top_cm"), _want_edge("margin_bottom_cm"),
                    _want_edge("margin_left_cm"), _want_edge("margin_right_cm"))
    margins = (sec.top_margin.cm, sec.bottom_margin.cm,
               sec.left_margin.cm, sec.right_margin.cm)
    symmetric = len({round(m, 2) for m in want_margins}) == 1
    label = (f"页边距 {want_margins[0]:g}cm（四边）" if symmetric else
             "页边距 上{:g}/下{:g}/左{:g}/右{:g}cm".format(*want_margins))
    check(label,
          all(abs(m - w) < 0.05 for m, w in zip(margins, want_margins)),
          str([round(m, 2) for m in margins]))

    # ---- 附：无未解析的 ** 加粗标记（列表项等富文本路径回归防线） ---- #
    # 代码块内容按字面输出（Consolas + 无首行缩进），块内的 ** 本就是原文，
    # 不算「未解析」——否则任何带 Markdown 示例的技术文档都会假失败。
    leftovers = []

    def _is_code_run(par):
        for run in getattr(par, "runs", []):
            name = run.font.name or ""
            if name.startswith("Consolas"):
                return True
        return False

    for p in doc.paragraphs:
        if "**" in p.text and not _is_code_run(p):
            leftovers.append(p.text[:30])
    for ti, table in enumerate(doc.tables):
        for row in table.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    if "**" in p.text and not _is_code_run(p):
                        leftovers.append(f"表{ti}:{p.text[:20]}")
    check("附 无未解析的 ** 加粗标记", not leftovers,
          str(leftovers[:5]))

    # ---- 无 Markdown 残留语法：围栏标记 / 分隔线 / 围栏注释误判为标题 ----
    # 2026-10-09 与 adc-standards 仓对齐时按本机 v1.8 恢复的三项残留防线：
    # 围栏内 `#` 注释被误升为标题、``` 与 `---` 字面落入成品，均为已在档缺陷。
    fence_residue, hr_residue, hash_heading = [], [], []
    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        if re.match(r"^(?:`{3,}|~{3,})", t):
            fence_residue.append(t[:30])
        elif re.match(r"^(?:-{3,}|\*{3,}|_{3,})$", t):
            hr_residue.append(t[:30])
        elif re.match(r"^#{1,7}\s+\S", t):
            style_name = (p.style.name or "") if p.style is not None else ""
            if style_name.startswith("Heading"):
                hash_heading.append(t[:30])
    check("附 无代码围栏标记残留", not fence_residue, str(fence_residue[:3]))
    check("附 无分隔线字面残留", not hr_residue, str(hr_residue[:3]))
    check("附 无围栏注释误判为标题", not hash_heading, str(hash_heading[:3]))

    print()
    print(f"合计：PASS {len(PASSES)} / FAIL {len(FAILS)}")
    if FAILS:
        print("失败项：")
        for f in FAILS:
            print("  -", f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    _args = sys.argv[1:]
    if not _args:
        print(__doc__)
        raise SystemExit(2)
    _profile = None
    _path = None
    _i = 0
    while _i < len(_args):
        _a = _args[_i]
        if _a in ("--profile", "-p") and _i + 1 < len(_args):
            _profile = _args[_i + 1]
            _i += 2
            continue
        if _a.startswith("--profile="):
            _profile = _a.split("=", 1)[1]
            _i += 1
            continue
        if _path is None:
            _path = _a
        _i += 1
    if _path is None:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(_path, _profile))
