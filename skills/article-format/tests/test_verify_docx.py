# -*- coding: utf-8 -*-
"""test_verify_docx.py — 转换完整性门禁（verify_docx.py）。

与 verify_article_style 的分工：
  - verify_article_style 查「版式对不对」：字体、字号、段距、编号体系、页码。
  - verify_docx 查「有没有丢东西」：源稿的标题数与表格数，在产物里是否一一对上。

后者挡的是另一类失败：样式全对，但内容在转换中丢了。两者不是替代关系。
"""
import os
import subprocess
import sys


def _gen(scripts_dir, out_dir, md, profile="formal-doc"):
    src = os.path.join(str(out_dir), "s.md")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(md)
    env = dict(os.environ)
    env["ARTICLE_OUT_DIR"] = str(out_dir)
    env.pop("ARTICLE_FORMAT_SPEC", None)
    docx = os.path.join(str(out_dir), "o.docx")
    r = subprocess.run(
        [sys.executable, os.path.join(scripts_dir, "md2docx.py"),
         src, docx, "--profile", profile],
        capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stderr[-800:]
    return src, docx


def _verify_docx(scripts_dir, md, docx, extra=None):
    cmd = [sys.executable, os.path.join(scripts_dir, "verify_docx.py"), md, docx]
    if extra:
        cmd += extra
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def test_structure_matches(scripts_dir, out_dir):
    """标题数与表格数一致时 pass。"""
    md = "# 标题\n\n## 1 一章\n\n正文。\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n"
    src, docx = _gen(scripts_dir, out_dir, md)
    r = _verify_docx(scripts_dir, src, docx)
    assert r.returncode == 0, r.stdout[-1200:]
    assert "标题数一致" in r.stdout
    assert "表格数一致" in r.stdout


def test_empty_table_detected(scripts_dir, out_dir):
    """空表格必须被报出来（内容在转换中丢失的典型形态）。"""
    md = "# 标题\n\n## 1 一章\n\n正文。\n\n|  |  |\n| --- | --- |\n|  |  |\n"
    src, docx = _gen(scripts_dir, out_dir, md)
    r = _verify_docx(scripts_dir, src, docx)
    assert "空表格" in r.stdout


def test_title_count_mismatch_detected(scripts_dir, out_dir):
    """人为把 docx 删去一个标题段落，标题数应不一致并 exit 1。

    用 --title 传主标题时 md 侧标题数少一个，靠 --title-in-docx 校正；
    这里反其道而行：不传该标志，构造出「docx 比 md 多一个 Title」的错配。
    """
    md = "# 标题\n\n## 1 一章\n\n正文。\n"
    src = os.path.join(str(out_dir), "s.md")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(md)
    env = dict(os.environ)
    env["ARTICLE_OUT_DIR"] = str(out_dir)
    env.pop("ARTICLE_FORMAT_SPEC", None)
    docx = os.path.join(str(out_dir), "o.docx")
    # 用 --title 额外注入一个主标题段落，docx 侧就多了一个 Title
    r = subprocess.run(
        [sys.executable, os.path.join(scripts_dir, "md2docx.py"),
         src, docx, "--profile", "formal-doc", "--title", "额外主标题"],
        capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stderr[-800:]
    # 不传 --title-in-docx，期望 = md 标题数，实际多 1 → 应 FAIL
    v = _verify_docx(scripts_dir, src, docx)
    assert v.returncode == 1, v.stdout[-1200:]
    assert "标题数不一致" in v.stdout


def test_title_in_docx_flag_corrects(scripts_dir, out_dir):
    """传 --title-in-docx 后同样的产物应通过。"""
    md = "# 标题\n\n## 1 一章\n\n正文。\n"
    src = os.path.join(str(out_dir), "s.md")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(md)
    env = dict(os.environ)
    env["ARTICLE_OUT_DIR"] = str(out_dir)
    env.pop("ARTICLE_FORMAT_SPEC", None)
    docx = os.path.join(str(out_dir), "o.docx")
    r = subprocess.run(
        [sys.executable, os.path.join(scripts_dir, "md2docx.py"),
         src, docx, "--profile", "formal-doc", "--title", "额外主标题"],
        capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stderr[-800:]
    v = _verify_docx(scripts_dir, src, docx, ["--title-in-docx"])
    assert v.returncode == 0, v.stdout[-1200:]


def test_date_line_not_counted_as_heading(scripts_dir, out_dir):
    """行首日期在两端口径里都不算标题，不能误报数量不一致。"""
    md = "# 标题\n\n## 1 一章\n\n09.17 期数据。\n\n2026.10.08 上新。\n"
    src, docx = _gen(scripts_dir, out_dir, md)
    r = _verify_docx(scripts_dir, src, docx)
    assert r.returncode == 0, r.stdout[-1200:]


def test_code_fence_heading_not_counted(scripts_dir, out_dir):
    """围栏内的 # 注释不算标题，两侧同口径。"""
    md = "# 标题\n\n## 1 一章\n\n```python\n# 注释不是标题\nx = 1\n```\n"
    src, docx = _gen(scripts_dir, out_dir, md)
    r = _verify_docx(scripts_dir, src, docx)
    assert r.returncode == 0, r.stdout[-1200:]
