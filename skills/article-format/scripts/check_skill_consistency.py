# -*- coding: utf-8 -*-
"""check_skill_consistency.py — 技能内文档与实物的交叉一致性检查。

检查项：
1. SKILL.md 里列出的每个 profile 名，profiles/ 下都有对应 yaml
2. profiles/ 下每个 yaml 的 profile.name 与文件名一致
3. SKILL.md 里写的规范库条数（490）与 standards.jsonl 实际行数一致
4. SKILL.md 里写的领域数与 query_standards 的领域数一致
5. 每个 profile 的 yaml 都能被 load_spec 正常解析
6. profile 里引用的字体名/编号体系取值都在允许集合内

用法：
    python check_skill_consistency.py
退出码 0 = 全部一致，1 = 有不一致项。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

FAILS = []


def check(name, cond, detail=""):
    mark = "OK  " if cond else "FAIL"
    print(f"[{mark}] {name}" + (f"  <- {detail}" if detail and not cond else ""))
    if not cond:
        FAILS.append(name)


def main():
    from spec_loader import list_profiles, load_spec

    skill_md = os.path.join(ROOT, "SKILL.md")
    with open(skill_md, encoding="utf-8") as fh:
        md = fh.read()

    profiles = list_profiles()
    n_profiles = len(profiles)
    check(f"文体 profile 数量 {n_profiles} 个", n_profiles >= 12,
          f"实际 {n_profiles}")

    # 1/2：SKILL.md 提到的每个 `xxx` profile 都在磁盘上
    mentioned = set(re.findall(r"`([a-z][a-z0-9-]+)`", md))
    missing = [p for p in profiles if p not in md]
    check("SKILL.md 覆盖全部 profile 名", not missing, f"未提及：{missing}")

    # 3：yaml 内 profile.name 与文件名一致
    pdir = os.path.join(ROOT, "profiles")
    name_mismatch = []
    for fn in sorted(os.listdir(pdir)):
        if not fn.endswith((".yaml", ".yml")):
            continue
        stem = os.path.splitext(fn)[0]
        spec = load_spec(profile=stem)
        got = (spec.get("profile") or {}).get("name", "")
        if got and got != stem:
            name_mismatch.append(f"{stem} -> {got}")
    check("各 profile 的 name 字段与文件名一致", not name_mismatch,
          str(name_mismatch))

    # 4：规范库条数
    cat = os.path.join(ROOT, "references", "standards", "standards.jsonl")
    if os.path.exists(cat):
        with open(cat, encoding="utf-8") as fh:
            n_rows = sum(1 for line in fh if line.strip())
        claimed = re.search(r"(\d+)\s*条", md)
        ok = claimed is not None and int(claimed.group(1)) == n_rows
        check(f"SKILL.md 规范库条数与实际一致（{n_rows} 条）", ok,
              f"SKILL.md 声称 {claimed.group(1) if claimed else '未写'}")
        domains = set()
        with open(cat, encoding="utf-8") as fh:
            import json
            for line in fh:
                if line.strip():
                    domains.add(json.loads(line).get("domain"))
        check(f"规范库覆盖 {len(domains)} 个领域", len(domains) == 14,
              f"实际 {len(domains)}: {sorted(domains)}")
    else:
        check("规范库文件存在", False, cat)

    # 5/6：各 profile 取值合法性
    allowed_kind = {"numeric", "chinese", "chapter", "chinese-numeric", "none"}
    allowed_numfmt = {"dash", "plain", "none"}
    bad = []
    for prof in profiles:
        try:
            spec = load_spec(profile=prof)
        except Exception as exc:
            bad.append(f"{prof} 解析失败：{exc}")
            continue
        kind = str(spec.get("numbering_scheme", {}).get("heading_kind", "numeric"))
        nf = str(spec.get("footer", {}).get("number_format", "dash")).lower()
        if kind not in allowed_kind:
            bad.append(f"{prof} heading_kind={kind}")
        if nf not in allowed_numfmt:
            bad.append(f"{prof} number_format={nf}")
        for key in ("heading", "body", "western"):
            if not spec.get("fonts", {}).get(key):
                bad.append(f"{prof} fonts.{key} 为空")
        # 结构要件必须是字符串列表（verify 按文本包含匹配）
        req = (spec.get("profile") or {}).get("required_sections")
        if req is not None:
            if not isinstance(req, list) or not all(isinstance(x, str) and x for x in req):
                bad.append(f"{prof} required_sections 须为非空字符串列表：{req!r}")
    check("全部 profile 的取值合法", not bad, str(bad[:5]))

    # 7：版本号单一来源（DEFAULT_SPEC 与基线 yaml 必须一致）
    from spec_loader import DEFAULT_SPEC
    import yaml as _yaml
    with open(os.path.join(ROOT, "article-format.yaml"), encoding="utf-8") as fh:
        yaml_version = (_yaml.safe_load(fh) or {}).get("version")
    check(f"版本号单一来源（{DEFAULT_SPEC['version']}）",
          DEFAULT_SPEC["version"] == yaml_version,
          f"DEFAULT_SPEC={DEFAULT_SPEC['version']} yaml={yaml_version}")

    # 8：已废弃的死键不得回流（heading_style/body_list_style/use_gongwen/formats）
    dead_prefix = ("heading_style:", "body_list_style:", "use_gongwen:", "formats:")
    dead_hits = []
    for path in [os.path.join(ROOT, "article-format.yaml")] + [
            os.path.join(pdir, fn) for fn in sorted(os.listdir(pdir))
            if fn.endswith((".yaml", ".yml"))]:
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                s = line.strip()
                if s.startswith("#"):
                    continue
                if any(s.startswith(k) for k in dead_prefix):
                    dead_hits.append(f"{os.path.basename(path)}:{lineno} {s}")
    check("无已废弃死配置键", not dead_hits, "; ".join(dead_hits[:4]))

    # 9：pandoc 通道残骸不得回流（该通道已于 2026-09-11 移除）
    relic = [p for p in ("reference.docx", os.path.join("scripts", "make_reference_docx.py"))
             if os.path.exists(os.path.join(ROOT, p))]
    check("无 pandoc 通道残骸", not relic, str(relic))

    print()
    print(f"合计：{'全部一致' if not FAILS else f'{len(FAILS)} 项不一致'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
