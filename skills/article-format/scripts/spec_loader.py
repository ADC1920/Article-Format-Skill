# -*- coding: utf-8 -*-
"""
文章排版规格配置加载器（article-format 技能内部模块）。

规格唯一权威源：技能根目录的 `article-format.yaml`。
配置文件缺失、字段缺失或 PyYAML 不可用时，一律回落到本模块的 DEFAULT_SPEC
（与 yaml 当前值一致），保证脚本在无配置环境下仍可正常运行。

用法：
    from spec_loader import load_spec
    spec = load_spec()                  # 默认 profile（通用文章，article-format.yaml）
    spec = load_spec(profile="gov-official")   # 指定文体 profile
    spec["sizes_pt"]["h1"]              # 15

profile 体系（2026-11-21 起）
--------------------------------
`profiles/` 目录下每个 yaml 描述一种文体的完整排版规格，与 DEFAULT_SPEC
深合并后使用（缺失字段自动继承通用文章默认值）。`default` 是特例，实体是
技能根目录的 `article-format.yaml`（保持既有引用与自定义不破坏）。

选择 profile 的优先级（高→低）：
    1. 环境变量 ARTICLE_FORMAT_SPEC（绝对路径，临时套用任意规格文件）
    2. 参数 profile=... 或环境变量 ARTICLE_FORMAT_PROFILE（文体名，如 gov-official）
    3. default（article-format.yaml）
"""
import os

SPEC_FILENAME = "article-format.yaml"
PROFILE_DIRNAME = "profiles"
DEFAULT_PROFILE = "default"
ENV_PROFILE = "ARTICLE_FORMAT_PROFILE"
ENV_SPEC_PATH = "ARTICLE_FORMAT_SPEC"

# 内置默认值：必须与 article-format.yaml 保持一致（配置文件缺失时的兜底）
DEFAULT_SPEC = {
    "version": "1.5.4",
    "fonts": {
        "heading": "黑体",
        "body": "宋体",
        "western": "Times New Roman",
    },
    "sizes_pt": {
        "doc_title": 18,
        "h1": 15,
        "h2": 14,
        "h3": 14,
        "h4": 12,
        "h5": 12,
        "h6": 10.5,
        "h7": 10.5,
        "body": 12,
        "table": 12,
        "footer": 12,
    },
    "spacing": {
        "line": 1.3,
        "h1_before_after_pt": 17,
        "h2_before_after_pt": 13,
        "h4_before_after_pt": 6,
        "h6_before_after_pt": 3,
        "body_before_after_lines": 0.1,
    },
    # 页面（纸型与页边距，v1.5.1 新增）
    "page": {
        "size": "A4",
        "width_cm": 21.0,
        "height_cm": 29.7,
        "margin_cm": 2.54,
        # 分边页边距（可选）：设置后覆盖 margin_cm 的四边同距行为。
        # 公文 GB/T 9704 用 上 3.7 / 下 3.5 / 左 2.8 / 右 2.6。
        # "margin_top_cm": None, "margin_bottom_cm": None,
        # "margin_left_cm": None, "margin_right_cm": None,
    },
    # 对齐（取值：center / justify / left / right）
    "alignment": {
        "title": "center",
        "h1": "center",
        "h2": "justify",
        "h3": "justify",
        "h4": "justify",
        "h5": "justify",
        "h6": "justify",
        "h7": "justify",
        "body": "justify",
    },
    "indent": {
        "body_first_line_chars": 2,
        "list_left": 0,
        "list_hanging": 0,
    },
    "color": {
        "text": "000000",
    },
    # 加粗规则（规范三/四/五/八/九）
    "bold": {
        "headings": True,
        "headings_western": True,
        "emphasis": True,
        "table_header": True,
    },
    # 表格（规范九）
    "table": {
        "font_size_pt": 12,
        "header_bold": True,
        "shading": False,
        "first_line_indent": False,
        "line_spacing": 1.3,
    },
    # 页脚页码（规范十）
    "footer": {
        "font": "宋体",
        "font_size_pt": 12,
        "color": "000000",
        "alignment": "center",
        "number_format": "dash",   # dash=- N -（默认）/ plain=N / none=不插页码
    },
    # 正文标号（规范七）
    "list": {
        "auto_numbering": True,
        "restart_per_block": True,
        "indent_zero": True,
        "space_after_number": True,
        "first_line_indent": False,
        "bold": False,
        "formats": {
            "level1": "%1.",                 # 1.（decimal）
            "level2": "%1)",                 # 1)（decimal）
            "level3": "(%1)",                # (1)（decimal）
            "level4": "%1",                  # ①（decimalEnclosedCircle）
            "level5": "%1.",                 # a.（lowerLetter）
            "level6": "(%1)",                # (a)（lowerLetter）
            "level7": "%1.",                 # i.（lowerRoman）
        },
    },
    # 导航目录（规范十一）
    "navigation": {
        "heading_styles": True,
        "outline_levels": [0, 1, 2, 3, 4, 5, 6],
        "title_in_toc": False,
    },
    # 编号体系（规范十二）
    "numbering_scheme": {
        "heading_levels": 7,
        "heading_style": "numeric",
        "heading_kind": "numeric",     # numeric / chinese / chapter / chinese-numeric / none
        "heading_auto_number": True,   # 标题编号 Word 自动多级编号（增删自动重排）
        "heading_gap_check": "error",  # 标题层级连续性校验：error / warn / off
        "space_after_number": True,
        "body_list_style": "1./1)/(1)/①/a./(a)/i.",
        "use_gongwen": False,
    },
}


def _skill_root():
    """技能根目录（本文件位于 <skill>/scripts/ 下）"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _profile_dir():
    """profile 预设目录"""
    return os.path.join(_skill_root(), PROFILE_DIRNAME)


def list_profiles():
    """列出可用文体 profile 名（按字母序）。不含 default（基线不再对外提供）。"""
    names = []
    pdir = _profile_dir()
    if os.path.isdir(pdir):
        for fn in sorted(os.listdir(pdir)):
            if fn.endswith((".yaml", ".yml")):
                names.append(os.path.splitext(fn)[0])
    return names


class ProfileNotSpecified(Exception):
    """未指定 profile 时抛出——本项目不使用「默认规范」，必须按文体选。"""


class ProfileNotFound(Exception):
    """指定了 profile 但找不到对应 yaml（文体名写错）时抛出。"""


def _profile_path(profile):
    """profile 名 → yaml 绝对路径。

    `default` 保留为内部基线（profile 的字段继承来源），不对外当文体用。
    未知名返回 profiles/<name>.yaml（由 load_spec 报缺失）。
    """
    if profile in (None, "", DEFAULT_PROFILE):
        return os.path.join(_skill_root(), SPEC_FILENAME)
    for ext in (".yaml", ".yml"):
        candidate = os.path.join(_profile_dir(), profile + ext)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(_profile_dir(), profile + ".yaml")


def _spec_path(profile=None, require=True):
    """配置文件路径。

    优先级：ARTICLE_FORMAT_SPEC（绝对路径覆盖）> profile 参数 >
    环境变量 ARTICLE_FORMAT_PROFILE。
    require=True 且三者都没有时抛 ProfileNotSpecified——
    本技能不提供「默认文体」，避免判不出文体时静默套一套不合适的位置。
    """
    override = os.environ.get(ENV_SPEC_PATH)
    if override:
        return override
    chosen = profile or os.environ.get(ENV_PROFILE)
    if not chosen:
        if require:
            raise ProfileNotSpecified(
                "未指定文体 profile。本技能不使用默认排版，必须按文章性质选择：\n  "
                + "、".join(list_profiles())
                + "\n用法：--profile <名>，或设环境变量 ARTICLE_FORMAT_PROFILE。")
        chosen = DEFAULT_PROFILE
    return _profile_path(chosen)


def resolve_profile(profile=None, require=True):
    """返回本次实际生效的 profile 名（用于日志与交付说明）。"""
    if os.environ.get(ENV_SPEC_PATH):
        return "custom:" + os.environ[ENV_SPEC_PATH]
    chosen = profile or os.environ.get(ENV_PROFILE)
    if not chosen and not require:
        return DEFAULT_PROFILE
    return chosen


def _deep_merge(base, override):
    """递归合并：override 有值的键覆盖 base，缺失的键保留 base 默认值"""
    result = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        elif value is not None:
            result[key] = value
    return result


def load_spec(verbose=False, profile=None, require=True):
    """加载指定文体的规格配置。

    profile: 文体 profile 名（如 "gov-official"）；None 时读环境变量
    ARTICLE_FORMAT_PROFILE。两者都没有且 require=True 时抛 ProfileNotSpecified——
    本技能不使用默认排版，必须按文章性质选 profile。
    profile 文件只写与该文体的差异，未写字段由 _deep_merge 继承 DEFAULT_SPEC
    这一字段级基线（基线是内部实现，不是可选文体）。

    require=False 仅供内部工具（如回归脚本读基线字段）使用。
    """
    path = _spec_path(profile, require=require)
    try:
        import yaml
    except ImportError:
        if verbose:
            print(f"[提示] 未安装 PyYAML，使用内置基线规格（{path} 未加载）")
        return dict(DEFAULT_SPEC)

    if not os.path.exists(path):
        # 指定了 profile 但文件不存在 = 文体名写错，必须报错。
        # 此前静默回落基线规格，会产出「看起来正常但文体不对」的文档（实测：
        # --profile not-exist 照常出稿，套的是基线 12pt 正文）。
        chosen = resolve_profile(profile, require=False)
        if require and chosen not in (None, "", DEFAULT_PROFILE):
            raise ProfileNotFound(
                f"未找到文体 profile「{chosen}」：{path}\n"
                "可用：\n  " + "\n  ".join(list_profiles()))
        if verbose:
            print(f"[提示] 未找到 {path}，使用内置基线规格")
        return dict(DEFAULT_SPEC)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as exc:
        if verbose:
            print(f"[警告] 读取 {path} 失败（{exc}），使用内置默认规格")
        return dict(DEFAULT_SPEC)

    return _deep_merge(DEFAULT_SPEC, data)


if __name__ == "__main__":
    import json
    import sys

    if "--list" in sys.argv:
        for name in list_profiles():
            print(name)
        raise SystemExit(0)

    prof = None
    if "--profile" in sys.argv:
        idx = sys.argv.index("--profile")
        if idx + 1 < len(sys.argv):
            prof = sys.argv[idx + 1]
    spec = load_spec(verbose=True, profile=prof)
    print(f"profile: {resolve_profile(prof)}")
    print(f"配置文件: {_spec_path(prof)}")
    print(json.dumps(spec, ensure_ascii=False, indent=2))
