# -*- coding: utf-8 -*-
"""query_standards.py — 按领域/关键词/文体检索规范库。

规范库位置：<skill>/references/standards/standards.jsonl（由
build_standards_catalog.py 从调研产物生成）。

用法：
    python query_standards.py --list-domains
    python query_standards.py --domain gov                    # 某领域全部条目
    python query_standards.py --keyword 三线表                # 关键词检索
    python query_standards.py --profile thesis                # 某 profile 关联条目
    python query_standards.py --domain academic --min-conf high
    python query_standards.py --keyword 摘要 --json           # 输出 jsonl 原文

输出默认是紧凑文本（编号｜名称｜置信度｜规格首句），--json 输出完整 JSON 行，
便于程序继续处理。--full 输出完整规格全文。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(os.path.dirname(HERE), "references", "standards",
                       "standards.jsonl")

DOMAIN_CN = {
    "gov": "公文与政务", "office": "办公与企业文书", "academic": "学术与科研",
    "language": "语言文字基础", "finance": "财经与披露", "legal": "法律与合规",
    "engineering": "工程与质量", "tech": "技术与数据文档", "media": "新闻与媒体",
    "marketing": "营销与品牌", "publishing": "出版与文学", "medical": "医疗卫生",
    "edu": "教育与教学", "misc": "综合实务",
}
CONF_RANK = {"high": 3, "medium": 2, "low": 1, "": 0}
CONF_CN = {"high": "高", "medium": "中", "low": "低"}


def load(path=CATALOG):
    if not os.path.exists(path):
        sys.stderr.write(
            f"[错误] 规范库不存在：{path}\n"
            "请先运行 build_standards_catalog.py 生成。\n")
        return None
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def render(row, full=False):
    name = row.get("name", "")
    conf = CONF_CN.get(row.get("confidence", ""), row.get("confidence", ""))
    specs = row.get("specs", "")
    if not full and len(specs) > 80:
        specs = specs[:78] + "…"
    line = f"[{row.get('id', '')}] {name}（{conf}）"
    if row.get("applies_to"):
        line += f"\n    适用：{row['applies_to']}"
    line += f"\n    规格：{specs}"
    if full and row.get("source"):
        line += f"\n    来源：{row['source']}"
    return line


def main(argv=None):
    ap = argparse.ArgumentParser(description="检索文章规范库")
    ap.add_argument("--list-domains", action="store_true", help="列出领域与条目数")
    ap.add_argument("--domain", default=None, help="按领域过滤（如 gov / academic）")
    ap.add_argument("--keyword", default=None, help="关键词（匹配名称/规格/适用文体）")
    ap.add_argument("--profile", default=None, help="按关联 profile 过滤")
    ap.add_argument("--category", default=None, help="按原始子类过滤（模糊匹配）")
    ap.add_argument("--min-conf", default=None,
                    choices=["high", "medium", "low"], help="最低置信度")
    ap.add_argument("--limit", type=int, default=0, help="最多输出条数（0=不限）")
    ap.add_argument("--json", action="store_true", help="输出 JSON 行原文")
    ap.add_argument("--full", action="store_true", help="输出完整规格与来源")
    ns = ap.parse_args(argv if argv is not None else sys.argv[1:])

    rows = load()
    if rows is None:
        return 2

    if ns.list_domains:
        counts = {}
        for row in rows:
            counts[row.get("domain", "misc")] = counts.get(row.get("domain", "misc"), 0) + 1
        print(f"规范库共 {len(rows)} 条")
        for key, cn in DOMAIN_CN.items():
            if counts.get(key):
                print(f"  {key:<12} {cn:<10} {counts[key]:>3} 条")
        return 0

    sel = rows
    if ns.domain:
        dom = ns.domain.strip().lower()
        if dom not in DOMAIN_CN:
            sys.stderr.write(
                f"[提示] 未知领域 {dom}，可用：{', '.join(DOMAIN_CN)}\n")
        sel = [r for r in sel if r.get("domain") == dom]
    if ns.profile:
        sel = [r for r in sel if r.get("profile") == ns.profile]
    if ns.category:
        cat = ns.category.strip()
        sel = [r for r in sel if cat in r.get("category", "")]
    if ns.keyword:
        kw = ns.keyword.strip()
        sel = [r for r in sel
               if kw in r.get("name", "") or kw in r.get("specs", "")
               or kw in r.get("applies_to", "") or kw in r.get("category", "")]
    if ns.min_conf:
        floor = CONF_RANK[ns.min_conf]
        sel = [r for r in sel if CONF_RANK.get(r.get("confidence", ""), 0) >= floor]

    sel.sort(key=lambda r: (-CONF_RANK.get(r.get("confidence", ""), 0),
                            r.get("domain", ""), r.get("id", "")))
    if ns.limit and ns.limit > 0:
        sel = sel[:ns.limit]

    if ns.json:
        for row in sel:
            print(json.dumps(row, ensure_ascii=False))
        return 0

    if not sel:
        print("（无匹配条目）")
        return 0
    print(f"匹配 {len(sel)} 条\n")
    for row in sel:
        print(render(row, full=ns.full))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
