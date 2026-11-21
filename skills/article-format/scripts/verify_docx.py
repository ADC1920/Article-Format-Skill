# -*- coding: utf-8 -*-
"""校验 docx 转换完整性：对比源 md 与生成 docx 的结构要素（门禁级，退出码 0/1）。

标题数两侧同口径统计、容差 0：
  · md 侧与 md2docx.parse_markdown 对齐——`#` 式 1~8 个；数字式「1 绪论」「1.1 实验装置」；
    代码围栏内不计数（围栏标记支持 ``` 与 ~~~）；行首日期形态（09.17 / 2026.10.08）
    已被 md2docx 落为正文，此处同步排除不计。
  · docx 侧按样式判定（Title / Heading 1-7），与产出通道结构一一对应。
  · 例外：md2docx 以 --title 显式传主标题时 docx 会多出 1 个 Title 段落，
    以 --title-in-docx 声明后按「md 标题数 + 1」比对。

用法：
    python verify_docx.py 源稿.md 产物.docx [--title-in-docx]
退出码：0 = 全部通过；1 = 存在失败项（表格数不一致 / 空表格 / 标题数不一致）。
"""

import argparse
import re
import sys

from docx import Document


def _is_date_like_number(num_text):
    """日期形态编号判定，与 md2docx._is_date_like_number 同口径：
    首段 4 位年份（2026.10.08）或任一段带前导零（09.17）→ 日期，md2docx 落为正文，
    此处同步不计为标题（否则含日期行首段的文档会误报「标题数不一致」）。"""
    parts = num_text.split(".")
    if len(parts[0]) == 4 and parts[0].isdigit():
        return True
    return any(len(seg) > 1 and seg.startswith("0") for seg in parts)


def count_md(md_path):
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.read().split("\n")
    tables, headings, code_blocks = 0, 0, 0
    in_code = False
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        # 围栏：与 md2docx 同口径（≥3 个反引号或波浪号，可带语言标注）
        if re.match(r"^(`{3,}|~{3,})", s):
            in_code = not in_code
            if in_code:
                code_blocks += 1
            i += 1
            continue
        if in_code:
            i += 1
            continue
        # 标题判定与 md2docx.parse_markdown 同口径：
        # `#` 式 1~8 个（主标题 + 七级章节）；数字式「1 绪论」「1.1 实验装置」；
        # 行首日期形态（09.17 / 2026.10.08）不按标题计（与 md2docx 日期防护一致）。
        if re.match(r"^#{1,8}\s+", s):
            headings += 1
        else:
            mn = re.match(r"^(\d+(?:\.\d+){0,6})\s+\S", s)
            if mn and not _is_date_like_number(mn.group(1)):
                headings += 1
        if s.startswith("|") and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if nxt.startswith("|") and "-" in nxt and re.fullmatch(r"\|[\s:|\-]+\|?", nxt):
                tables += 1
                i += 2
                while i < len(lines) and lines[i].strip().startswith("|"):
                    i += 1
                continue
        i += 1
    return {"tables": tables, "headings": headings, "code_blocks": code_blocks}


def count_docx(docx_path):
    d = Document(docx_path)
    tables = len(d.tables)
    # 标题段落按样式判定（Title / Heading 1-7）：旧版按「加粗 + 大字号」近似统计，
    # 会漏计仅靠样式定大小的标题、误计加粗引用段，在一致产物上即误报（实测 md=4
    # 时误算 docx=1），故改样式判定后两侧可精确比对。
    paras = [p for p in d.paragraphs if p.text.strip()]
    headings = 0
    for p in paras:
        name = (p.style.name or "").strip()
        if name == "Title" or name.startswith("Heading") or name.startswith("标题"):
            headings += 1
    total_table_cells = sum(len(t.rows) * len(t.columns) for t in d.tables)
    empty_tables = [i for i, t in enumerate(d.tables)
                    if not any(c.text.strip() for r in t.rows for c in r.cells)]
    return {
        "tables": tables,
        "headings": headings,
        "paragraphs": len(paras),
        "table_cells": total_table_cells,
        "empty_tables": empty_tables,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="docx 转换完整性校验（md 与 docx 结构要素对比）")
    ap.add_argument("md", help="源 Markdown")
    ap.add_argument("docx", help="生成 docx")
    ap.add_argument("--title-in-docx", action="store_true",
                    help="md2docx 以 --title 传了主标题（docx 标题数 = md 标题数 + 1）")
    ns = ap.parse_args(argv)

    a = count_md(ns.md)
    b = count_docx(ns.docx)
    print("--- 源 Markdown ---")
    print(f"  表格数     : {a['tables']}")
    print(f"  标题数     : {a['headings']}")
    print(f"  代码块数   : {a['code_blocks']}")
    print("--- 生成 docx ---")
    print(f"  表格数     : {b['tables']}")
    print(f"  标题数     : {b['headings']}")
    print(f"  非空段落数 : {b['paragraphs']}")
    print(f"  表格单元格 : {b['table_cells']}")
    print(f"  空表格索引 : {b['empty_tables'] or '无'}")

    print("--- 判定 ---")
    ok = True
    if a["tables"] != b["tables"]:
        print(f"  [FAIL] 表格数不一致: md={a['tables']} docx={b['tables']}")
        ok = False
    else:
        print(f"  [PASS] 表格数一致 ({a['tables']})")
    if b["empty_tables"]:
        print(f"  [FAIL] 存在空表格: {b['empty_tables']}")
        ok = False
    else:
        print("  [PASS] 无空表格")
    expected = a["headings"] + (1 if ns.title_in_docx else 0)
    if b["headings"] != expected:
        note = "（--title-in-docx：期望 = md + 1）" if ns.title_in_docx else "（容差 0）"
        print(f"  [FAIL] 标题数不一致: md={a['headings']} docx={b['headings']} "
              f"期望={expected} {note}")
        ok = False
    else:
        print(f"  [PASS] 标题数一致 ({expected})")
    print("  结果:", "全部通过" if ok else "存在问题")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
