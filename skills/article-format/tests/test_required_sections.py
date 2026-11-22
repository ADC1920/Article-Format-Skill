# -*- coding: utf-8 -*-
"""test_required_sections.py — 结构要件门禁。

版式全对不代表文章成立：论文缺摘要、公文缺发文机关，版式再准也没用。
profile 可通过 required_sections 声明必备章节关键词，verify 做存在性检查。
"""
import os
import subprocess
import sys

from spec_loader import list_profiles, load_spec


def _profiles_with_requirements():
    out = {}
    for name in list_profiles():
        req = (load_spec(profile=name).get("profile") or {}).get("required_sections")
        if req:
            out[name] = req
    return out


def test_some_profiles_declare_requirements():
    """至少要有一批 profile 声明了结构要件，否则门禁形同虚设。"""
    declared = _profiles_with_requirements()
    assert len(declared) >= 3, f"声明结构要件的 profile 太少：{declared}"
    assert "academic-paper" in declared
    assert "thesis" in declared


def test_academic_paper_requires_abstract():
    req = (load_spec(profile="academic-paper").get("profile") or {})["required_sections"]
    assert "摘要" in req
    assert "关键词" in req
    assert "参考文献" in req


def _gen_and_verify(scripts_dir, out_dir, md, profile):
    src = os.path.join(str(out_dir), "s.md")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(md)
    env = dict(os.environ)
    env["ARTICLE_OUT_DIR"] = str(out_dir)
    env.pop("ARTICLE_FORMAT_SPEC", None)
    docx = os.path.join(str(out_dir), "o.docx")
    gen = subprocess.run(
        [sys.executable, os.path.join(scripts_dir, "md2docx.py"),
         src, docx, "--profile", profile],
        capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
    assert gen.returncode == 0, gen.stderr[-800:]
    ver = subprocess.run(
        [sys.executable, os.path.join(scripts_dir, "verify_article_style.py"),
         docx, "--profile", profile],
        capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
    return ver


def test_missing_sections_fails(scripts_dir, out_dir):
    """缺摘要关键词的论文必须被结构门禁拦下。"""
    md = "# 标题\n\n## 1 绪论\n\n正文。\n"
    ver = _gen_and_verify(scripts_dir, out_dir, md, "academic-paper")
    assert ver.returncode == 1
    assert "结构 必备章节齐全" in ver.stdout
    assert "摘要" in ver.stdout


def test_present_sections_passes(scripts_dir, out_dir):
    """章节齐全时结构门禁应放行。"""
    md = ("# 标题\n\n## 1 摘要\n\n本文提出……\n\n"
          "## 2 关键词\n\n排版；文档\n\n"
          "## 3 正文\n\n正文内容。\n\n"
          "## 4 参考文献\n\n[1] 某某. 某书[M]. 2020.\n")
    ver = _gen_and_verify(scripts_dir, out_dir, md, "academic-paper")
    assert ver.returncode == 0, ver.stdout[-1500:]


def test_profile_without_requirements_skips(scripts_dir, out_dir):
    """未声明结构要件的 profile 该项直接通过，不误报。"""
    md = "# 标题\n\n## 1 一章\n\n正文。\n"
    ver = _gen_and_verify(scripts_dir, out_dir, md, "formal-doc")
    assert ver.returncode == 0, ver.stdout[-1200:]
    assert "未声明，跳过" in ver.stdout
