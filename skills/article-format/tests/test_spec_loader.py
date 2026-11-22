# -*- coding: utf-8 -*-
"""test_spec_loader.py — 规格加载契约测试。

覆盖三类曾经的静默失败：
  1. profile 写错键不报错（list.formats 死键）
  2. 版本号三处不一致
  3. 未知 profile 名静默回落基线
"""
import os

import pytest

from spec_loader import (
    DEFAULT_SPEC,
    ProfileNotFound,
    ProfileNotSpecified,
    SpecKeyError,
    list_profiles,
    load_spec,
    validate_spec_keys,
)


def test_all_profiles_load():
    """13 个 profile 全部能被加载并通过未知键校验。"""
    names = list_profiles()
    assert len(names) >= 12, f"profile 数量异常：{len(names)}"
    for name in names:
        spec = load_spec(profile=name)
        assert spec["fonts"]["heading"], f"{name} 标题字体为空"
        assert spec["sizes_pt"]["body"] > 0, f"{name} 正文字号异常"


def test_baseline_loads():
    spec = load_spec(profile="default")
    assert spec["sizes_pt"]["body"] == 12


def test_unknown_key_rejected():
    """写错键必须报错——这是 P0 的核心防线。"""
    with pytest.raises(SpecKeyError) as exc:
        validate_spec_keys({"list": {"formats": {"level1": "%1."}}})
    assert "list.formats" in str(exc.value)


def test_unknown_top_key_rejected():
    with pytest.raises(SpecKeyError):
        validate_spec_keys({"typo_section": {"x": 1}})


def test_level_defs_accepted():
    """list.level_defs 是合法键，其元素键 fmt/text 也合法。"""
    validate_spec_keys({
        "list": {"level_defs": [
            {"fmt": "decimal", "text": "%1."},
        ]}
    })


def test_level_defs_bad_element_key_rejected():
    """level_defs 元素里写错键要报出来，不能整体放行。"""
    with pytest.raises(SpecKeyError) as exc:
        validate_spec_keys({
            "list": {"level_defs": [{"fmt": "decimal", "fmtt": "oops"}]}
        })
    assert "fmtt" in str(exc.value)


def test_heading_by_level_dynamic_keys():
    """heading_by_level 的 1/2/3/4 是动态键，不能被判为未知。"""
    validate_spec_keys({"fonts": {"heading_by_level": {1: "黑体", 2: "楷体"}}})


def test_profile_meta_keys_accepted():
    validate_spec_keys({
        "profile": {
            "name": "x", "title": "y", "standard": "z",
            "source": "s", "note": "n", "required_sections": ["摘要"],
        }
    })


def test_nonexistent_profile_raises():
    with pytest.raises(ProfileNotFound):
        load_spec(profile="not-a-real-profile")


def test_no_profile_raises_when_required():
    """不传 profile 且无环境变量时必须报错，不许静默套基线。"""
    os.environ.pop("ARTICLE_FORMAT_PROFILE", None)
    os.environ.pop("ARTICLE_FORMAT_SPEC", None)
    with pytest.raises(ProfileNotSpecified):
        load_spec(profile=None, require=True)


def test_dead_keys_absent_from_all_profiles():
    """已废弃的死键不得再出现在任何 profile 或基线 yaml 里。

    heading_style / body_list_style / use_gongwen 从未被代码读取，
    留着只会让人以为改了有用。
    """
    import glob
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = [os.path.join(root, "article-format.yaml")]
    files += sorted(glob.glob(os.path.join(root, "profiles", "*.yaml")))
    dead = ("heading_style:", "body_list_style:", "use_gongwen:", "formats:")
    offenders = []
    for path in files:
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for key in dead:
                    if stripped.startswith(key):
                        offenders.append(f"{os.path.basename(path)}:{lineno} {stripped}")
    assert not offenders, "仍存在死配置键：\n" + "\n".join(offenders)


def test_version_single_source():
    """版本号必须单一来源：DEFAULT_SPEC 与基线 yaml 一致。"""
    import yaml
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "article-format.yaml"), encoding="utf-8") as fh:
        yaml_version = yaml.safe_load(fh).get("version")
    assert DEFAULT_SPEC["version"] == yaml_version, (
        f"版本不一致：DEFAULT_SPEC={DEFAULT_SPEC['version']} "
        f"yaml={yaml_version}")


def test_documented_test_count_matches():
    """文档里声称的测试项数必须与实际收集到的一致。

    这类数字最容易漂：加一个测试文件就过期，而没有任何东西会报错。
    table-format 曾因同样的漂移把「408 项」写成旧值，故这里钉死。
    找不到声称值就跳过（文档可能选择不写具体数字）。
    """
    import re
    import subprocess
    import sys
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    claimed = None
    for path in (os.path.join(root, "SKILL.md"),
                 os.path.join(root, "README.md"),
                 os.path.join(root, "..", "README.md")):
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            m = re.search(r"pytest[^\n]*?(\d+)\s*项", fh.read())
        if m:
            claimed = int(m.group(1))
            break
    if claimed is None:
        return
    # pyproject 的 addopts 带 -q，与命令行 -q 叠成 -qq 会吞掉汇总行，
    # 故用 --override-ini 清空 addopts 后再取数。
    r = subprocess.run([sys.executable, "-m", "pytest", "tests/",
                        "--collect-only", "-q",
                        "--override-ini=addopts="],
                       cwd=root, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    m = re.search(r"(\d+)\s+tests? collected", r.stdout + r.stderr)
    assert m, f"无法获取测试项数：{(r.stdout + r.stderr)[-500:]}"
    actual = int(m.group(1))
    assert claimed == actual, (
        f"文档声称 {claimed} 项，实际 {actual} 项。请同步文档里的数字。")
