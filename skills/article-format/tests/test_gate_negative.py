# -*- coding: utf-8 -*-
"""test_gate_negative.py — 门禁的负向测试。

正向测试只能证明「合规产物能过」，不能证明「不合规产物会被拦」。
这里篡改产物再跑校验，确认门禁真的会报 FAIL——否则 verify 就是空转。
"""
import os
import shutil
import subprocess
import sys
import zipfile

import pytest


@pytest.fixture
def good_docx(scripts_dir, out_dir):
    """生成一份合规的 formal-doc 产物作为篡改基底。"""
    md = "# 样例\n\n## 1 一章\n\n正文段落。\n\n## 2 二章\n\n另一段。\n"
    src = os.path.join(str(out_dir), "src.md")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(md)
    env = dict(os.environ)
    env["ARTICLE_OUT_DIR"] = str(out_dir)
    env.pop("ARTICLE_FORMAT_SPEC", None)
    out = os.path.join(str(out_dir), "good.docx")
    r = subprocess.run(
        [sys.executable, os.path.join(scripts_dir, "md2docx.py"),
         src, out, "--profile", "formal-doc"],
        capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stderr[-800:]
    return out


def _tamper_styles(src, dst, replacements):
    """改写 docx 内的 styles.xml，返回是否至少替换成功一处。"""
    hit = 0
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/styles.xml":
                text = data.decode("utf-8")
                for old, new in replacements:
                    if old in text:
                        text = text.replace(old, new)
                        hit += 1
                data = text.encode("utf-8")
            zout.writestr(item, data)
    return hit


def _verify(scripts_dir, docx, env):
    return subprocess.run(
        [sys.executable, os.path.join(scripts_dir, "verify_article_style.py"),
         docx, "--profile", "formal-doc"],
        capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")


def test_gate_passes_on_clean_output(scripts_dir, good_docx):
    """基线：合规产物必须 exit 0，否则后面的负向测试无意义。"""
    r = _verify(scripts_dir, good_docx, dict(os.environ))
    assert r.returncode == 0, r.stdout[-1500:]


def test_gate_catches_wrong_body_font(scripts_dir, good_docx, out_dir):
    """把正文中文字体改成微软雅黑，门禁必须报 FAIL。"""
    bad = os.path.join(str(out_dir), "bad_font.docx")
    hit = _tamper_styles(good_docx, bad, [('w:eastAsia="宋体"', 'w:eastAsia="微软雅黑"')])
    if hit == 0:
        pytest.skip("styles.xml 中未找到宋体声明，本机产物形态不同")
    r = _verify(scripts_dir, bad, dict(os.environ))
    assert r.returncode == 1, "门禁未拦住错误字体"
    assert "FAIL" in r.stdout
    assert "正文中文字体" in r.stdout


def test_gate_catches_wrong_body_size(scripts_dir, good_docx, out_dir):
    """把正文字号改错，门禁必须报 FAIL。"""
    bad = os.path.join(str(out_dir), "bad_size.docx")
    hit = _tamper_styles(good_docx, bad, [('w:val="24"', 'w:val="28"')])
    if hit == 0:
        pytest.skip("styles.xml 中未找到 12pt 字号声明")
    r = _verify(scripts_dir, bad, dict(os.environ))
    assert r.returncode == 1, "门禁未拦住错误字号"
    assert "FAIL" in r.stdout


def test_gate_clean_error_on_missing_file(scripts_dir, out_dir):
    """缺文件必须给一句话错误，不能抛 traceback。"""
    r = _verify(scripts_dir, os.path.join(str(out_dir), "nope.docx"),
                dict(os.environ))
    assert r.returncode == 1
    assert "不存在" in r.stderr
    assert "Traceback" not in r.stderr


def test_gate_clean_error_on_corrupt_file(scripts_dir, out_dir):
    """伪 docx 必须给可行动错误，不能抛 traceback。"""
    fake = os.path.join(str(out_dir), "fake.docx")
    with open(fake, "wb") as fh:
        fh.write(b"not a zip file")
    r = _verify(scripts_dir, fake, dict(os.environ))
    assert r.returncode == 1
    assert "无法作为 docx 打开" in r.stderr
    assert "Traceback" not in r.stderr


def test_gate_requires_profile(scripts_dir, good_docx):
    """不传 profile 必须 exit 2，不许用基线静默校验。"""
    env = dict(os.environ)
    env.pop("ARTICLE_FORMAT_PROFILE", None)
    env.pop("ARTICLE_FORMAT_SPEC", None)
    r = subprocess.run(
        [sys.executable, os.path.join(scripts_dir, "verify_article_style.py"),
         good_docx],
        capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
    assert r.returncode == 2, r.stdout[-500:]
    assert "未指定文体 profile" in r.stderr
