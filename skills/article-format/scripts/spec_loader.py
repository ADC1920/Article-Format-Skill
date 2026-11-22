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
    "version": "2.2.1",
    "fonts": {
        "heading": "黑体",
        "body": "宋体",
        "western": "Times New Roman",
        # 按标题层级分别指定中文字体（公文体：黑体/楷体/仿宋）；
        # None = 未设置，各级统一用 fonts.heading
        "heading_by_level": None,
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
        # 固定行距（行网格）：line_rule=exact 时用 line_pt，覆盖倍数行距
        "line_rule": "auto",
        "line_pt": None,
    },
    # 页面（纸型与页边距，v1.5.1 新增）
    "page": {
        "size": "A4",
        "width_cm": 21.0,
        "height_cm": 29.7,
        "margin_cm": 2.54,
        # 分边页边距（可选）：设置后覆盖 margin_cm 的四边同距行为。
        # 公文 GB/T 9704 用 上 3.7 / 下 3.5 / 左 2.8 / 右 2.6。
        "margin_top_cm": None,
        "margin_bottom_cm": None,
        "margin_left_cm": None,
        "margin_right_cm": None,
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
        "header_repeat": True,
        "cant_split": True,
        # 表格样式：three-line=三线表（学术/学位/医学论文）；None/空=常规网格
        "style": None,
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
        # 七级编号定义（profile 整体替换）；None = 用代码内置七级
        # 形态：[{fmt: decimal, text: "%1."}, ...]，见 article_style._list_level_defs
        "level_defs": None,
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
        "heading_kind": "numeric",     # numeric / chinese / chapter / chinese-numeric / none
        "heading_auto_number": True,   # 标题编号 Word 自动多级编号（增删自动重排）
        "heading_gap_check": "error",  # 标题层级连续性校验：error / warn / off
        "space_after_number": True,
    },
}

# profile 专用元数据键（只作说明与溯源，不影响排版行为）
PROFILE_META_KEYS = {"name", "title", "standard", "source", "note", "required_sections"}


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


class SpecKeyError(Exception):
    """profile yaml 里出现基线中不存在的键（拼错或已废弃）时抛出。

    此前 yaml 写错键（如把 list.level_defs 写成 list.formats）会被 _deep_merge
    静默吞掉，改配置不生效且不报错——实测改 formats.level1 后 numbering.xml
    逐字节不变、exit 0。这类静默失效排查成本极高，进入加载即拦截。
    """


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


def _key_paths(node, prefix=""):
    """收集一份配置的键路径集合（叶子与中间节点都算）。

    heading_by_level 的值是 {1: 黑体} 这类动态键，按「前缀整体放行」处理，
    不逐条比对以免把合法配置判成未知键。
    """
    paths = set()
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            paths.add(path)
            if path in _DYNAMIC_KEY_PATHS:
                continue
            paths |= _key_paths(value, path)
    elif isinstance(node, list):
        allowed = _LIST_OF_DICT_PATHS.get(prefix)
        for item in node:
            if not isinstance(item, dict):
                continue
            if allowed is not None:
                # 白名单模式：只放行声明的元素键，其余记为未知
                paths |= {f"{prefix}.{k}" for k in item if k not in allowed}
            else:
                # 普通列表内字典：按元素键递归（不按下标展开）
                paths |= _key_paths(item, prefix)
    return paths


# 值本身是「动态键→值」映射的路径：不展开其内部键
_DYNAMIC_KEY_PATHS = {"fonts.heading_by_level"}
# 值本身是「列表内字典」的路径：元素键按白名单整体放行（不按下标展开）
_LIST_OF_DICT_PATHS = {
    "list.level_defs": {"fmt", "text"},
}


def validate_spec_keys(data, origin="profile"):
    """校验 profile yaml 的键都能在 DEFAULT_SPEC 中找到对应位置。

    存在未知键即抛 SpecKeyError 并列出全部可疑键——拼错的键会被 _deep_merge
    静默吞掉，改配置不生效且不报错，是排查成本最高的一类问题。
    profile 元数据键（name/title/standard/source/note/required_sections）放行。
    """
    known = _key_paths(DEFAULT_SPEC) | {f"profile.{k}" for k in PROFILE_META_KEYS}
    known.add("profile")
    known.add("version")
    # version 的父层与 profile 节本身允许
    unknown = []
    for path in sorted(_key_paths(data) - known):
        # 跳过动态键的内部路径（heading_by_level 下的 1/2/3/4）
        if any(path.startswith(d + ".") for d in _DYNAMIC_KEY_PATHS):
            continue
        # profile.xxx 下的说明项已整体放行，这里只拦非元数据
        unknown.append(path)
    if unknown:
        shown = "\n  ".join(unknown)
        raise SpecKeyError(
            f"{origin} 含未知配置键（这些键不会被任何代码读取，改了也不生效）：\n"
            f"  {shown}\n"
            "对照 scripts/spec_loader.py 的 DEFAULT_SPEC 检查拼写；"
            "可选键见 SKILL.md「规格配置」节。")
    return data


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

    # 未知键拦截：拼错或已废弃的键会被 _deep_merge 静默吞掉，改配置不生效
    # 且不报错。这里在合并前校验，让「改了没反应」立刻变成明确报错。
    validate_spec_keys(data, origin=os.path.basename(path))

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
