# article-format 技能变更记录

## 2026-11-21 · v2.1.0：取消默认排版，改为按文体强制选择

**动因**：用户指令「不需要默认规范，按文章的性质来选择排版，不固定」。v2.0 之前不指定 profile 时静默套用 default，等于给所有文体兜一套规格——判不出文体时出的成品可能整套版式都不对（如学位论文按通用文章排）。

**变更**：

| 文件 | 变更 |
|---|---|
| `profiles/formal-doc.yaml`（新增） | 原 default 基线独立成正式文体选项，适用范围明确为「方案、总结、汇报、调研报告、说明书等通用正式文章」。样式与旧 default 完全一致 |
| `scripts/spec_loader.py` | `list_profiles()` 不再返回 default；`_spec_path` / `resolve_profile` 增加 `require` 参数，未指定文体时抛 `ProfileNotSpecified`；新增 `ProfileNotFound`——指定了不存在的文体名时报错而非静默回落基线（实测 `--profile not-exist` 此前照常出稿、套的是基线 12pt 正文） |
| `scripts/article_style.py` | import 时不再强制要求 profile（否则连 `--list-profiles` 都跑不了），改为 `apply_article_style()` 入口拦截；`set_profile()` 置 `_PROFILE_SELECTED` |
| `scripts/md2docx.py` | 无 profile 时列出可选文体并 exit 2；捕获 `ProfileNotFound`；`first` 参数改为可选，使 `--list-profiles` 可单独使用 |
| `scripts/verify_article_style.py` | 核验同样要求 profile（须与生成时一致），并对未知文体名报错 |
| `scripts/run_profile_regression.py` / `check_skill_consistency.py` | 清理 default 特殊分支，回归范围变为 12 个文体 profile |
| `SKILL.md` | 文体表 default 行改 formal-doc；执行步骤「判不准用 default」改为「先查规范库，仍不确定问用户」；规格章节标明根 yaml 是字段级基线、非可选文体 |
| `~/.zcode/scripts/article-default.js` + `~/.zcode/AGENTS.md` | 常驻注入文案同步：从「一律默认用本技能」改为「没有默认排版，必须先按文体选 profile」 |

**行为变化**：不指定 profile 从「静默出稿」变为「报错退出（exit 2）并列出可选文体」；文体名写错从「静默套基线」变为「报错」。环境变量 `ARTICLE_FORMAT_PROFILE` 与 `--profile` 仍可用。

**验证**：13 个 profile（12 文体 + formal-doc）回归全绿；三入口无 profile 均 exit 2；未知文体三入口均 exit 2；环境变量方式正常；`--list-profiles` 输出 12 个文体、不含 default；一致性检查 6 项全过。

## 2026-11-21 · v2.0.0：多文体 profile + 490 条规范库（从单套规格升级为分文体规格体系）

**动因**：本技能此前只有一套「通用文章」规格，公文、学位论文、期刊论文、技术文档、法律文书等文体只能硬套同一组字体字号，与各自行业规范冲突（如公文要求 3 号仿宋 + 上 3.7/下 3.5/左 2.8/右 2.6cm 分边页边距、固定行距 28.9 磅、层次序数「一、」「（一）」；学位论文要求章标题「第1章」与三线表）。本次按用户指令收集 WPS 与全网各行业文章规范并融合升级。

**调研**：六路并行联网调研（国标与学术、WPS 与办公文书、财经与法律、媒体与营销、技术与质量、医疗与教育），共产出 **490 条**规范条目，覆盖 **46 个子类 / 14 个领域**；每条含名称、可执行规格、适用文体、来源与置信度（high 303 / medium 177 / low 10）。标准号经 openstd.samr.gov.cn、iso.org 等权威源核对，2025—2026 年新版标准（GB/T 7714-2025、GB/T 7713.1-2025、ISO 9001:2026、DCMM 2.0 等）按现行版本收录。

**变更**（10 件）：

| 文件 | 变更 |
|---|---|
| `profiles/*.yaml`（新增 12 个） | gov-official / enterprise-doc / thesis / academic-paper / medical-paper / tech-doc / legal-doc / press-release / business-report / regulation / teaching-doc / social-media，每个文件头注明依据的标准与来源 |
| `references/standards/`（新增 15 个） | 规范库三层结构：`index.md`（588 行索引）、`domain-<slug>.md`（14 个分域详表）、`standards.jsonl`（490 条机器可查数据） |
| `scripts/spec_loader.py` | 新增 profile 体系：`load_spec(profile=)`、`list_profiles()`、`resolve_profile()`；优先级 ARTICLE_FORMAT_SPEC > profile 参数 > ARTICLE_FORMAT_PROFILE > default；DEFAULT_SPEC 补 `heading_kind` / `number_format` / 分边页边距 / `alignment` 等字段 |
| `scripts/article_style.py` | ①规格常量改为可运行时刷新（另修一处既有缺口：`color.text` 此前从未被读取、一律硬编码 000000，导致 social-media 的 #333333 正文色配置无效）；（`set_profile` / `_refresh_spec_constants`），修复函数默认参数在 import 时固化导致切 profile 不生效；②新增四种章节编号体系（numeric / chinese / chapter / chinese-numeric / none）；③新增 `fonts.heading_by_level` 按层级指定字体（公文第一层黑体、第二层楷体）；④新增固定行距 `line_rule: exact` + `line_pt`（公文体行网格）；⑤新增分边页边距；⑥新增页码格式 `dash`/`plain`/`none`；⑦表格三线表 |
| `scripts/md2docx.py` | ①规格改为实时读取，不再 import 时固化；②新增 `--profile` 与 `--list-profiles`；③支持中文式标题识别与编号剥离（「一、」「（一）」「第一章」）；④新增三线表渲染（顶底 1.5 磅、栏目线 0.75 磅、无竖线） |
| `scripts/verify_article_style.py` | 断言全部改为规格驱动（字体/字号/段距/行距/纸型/页边距/编号体系/页码/加粗开关随 profile 变化），新增 `--profile`，断言数 173→约 100~107 项（随 profile 与表格数浮动）；新增三线表四项断言 |
| `scripts/query_standards.py`（新增） | 规范库检索：按领域/关键词/profile/子类/置信度过滤，支持 `--json` 与 `--full` |
| `scripts/build_standards_catalog.py`（新增） | 调研 jsonl → 规范库归一化合并（46 子类→14 域、去重、profile 软映射、三层输出） |
| `scripts/apply_verification.py`（新增） | 标准号核查结果并入规范库（不成立的降 low 并打标记） |
| `scripts/run_profile_regression.py`（新增） | 全部 profile 端到端回归，13 个 profile 一键核验 |
| `SKILL.md` | version → 2.0.0；新增 profile 速选表、规范库 14 域索引、四种编号体系说明、三线表说明、高级字段表、已知限制；description 触发词扩到各文体 |

**行为变化**：
- 不指定 profile 时行为与 v1.5.5 **完全一致**（default profile 就是原 `article-format.yaml`），既有调用无需改动。
- 指定 `--profile gov-official` 出公文版式（A4、分边页边距、3 号仿宋、固定行距 28.9 磅、「一、」层次序数、层级字体黑体/楷体/仿宋、层次标题不加粗、页码纯数字）。
- 指定 `--profile thesis` 出学位论文版式（章标题「第1章」、1.5 倍行距、三线表、五号表格）。
- 中文式标题（「一、」「（一）」）只在 `heading_kind` 为中文体系的 profile 下识别为标题；default 下仍是正文列举，避免误判。
- 正文列举标号「(1)」「①」在**任何** profile 下都不再被误判为章节标题（修复 thesis 下跳级报错）。

**验证**：`run_profile_regression.py` 13 个 profile 全通过（default 105 项、thesis 107 项、gov-official 103 项等，FAIL 0）；多负载形状人工构造文档（长标题、代码块含 `**`、嵌套七级列表、分页、引文、表格）在 default / gov-official / thesis / tech-doc / social-media 五个 profile 下均 PASS；公文成品实测页边距 3.7/3.5/2.8/2.6cm、正文 3 号、固定行距 exact 均正确落地。

**回滚点**：`~/.zcode/skill-backups/20261121-pre-v2-profiles/`。其中 SKILL.md（改前 10441 字节原文）与 article-format.yaml（按 v1.5.4 备份补 v1.5.5 两字段重建）可直接覆盖回滚；四个脚本取自更早的 `~/.agents/skill-backups/20261013-pre-af-v155/`（v1.5.4 原版），回退后功能等同 v1.5.4，如需精确回到 v1.5.5 的表格跨页两规则，另需按 2026-10-12 条目重新应用。

## 2026-10-12 · v1.5.5：表格跨页两条硬规则回归 + 页底孤行修复（渲染验收实战驱动）

**动因**：真实交付（《金点子贸易新产品开发方案-清晰版V2.0》）经 visual-judge 逐页验收抓出 7 页缺陷，归为两类：①表格行被页边界拆断、续页无表头（本机 v1.8 的 `header_repeat`/w:tblHeader 特性在 10-09 仓对齐全量替换时丢失）；②表头行与标题行孤立页底（表头/标题与内容被分页隔开）。本次以两条规则落地修复并重验归零。

**变更**（4 件）：

| 文件 | 变更 |
|---|---|
| `article-format.yaml` | 新增 `table.header_repeat`（首行重复标题行，默认 true）与 `table.cant_split`（行不跨页拆断，默认 true）两开关；version → 1.5.5 |
| `scripts/article_style.py` | 新增 `_set_table_cross_page()`：每表首行加 `w:tblHeader`（按 ECMA-376 子元素顺序落位、幂等）、每行加 `w:cantSplit`；表头行单元格段落加 keep_with_next；`_style_heading()` 补标题 keep_with_next（防标题孤立页底） |
| `scripts/verify_article_style.py` | 新增两条联动断言：每表「首行重复标题行(tblHeader)」「行不拆页(cantSplit)」，随 yaml 开关口径（173→194 条） |
| `SKILL.md` | 规格表「表格」行同步两条新规则；version → 1.5.5 |

**行为变化**：此后生成的 docx——跨页表格每页自动重复表头；同一行内容不再被页边界切成两半；标题与表头不孤立在页底（自动随内容推页）。行高近满页的表格如不希望整行推页，可关 `cant_split`。

**验证**：真实交付实证——修复前 visual-judge 12 页 7 fail（表格拆断 5 页 + 图形折行 2 页）；修复后 12 页 12 pass；`verify_article_style` 194/194 PASS；`check_delivery.py` 三道全过（含 officecli validate 0 错误与结构一致性）；ASCII 宽图折行问题以「源稿不用超过版心的围栏树图」规避（表述改行内串联/表格）。

**回滚点**：`~/.zcode/skill-backups/20261012-pre-tblheader-cantsplit/`（本条目三脚本备份）。

## 2026-10-09 · 回归补丁回流入仓（v1.5.4 收口：三项 Markdown 语法 + verify 链路增强）

**动因**：与仓对齐（v1.5.4）后本机保留了 4 项 v1.8 特性补丁而仓版缺失，其中三项语法（分隔线/围栏/分页）该文档（SKILL.md）本已承诺、脚本却未实现（文档-实现不一致）；verify_docx 为本机门禁级增强。本机技能双根去重收尾时按「单向同步」口径将补丁正式回移入仓，消除仓版自洽性缺陷。

**变更**（4 件）：

| 文件 | 变更 |
|---|---|
| `scripts/md2docx.py` | 新增三项 Markdown 语法渲染：`---`/`***`/`___` 独立行渲染为段落下边框横线（不留字面）；``` 与 ~~~ 代码围栏（块内文本按原样输出，`#` 注释不升标题）；独立行 `[[PAGEBREAK]]` 生成硬分页符 |
| `scripts/verify_article_style.py` | 新增 3 条残留扫描断言：无代码围栏标记残留 / 无分隔线字面残留 / 无围栏注释误判为标题（70→73 条） |
| `scripts/verify_docx.py` | 升级为门禁级（退出码 0/1）：标题数两侧同口径精确统计、容差 0、`--title-in-docx` 通道、行首日期形态同口径排除（旧版按「加粗+大字号」近似统计，一致产物上会误报） |
| `SKILL.md` | 语法说明同步（分隔线/围栏/分页写法）；技能路径描述更新为「技能实体位于 `%USERPROFILE%\.agents\skills\article-format`」 |

**行为变化**：md 源稿中 `---`、代码围栏、`[[PAGEBREAK]]` 自本次起按规范渲染（此前落字面文本或误升标题）；verify_docx 由近似 WARN 改为精确门禁（标题数不符即 exit 1）。

**验证**：本机全链——verify_article_style **73/73 PASS**；office 回归套件 ALL PASS（7 套件）；边界样稿（分隔线/围栏/分页/日期行）与负例（旧缺陷形态）均按预期拦截；回流入仓后以仓版脚本冒烟复验 73/73 + verify_docx 全过。

**回滚点**：本条目对应 git 提交本身（`git revert <提交>` 可精确回滚）。
## 2026-10-09 · v1.5.4：页脚页码规格修订 + 三级标题示例写法更正

**动因**（用户指令两条）：① 三级标题示例编号写法——原文档示例用「2.3.3 …」，用户指正应为「1.1.1 …」（与层级推进顺序一致）；② 页脚页码——字号由 10.5 磅改**宋体小四（12 磅）**，页码显示格式由裸数字改为 **「- 1 -」「- 2 -」「- 3 -」**（PAGE 域两侧加「- 」与「 -」），底端居中（居中本已实现，位置口径明确化）。

**变更**（5 件）：

| 文件 | 变更 |
|---|---|
| `article-format.yaml` | `sizes_pt.footer` 与 `footer.font_size_pt`：10.5 → 12；version → 1.5.4；头注补修订说明 |
| `scripts/article_style.py` | `_set_page_number_footer()`：PAGE 域前加「- 」run、域后加「 -」run（同字号字体） |
| `scripts/verify_article_style.py` | 页脚字号断言 10.5 磅 → 12 磅；新增「页码格式『- N -』」断言（69→70 条） |
| `scripts/spec_loader.py` | DEFAULT_SPEC 同步（footer 12 / version 1.5.4） |
| `SKILL.md` / `references/spec.md` / `scripts/md2docx.py` | 三级标题示例「2.3.3 → 1.1.1」（4 处）；页脚描述同步（规格表/核对要点/yaml 摘要/规范原文与实现映射）；断言数 70 |

**行为变化**：产出文档的页脚页码显示为「- N -」、字号小四；其余排版行为不变。

**验证**：全链冒烟 **70/70 PASS**；渲染读数（pymupdf）：p1「- 1 -」/ p2「- 2 -」，size=12pt，y=785.5/842（底端）；WPS COM 读页脚字号 12、文本「- N -」格式在位。

**回滚点**：`~/.zcode/tmp/af-backup-20261009-v153/article-format-pre-v153.tgz`（v1.5.3 改前归档；如需精确回 v1.5.3 可从技能仓翻本文件历史）。


## 2026-10-09 · v1.5.3：修复标题段前段后被正文行单位属性顶掉（渲染事故）

**动因**（用户目检测试页发现「段落格式没有按照格式执行」）：八种标题样式（Title / Heading 1-7）默认 basedOn 正文（Normal），而 Normal 为落实「正文段前段后 0.1 行」承载了行单位属性（`w:beforeLines/afterLines=10`）。OOXML 规定同一 spacing 内**行单位优先于磅值**——继承链把标题自身写入的段前段后磅值（一级 17 磅 / 二三级 13 磅 / 四五级 6 磅 / 六七级 3 磅 / 主标题段后 17 磅）整体压成 0.1 行（实测渲染约 1.8pt），标题与上下文贴紧。此前 verify 的段距断言只查「磅值属性是否存在」，不查继承链——存在性≠生效性的又一处盲区（同已知坑 #10/#11 家族）。

**变更**（4 件）：

| 文件 | 变更 |
|---|---|
| `scripts/article_style.py` | 新增 `_disinherit_from_normal()`：`_style_heading()` 与 `_style_title_style()` 先剥离样式的 basedOn（标题正式属性均显式设置、自包含；对无 basedOn 的样式幂等） |
| `scripts/verify_article_style.py` | 新增 1 条防回归断言：标题样式（Title / Heading 1-7）不得存在 basedOn（68→69 条） |
| `article-format.yaml` | version → 1.5.3；头注补修订说明 |
| `spec_loader.py` / `SKILL.md` | version → 1.5.3；SKILL.md 断言数说明同步为 69 |

**行为变化**：标题段前段后自本次起按 yaml 磅值真实生效（此前静默压成 0.1 行）；正文段（0.1 行）、列表、表格、页码不受影响。

**验证**：最小 A/B 对照（同结构两版 docx，剥离前「正文底→标题顶」渲染间隙 9.9pt，剥离后 25.7pt）；全链冒烟 verify **69/69 PASS**；WPS COM 读段落有效值复核（一级标题段距 17pt 生效）。

**回滚点**：`%USERPROFILE%\.zcode\tmp\af-backup-20261009-v153\article-format-pre-v153.tgz`（改前全目录归档）。

## 2026-10-09 · 文档对账：移除 外部平台承载描述（零行为变更）

**动因**（用户指令「外部平台永不回用」）：SKILL.md 内 5 处「外部平台侧由全局注入段 `外部平台主目录/AGENTS.md` 的『文章规范（全局默认）』节承担」及相关双平台并述已失实——同日本机 外部平台形态完成退役（安装源 外部平台段清除 → 部署脚本 外部平台逻辑删除 → 外部平台侧实际注入面 `外部平台主目录/AGENTS.md` 的文章规范节退役）。

**变更**（`SKILL.md` 单文件 5 处，零行为变更）：①「常驻规则」与「触发提示」两节去双平台并述（其他平台以 front-matter `description` 随技能清单语义匹配兜底）；②`<skill_dir>` 路径说明改中性（技能实体 + Junction 同址）；③「触发覆盖」两节同步同样处理。技能脚本、规格与产出行为零改动。

**验证**：本机技能与仓副本两版 SKILL.md 全文 外部平台残留 0；部署链无涉（本轮无脚本改动，切段/`--check` 行为不变）。

## 2026-10-09 · v1.5.2：表格配置接通 + 日期行标题误判修复

**动因**（用户指令「优化三个现状」，承接现状排查）：①表格外观与 `article-format.yaml` 的 `table` 节脱节——字号写死在 `add_rich_runs` 默认参数、行距与对齐靠样式继承、`sizes_pt.table` 与 `table.font_size_pt` 双源并存，改 yaml 对表格成品不生效；②单元格段落继承正文两端对齐与首行缩进（窄列字距被拉开、单元格文字缩进不齐，此前全靠出稿链后处理器 `fix_table_align` / `postprocess_article_docx` 兜底）；③行首日期形态（`09.17 期…` / `2026.10.08 …`）与数字编号同构，被误判为二级标题并挂章节编号（实测事故：两篇公众号数据报告均中招、靠改写行首规避）。

**变更**（5 件）：

| 文件 | 变更 |
|---|---|
| `scripts/md2docx.py` | `_add_table` 全面接通 `SPEC["table"]`：字号/表头加粗/行距读配置；单元格段落显式左对齐＋缩进清零（`_clear_first_line_indent`）；清除 `cell.text=""` 遗留的无字号空 run（会混入字号核验）；新增 `_is_date_like_number()` 日期守卫——日期形态的「编号」不参与标题定级（无 `#` 行落为正文段；`#` 行走无编号兜底、保留全文） |
| `scripts/verify_article_style.py` | 新增 3 条/表断言：字号（读 yaml `table.font_size_pt`）、行距（读 yaml `table.line_spacing`）、单元格左对齐（防两端对齐字距回潮）；字号/行距断言随配置口径 |
| `article-format.yaml` | version → 1.5.2；头注补修订记录；`table` 节标注「表格外观唯一权威源」；`sizes_pt.table` 标注遗留兼容 |
| `scripts/spec_loader.py` | DEFAULT_SPEC version → 1.5.2 |
| `SKILL.md` | md 源稿约定补日期守卫；规格表「表格」行更新；yaml 摘要补 `table` 键；verify 条数 65→68（每表 5 条）；version → 1.5.2 |

**行为变化**：表格外观改由 yaml `table` 节驱动（默认值下成品与 v1.5.1 一致），并有两处源头修复——单元格左对齐、缩进清零（此前依赖出稿链后处理，裸链场景不生效）；行首日期（前导零或四位年份开头）不再被误判为标题，落为正文段、不挂章节编号（`9.17` 这类无前导零月日与章节号同形，维持原行为，作标题需加 `#`）。

**验证**：①解析层回归 `.build/_af_v152_regression.py` **12/12 PASS**（日期落正文 ×4、正常编号不误伤 ×7、混排序列 ×1）；②全链冒烟（`.build/make_article.py`，样本含日期正文/表格/列表/加粗）`verify_article_style.py` **68/68 PASS** exit=0，链上 `fix_table_align` 环节 changed=0（源头已对齐，后处理器无活可干）；③负向对照（程序化破坏：某单元格字号 12→10 且左对齐→居中）两条新断言正确 FAIL、exit=1——断言有区分力，非假绿；④python-docx 行为实证（新建单元格 runs=0、`cell.text=""` 后 runs=1 空 run）——空 run 修复的根因取证。

**回滚点**：`%USERPROFILE%\.zcode\tmp\af-backup-20261009-pre-v152\article-format-pre-v152.tgz`（改前全目录归档，含 SKILL.md / scripts / references；`tar -xzf` 覆盖回技能目录即可）。

**迁移包**：`<迁移包目录>`（+ 同名 .zip）——含本版技能全目录、SessionStart hook、触发词行与安装说明，供源机安装同步（v1.5.1 以来的本地领先项一并纳入）。


## 2026-09-22 · v1.5.1：补纸型规格（A4）+ 编号列表富文本加粗

**动因**（用户指令「按建议顺序改」，承接会议纪要技能评审）：两处通用缺陷——①本技能脚本不设纸型，成品随 python-docx 默认模板落到 Letter（8.5×11in），中文办公打印/归档应为 A4（评审实测：无纸型设置的产物为 21.59×27.94cm）；②`**加粗**` 仅正文段与表格单元格解析，编号列表整段按纯文本写入——会议纪要里 12 处 `**已定**/**待确认/**待定**` 全在编号列表内，成品出现字面星号（上轮须靠文档级后处理脚本补救）。

**变更**（6 件）：

| 文件 | 变更 |
|---|---|
| `article-format.yaml` | 新增 `page` 节（A4 / 21.0×29.7cm / 页边距 2.54cm）；version → 1.5.1 |
| `scripts/spec_loader.py` | DEFAULT_SPEC 同步新增 `page` 节；version → 1.5.1 |
| `scripts/article_style.py` | 新增页面常量 + `_apply_page_setup()`（apply_article_style 内对全部节设纸型页边距）；新增公共 `add_rich_runs()`，`add_auto_numbered_list` 改走该入口 |
| `scripts/md2docx.py` | 删除本地 `_add_rich_runs`，统一 import `add_rich_runs`（正文/引文/表格/列表同一实现，避免两处漂移） |
| `scripts/verify_article_style.py` | 新增 3 条断言：纸型 A4、页边距 2.54cm、无未解析的 `**` |
| `SKILL.md` | 规格表补「页面」行与 v1.5.1 富文本说明；yaml 摘要补 page 键；交付前抽查补 verify 脚本；version → 1.5.1 |

**行为变化**：全部文章类产出的纸型由 Letter 变为 A4（四边 2.54cm 不变）；编号列表内的 `**重点**` 渲染为真加粗（不再输出字面星号）。其余排版行为不变。

**验证**：全链冒烟（样本 md 覆盖无编号标题 / 带 `**` 的编号列表 / 带 `**` 的表格单元格）→ `verify_article_style.py` **65/65 PASS**（原 62 + 新 3），exit=0；加粗落地取证（列表段与单元格均见加粗 run）；**负向对照**（Letter 纸型 + 含字面 `**` 的负例文档）两条新断言均正确 FAIL、退出码 1——断言有区分力，非假绿。

**回滚点**：`%USERPROFILE%\.zcode\tmp\af-backup-20260922-165553\article-format-pre-pagebold.tgz`（改前全目录归档，含 SKILL.md / scripts / references；`tar -xzf` 覆盖回技能目录即可）。


## 2026-09-22 16:01:06 · 回滚：回到 v1.5 基线（撤销本日表格并入系列改动）

**变更指令**（用户）：用户指令「回滚文章规范」；经平台提问确认，目标 = 2026-09-22 13:55 快照（= 本日表格并入之前的 v1.5 基线）。

**回滚内容**（8 件，逐件 sha256 与快照核对一致）：

| 文件 | 回滚前（现行 v1.6 终版） | 回滚后（v1.5） |
|---|---|---|
| `article-format.yaml` | 9,278 B / c71d1c1d9153 | 6,265 B / 571bec574dd3 |
| `SKILL.md` | 12,640 B / 578be2051d51 | 9,255 B / 49b57420fb3d |
| `references/spec.md` | 8,878 B / 91a8c7c3bd04 | 6,370 B / e91ad324a2bd |
| `scripts/article_style.py` | 42,908 B / 172d976b3130 | 31,798 B / 4376454bf05f |
| `scripts/md2docx.py` | 19,044 B / 76e4802832e8 | 16,133 B / a6c6f259d7ab |
| `scripts/spec_loader.py` | 5,916 B / 7b4689d59438 | 5,201 B / ee37938f06e0 |
| `scripts/verify_article_style.py` | 19,427 B / f7f087260bd4 | 10,810 B / 7c4ccab0c405 |
| `scripts/make_reference_docx.py` | 7,155 B / 2b4bb6ea1999 | 6,742 B / f21f4e52b790 |

**行为变化**：文章内表格恢复规则九原文——宋体小四、表头加粗、去底色（不再有深蓝表头 / 标题行底色 / 隔行底纹 / 网格主题色 / 跨页重复表头）；表首 `[[TABLETITLE]]` 整行标题行标记不再支持（md 源稿勿再使用）。

**未动**：`reference.docx`、`scripts/verify_docx.py`（两版逐字节一致，仅纳入备份）；全局规则「表格默认偏好」不在本次回滚范围——其原文中「与文章规范表格同源」的括注已于同日 15:59 另行删除（四副本同步），两处口径无悬挂引用。

**回滚点（现行 v1.6 终版完整备份，可再恢复）**：`%USERPROFILE%\.zcode\tmp\af-backup-20260922-20260922-160106-pre-rollback-v15`（11 件，含 CHANGELOG / reference.docx / verify_docx.py）。恢复办法：按同相对路径覆盖回技能目录即可。

**验证**：回滚后全链冒烟（样本 md → `md2docx.py` → `article_style.py` → `verify_article_style.py`）exit=0，**核验 62/62 PASS**（含「九 表0 无底色/隔行着色」）；`officecli validate` 0 错误；产物零主题色残留（`w:shd` 元素 0、色板串命中 0、表格样式回落 Table Grid）；8 件还原后 sha256 与快照逐件一致；`__pycache__` 4 个旧 pyc 已清。

## 2026-09-22 15:42:11 · 引用名再同步：全局条款换版「表格默认偏好」（零行为变更）

**动因**（用户指令）：全局规则把「表格外观默认」整段换版为「表格默认偏好」——范围扩为任何表格（xlsx/xls/md/CSV）、新增触发词表、表内字体改黑体 10 号、默认冻结表头条款回归（标题行+表头行 → `A3`，无标题行 → `A2`）、新增载体归属条。本技能 6 个文件 9 处引用旧名同步改名；两处「独立 xlsx 表格字体」的现态说明同步改为黑体 10 号。文章内表格仍按规则九用宋体小四（载体归属条明确随本文档载体），全局冻结条款的 docx 等价做法（重复表头行）本技能已在用，行为零变更。

**变更**（仅标题、说明与注释文字，零取值与逻辑改动）：`SKILL.md`「表格规格」节标题与字体分立句；`references/spec.md` 规则九修订说明首句；`article-format.yaml`（2 处注释 + 字体分立说明）；`scripts/article_style.py`（2 处）、`scripts/md2docx.py`、`scripts/make_reference_docx.py` 注释内旧名替换。

**验证**：六个文件旧名残留 0（本 CHANGELOG 历史条目按史实保留）；三个 .py 语法编译通过；`article-format.yaml` 解析通过；本轮未改任何规格取值与代码逻辑，核验链（96/96）结论不受影响、未重跑。

## 2026-09-22 15:00:33 · 引用名同步：全局条款改名「表格外观默认」（无行为变更）

**动因**：全局规则同日先删「表格默认偏好」段（用户指令），随后按用户指令重立为「表格外观默认」（独立表格统一外观，色板与本技能同源）。本技能 6 个文件内 8 处引用旧名，同步改名，避免指向已不存在的条款。

**变更**（仅标题、说明与注释文字，零行为改动）：`SKILL.md`「表格规格」节标题改为与全局同源表述、表内字体分立说明补全局条款名；`references/spec.md` 规则九修订说明首句改名；`article-format.yaml`（2 处注释）、`scripts/article_style.py`（2 处）、`scripts/md2docx.py`、`scripts/make_reference_docx.py` 注释内旧名替换。

**验证**：规格与代码六文件内旧名残留 0（本 CHANGELOG 按史实保留旧名叙述）；三个 .py 语法编译通过；`article-format.yaml` 解析通过；本轮未改任何规格取值与代码逻辑，核验链（96/96）结论不受影响、未重跑。

## 2026-09-22 14:30:00 · 表格四项色板改按用户指定参照表

**动因**（用户指令）：用户提供参照表 `<业务目录>\<产品>需求清单-20260922.xlsx`（业务侧既有交付表），要求「表头行、数据行、标题行、边框参照这个表修改」。

**取证**（先读后改，全量而非抽样）：
- 逐格提取该工作簿 11 张子表的填充色 / 字体色 / 边框色：填充 `F7F9FD`(852) / `1F3864`(118) / `D9E2F3`(36)；字体色 `262626`(1608) / `1F3864`(179) / `FFFFFF`(118)；边框全表统一 `B4C6E7`(8000 条边)。
- 结构模式（11 表一致）：章节标题栏 `1F3864` 16pt 白字 → 说明行（灰 595959）→ 小节标题行 `D9E2F3` + `1F3864` 字 → 表头行 `1F3864` 10.5pt 白字 → 数据行 `262626` 10pt。
- **隔行相位**：44 个数据行抽样核验，**首行数据行留白、次行起着色**，跨 11 表零例外（与 2026-09-21 客户表那版的相位相反，故相位需可配）。

**变更**（规格 + 实现 + 核验 + 文档）：
- `article-format.yaml`：`header_fill` `1F4E79`→`1F3864`；`title_row_text` `1F4E79`→`1F3864`；`band_fill` `F7F7F7`→`F7F9FD`；`band_start` `first`→`second`；`border_color` `BFBFBF`→`B4C6E7`；**新增 `data_text: "262626"`**（数据行文字色，此前未定义）；头注补记本次修订与参照来源。
- `scripts/spec_loader.py`：DEFAULT_SPEC 同步六项。
- `scripts/article_style.py`：新增 `TABLE_DATA_TEXT` 并接入 `style_tables()` 数据行分支（`bold=None` 保留数据格内 `**重点**` 加粗，只改字色）。
- `scripts/verify_article_style.py`：新增两条断言——「标题行字色」与「数据行字色」（逐 run 读 `w:color`，未写颜色的 run 视为不合规）。
- `SKILL.md`：规格摘要块、排版规格表「表格」行、「表格规格」节四项 + 说明（补 `band_start` 相位说明与色板实证源）。
- `references/spec.md`：规则九修订说明同步（含相位与参照表来源）。

**验证**：
- 结构核验：样例 md（3 张表）→ `verify_article_style.py` **96/96 PASS**（新增标题行字色、数据行字色两条），exit=0。
- **独立源值比对**（不经 yaml 中转，直接拿 xlsx 原值核 docx 输出）：表头底色 / 表头字色 / 标题行底色 / 标题行字色 / 数据行字色 / 隔行底纹 / 隔行相位 / 边框色 **八项 ALL MATCH**。
- 严格 schema：`officecli validate` 0 错误。
- 边界回归：数据格内 `**重点**` 加粗保留（实测 `重点行` bold=True 且字色 262626，同格未加粗的 `12` 保持 bold=False）。
- 渲染目检：`screenshot --render native` 出图——表头深蓝白字、标题行浅蓝合并居中、隔行自次行起、淡蓝细线边框，与参照表观感一致。
- 独立视觉验收子代理判定：**pass**（渲染件 `render/page1-v7.png`，其 `document.xml` 与最终产物 v8 逐字节一致，故判定对现版有效）。

**回滚**：`~/.zcode/tmp/af-backup-20260922b/article-format-pre-palette/`（本次改动前全量快照）。仅回退色板不必还原文件：把 `table` 节六项改回 `1F4E79` / `1F4E79` / `F7F7F7` / `first` / `BFBFBF` 并删 `data_text` 即可（核验断言按 yaml 取值，自动跟随）。

## 2026-09-22 14:15:15 · 表内字体字号改回宋体小四（深蓝主题保留）

**动因**（用户指令）：v1.6 里表内字体按全局偏好钉成微软雅黑 10 号，与规则九原文的「宋体小四」不一致；用户指令改回宋体小四。

**变更**（只动规格与文档，代码逻辑零改动；核验断言按 yaml 取值，自动跟随）：
- `article-format.yaml`：`table.font` 微软雅黑 → 宋体、`table.western` 微软雅黑 → Times New Roman、`table.font_size_pt` 10 → 12；表头底色 / 隔行 / 边框 / 重复表头等深蓝主题项全部保留；头注与 table 节注释改写（明确「独立 xlsx 表格用微软雅黑 10 号、文章内表格用宋体小四」为有意分立，并给出改字体与去装饰的两条操作路径）。
- `scripts/spec_loader.py`：DEFAULT_SPEC 同步三项（无配置文件时回落一致）。
- `scripts/article_style.py` / `md2docx.py` / `verify_article_style.py` / `make_reference_docx.py`：仅更新注释与 docstring 里的字体描述，无逻辑改动。
- `SKILL.md`：规格摘要块、排版规格表「表格」行、「表格规格」节表内文字行与说明条同步。
- `references/spec.md`：规则九修订说明里的字体句同步。

**验证**：样例 md（三张表）重跑 `md2docx.py` + `article_style.py` → `verify_article_style.py` **92/92 PASS**（含表内字体宋体、字号 12 磅断言，逐单元格读 `rFonts/@eastAsia` 与 `w:sz`）；`officecli validate` 0 错误；`screenshot --render native` 渲染目检：表格文字已为宋体小四（较上版明显变大、字形与正文一致），深蓝表头 / 隔行 / 网格线 / 合并标题行未受影响，三张表无截断错位，页脚页码居中正常。本轮为规格取值调整（无代码逻辑改动），目检由本会话直接核对渲染图完成，未重复派视觉验收子代理。

**备注**：全局规则「表格默认偏好」的载体归属条已写明「作为文章类文档的组成部分时，随该文档载体」——故本技能内表格用宋体小四与全局 xlsx 色板并不冲突，无需改全局规则。

## 2026-09-22 14:00:41 · 并入全局「表格默认偏好」：表格深蓝主题落地（v1.5 → v1.6）

**动因**（用户指令）：把全局规范 `%USERPROFILE%\.zcode\AGENTS.md` 的「表格默认偏好」并入文章规范。规则九原为「宋体小四 12 磅、表头加粗、无底色、无隔行着色」（2026-09-08 用户《排版格式要求》），此次按用户指令改为全局钉值色板：表头深蓝底 `#1F4E79` + 白色加粗字、数据行隔行 `#F7F7F7`、全表 `#BFBFBF` 灰细线、表内字体统一微软雅黑 10 号、表头行跨页重复（docx 里「冻结表头」的等价做法）、带独立标题行时浅蓝底 `#D9E2F3` + 深蓝字 `#1F4E79`、数据区禁止合并。色板取值与用户现有 xlsx 交付惯例逐项对齐（实测 `业务员客户销售从大到小再排列-20260921.xlsx`：标题行 D9E2F3/1F4E79、表头 1F4E79/白字、隔行 F7F7F7 自首行数据行起、边框 BFBFBF）。

**变更**（规格源 + 实现 + 核验 + 文档，共 8 个文件）：
- `article-format.yaml`：版本 1.5 → 1.6；`table` 节由三项扩为完整色板（font / western 微软雅黑、font_size_pt 10、header_fill、header_text、title_row_fill、title_row_text、title_row_bold、banding、band_fill、band_start、borders、border_color、border_size_eighths、repeat_header、first_line_indent、line_spacing、merge_data_area）；删除 `sizes_pt.table`（字号并入 `table.font_size_pt`，消除双份来源），表头加粗沿用 `bold.table_header` 不另设键。
- `scripts/spec_loader.py`：DEFAULT_SPEC 同步（version 1.6 + 新 table 节 + sizes_pt 去 table），保证无配置文件时回落值一致。
- `scripts/article_style.py`：**首次实现表格样式**——此前 yaml 的 `table` 节从未被代码读取（纯记录性配置，规则九实际由 md2docx 的 Table Grid 兜着）。新增 `style_tables()` 及 `_set_cell_shading` / `_set_table_borders` / `_set_row_repeat` / `_style_cell_text` / `_is_title_row` / `_insert_ordered`；`_force_black` 抽出通用 `_set_run_color(rPr, hex)`（供表头白字/标题行深蓝字复用）；`apply_article_style()` 末尾调用 `style_tables()`。
- `scripts/md2docx.py`：新增 `[[TABLETITLE]] 表 1 …` 标记行 → 表首整行合并标题行（显式标记，不按「表 1」文字猜测正文）；`_add_table` 改为只建表填字，外观统一交 article_style；单元格缩进改由样式层归零（`firstLineChars` 必须与 `firstLine` 同清，否则继承 Normal 的 2 字符缩进）。
- `scripts/verify_article_style.py`：规范九断言重写为「按 yaml 的 table 节取值核对」——表头底色 / 白字 / 加粗、标题行底色、隔行底纹（相位随 `band_start`）、网格线色、表头行跨页重复、表内字体字号、无首行缩进、数据区无合并单元格；规格回退到旧规则九时断言同步成立，不产生假红。
- `scripts/make_reference_docx.py`：pandoc 模板的表格样式改读 `table` 节（原读已删除的 `sizes_pt.table`），西文字体可随表内设定。
- `SKILL.md`：版本 1.6；新增「表格规格」节（部位—规格对照 + 回退方式 + 交付前渲染目检命令）；md 写法约定加 `[[TABLETITLE]]`；排版规格表与 yaml 摘要块同步；交付前抽查指向核验脚本。
- `references/spec.md`：规则九加 2026-09-22 修订说明（原文保留为历史依据），已知坑补第 12、13、14 条。
- `scripts/verify_article_style.py`（规范十）：新增「页脚无首行缩进」断言，按「段落 → 样式 → basedOn 链」解析有效缩进。

**验证**：
- 端到端：样例 md（3 张表——三列普通表 / 带标题行表 / 单列表）→ `md2docx.py` → `article_style.py` → `verify_article_style.py` **92/92 PASS**（exit=0，含新增页脚断言）。
- 严格 schema：`officecli validate` **0 errors**。首轮 12 errors 暴露两处真缺陷并修复——① `w:color` 裸 append 落到 `rPr` 末尾（CT_RPr 要求排在 `w:sz` 之前）；② `w:tblHeader w:val="true"` 枚举约束失败，改空元素。两坑已写入 references/spec.md 已知坑 12/13。
- 渲染目检：`officecli view <docx> screenshot --page 1 --render native` 出图，表头深蓝白字、数据行隔行浅灰、标题行浅蓝合并居中、灰细线网格、正文与标号未受影响。
- **独立视觉验收抓出并修复一处既有缺陷**：子代理量化判定「页脚页码未居中，整体右偏 ≈13px（3.5mm）」——`Footer` 样式 basedOn `Normal`，继承了 2 字符首行缩进，居中段带缩进即右偏半个缩进量（与本次表格改动无关，属旧缺陷）。已修：`_set_page_number_footer()` 显式把页脚段落 `firstLine`/`firstLineChars`/`left`/`leftChars` 归零；`_clear_first_line_indent()` 补 schema 顺序插入（`w:ind` 须排在 `w:jc` 之前）。核验器新增「页脚无首行缩进（有效缩进）」断言——**负向对照**：修复前产物精确 FAIL（有效 `firstLineChars=200`），修复后 PASS；同时把该坑写入 references/spec.md 已知坑 14（结构断言 `jc=center` 是代理，查不出真实位移）。
- **视觉复验（修复后重新渲染）**：子代理量化判定 **pass**——页脚数字墨迹中心 407.5px 与页面几何中心 407.5px 偏差 0.0px（修复前同点位 421.5px，右偏 14.0px，恰为 2 字符缩进的一半）；两版渲染逐像素比对仅 46 像素不同且全落在页脚数字区，标题 / 正文 / 三张表格 / 列表零位移；表头 #1F4E79 白字、标题行 #D9E2F3 整行合并、隔行 #F7F7F7 自首行数据行起、灰细线边框、正文缩进 2 字符、标题居中、无截断溢出均复验通过。
- **非缺陷观测（未改）**：三张表外框左边线比正文框左偏约 7.5px（≈2mm），与单元格默认左边距（108 twips）吻合，成因在渲染端表格定位换算；文档层为 `tblW auto` 且无 `tblInd`（网格合计 = 正文宽 8640 twips），两版渲染一致，判为非文档缺陷，未做改动。
- 验证件：`<验证目录>`（样例 md、成品 docx、渲染 PNG、核验输出）。

**回滚**：`~/.zcode/tmp/af-backup-20260922/article-format-snapshot-20260922/`（改动前全量快照，含 SKILL.md / yaml / scripts / references；反向复制即还原）。仅需回退表格外观时不必还原文件：改 yaml 的 `table` 节（见上「回退」说明）即可。

**备注**：本机 v1.6 属本地领先项（与 09-14 标题层级映射、09-15 schema 顺序修复同列），迁移包与源机 v1.5 均不含本改动。

## 2026-09-15 12:10 · 修复 numPr / abstractNum 插入顺序（OOXML schema 合规）

**动因**：office 自动化体检（对生成产物跑 OpenXML 严格校验）发现每份 md2docx 产物带 8–12 处 schema 违规——Heading 1-7 样式与列表段落的 `w:numPr` 被裸 append 到 pPr 末尾（ECMA-376 要求排在 spacing/ind/jc/outlineLvl 之前），numbering.xml 中新建的 abstractNum 追加在 `w:num` 之后。根因：本机 v1.5 版本的 article_style.py 丢失了旧版按序插入逻辑（`.bak-20260909-preconfig` / `.bak-20260910-preNormalFix` 中均有 `insert_numpr()` 函数）。影响：严格校验器（OpenXML SDK / OfficeCLI）报错；Word/WPS 容错可正常打开（WPS COM 实测 512 样式正常加载）。

**变更**（scripts/article_style.py；scripts/verify_article_style.py 同步加检查）：
- 新增 `_insert_numpr_ordered(pPr, numPr)`：按 ECMA-376 §17.3.1.26 顺序插到 spacing/ind/jc 等之前（`_PPR_AFTER_NUMPR` 含完整后继元素集合）
- 新增 `_insert_abstract_num_ordered(element, abstractNum)`：插到第一个 `w:num` 之前
- 四处调用点改用按序插入：`_add_abstract_num`、`_add_heading_multilevel_abstract`、`_ensure_heading_auto_number`（Heading 1-7 样式绑定）、`add_auto_numbered_list`（列表段落绑定）
- `verify_article_style.py` 新增「附 schema 顺序」2 条断言（numPr 位置合规 + abstractNum 先于 num）——修复前产物上实测 FAIL、修复后 PASS，防同类回归

**验证**：officecli `validate`：修复前 8（无列表样例）/ 12（含列表样例）错误 → 修复后 **0 errors**（两样例）；`verify_article_style.py` **62/62 PASS**（含新增附条）；`verify_docx.py` 双样例通过；WPS COM 实测打开 + 导出 PDF + 渲染目检（标题编号 1 / 1.1 / 2、列表 1-4、表格、页脚页码全正常）；负向对照（修复前产物）在新增检查下精确报出 7 样式 + 4 段落 + 8 处 abstractNum 错位。

**回滚**：`~/.zcode/tmp/af-backup-20260915/article-format-snapshot-20260915.tgz`（改动前全量快照，含本文件）。注：`scripts/article_style.py.bak-*` 因本机安全策略（Bash 不可直写技能目录）未落盘于脚本目录，回滚以快照 tgz 为准。

**备注**：迁移包（E 盘）未同步本修正，与源机版本分叉（与 heading-map 修正同为本地领先项）。

## 2026-09-14 10:17:43 · 本机修正：标题层级改按「编号段数」定级（`## 1 绪论` → H1）

**动因**（用户指令）：SKILL.md 教学骨架与实现不符——旧实现按 `#` 数定级，`## 1 绪论` 渲染为 Heading 2、`# 主标题` 变 Heading 1 参与编号，整族偏一级。要求 `## 1 绪论` 必须是 H1，在本机修正。

**变更**（scripts/md2docx.py 解析+渲染；SKILL.md 同步）：
- 标题层级改由「数字编号段数」决定：1 段→H1、2 段→H2 …… 7 段→H7；`#` 前缀数不参与定级（`## 1.1` 与 `### 1.1` 同为二级）
- 新增 title 节点：单个 `# ` 且无编号 → Title 样式（不进目录、不参与章节编号）；`--title` 已给或已有主标题时该行降级为一级（不丢内容）
- 无编号的 `##`~`#######` 行按「# 数 - 1」兜底（`## 概述` → 一级）
- 兼容保持：`# 1 引言`（带编号）仍为一级；编号独立成行写法不变；表格/列表/引用/跳级校验逻辑未动

**验证**：用户场景标题序列 Title→H1→H2→H2→H3→H3→H1→H2→H2→H1 全对且无编号残留；边界（`## 1.1`→H2、`###### 1.1.1`→H3、`######## 1.1.1.1`→H4）对；旧写法与 `--title` 并存行为对；verify_article_style 60/60 PASS（场景+旧样例各一遍）；verify_docx 通过；跳级负例 exit=1 拦截；stdin 模式 OK；officecli 渲染目检（编号阶梯 1→1.1→1.2→1.2.1→2→2.1→2.2→3）。验证件：`<验证目录>`。

**回滚**：`scripts/md2docx.py.bak-20260914-preheadingmap`、`SKILL.md.bak-20260914-preheadingmap`（反向复制即还原）。

**备注**：迁移包（E 盘 zip 与解压件）未同步本修正，与源机版本分叉；如需回灌另行处理。

## 2026-09-14 10:08:06 · 本机安装 v1.5（迁移包落地）

**来源**：`<迁移包>`（源版本 v1.5；包内 SKILL.md 原留源机路径 %USERPROFILE%\.zcode\skills\article-format，安装时适配为目标机本机路径共 1 处）。

**变更**：v1.0 → v1.5 覆盖安装：article-format.yaml / SKILL.md / scripts（md2docx、article_style、spec_loader、verify_docx）+ 新增 scripts/verify_article_style.py、references/spec.md；`~/.zcode/scripts/article-default.js` 换为动态 homedir 版（config.json 钩子条目未改动）；SKILL-TRIGGERS.md 第 194 行更新为 v1.5 触发词表（旧版备份 .bak-20260914-prearticleformatv15）。

**旧版遗留未动**：reference.docx、scripts/make_reference_docx.py、scripts/article_style.py.bak-2026*（pandoc 通道遗留，如需清理待定）。

**回滚**：`~/.zcode/tmp/article-format-upgrade-backup-20260914-100431`（旧全量 + manifest-old-md5.txt），反向复制即还原。

**验证**：端到端 md→docx 全链路通过——verify_article_style.py 60/60 PASS；verify_docx.py 通过；标题自动编号（Heading 1-7 绑定 numId=90 / ilvl 0-6，abstractNum 90 七级 lvlText %1…%1.%2…%7）；源稿手写编号剥离；标题跳级拦截（exit=1 + 行号定位）；stdin 安全模式；hook 脚本 JSON 合法 + 路径动态解析；officecli 渲染目检。验证件：`<本机工作目录>`。

**观察（待源机侧确认）**：SKILL.md「主标题用 `# `」描述与实现不符——实测 `# xxx` 渲染为 Heading 1（进入目录），主标题由 `--title` 参数生成（Title 样式、不进目录）；示例 `## 1 绪论` 按实现为 H2。本机未擅改文档表述。

## 2026-09-10 11:51:00 · 修复样式层字体残留（微软雅黑 / 标题蓝色）

**发现**：示例文档核验时拆 `styles.xml` 发现两处样式层残留——① `md2docx.py` 把 `Normal` 样式设为**微软雅黑 10.5pt**（`FONT_CN`，第 21/263/265 行），逐段设置 run 字体覆盖不到**空段落**（无 run），在空行直接键入即得微软雅黑小五；② Word 内置 `Heading 1-3` 样式自带 Office 主题字体与蓝色（`365F91` / `4F81BD`），在标题样式处键入会得到蓝色主题字。

**变更**：`article_style.py` 新增 `normalize_style_layer(doc)`，在 `convert()` 开头调用，按 `SPEC` 统一 `Normal` 与 `Heading 1-3` 的样式层：中文字体（宋体 / 黑体）、西文 Times New Roman、字号、加粗、黑色，并清除 `w:asciiTheme` 等主题字体属性。规格仍只由 `article-format.yaml` 决定，未改 `md2docx.py`。

**验证证据**：
- 样式层（`styles.xml`）：Normal=宋体/12pt/000000、Heading 1=黑体/15pt、Heading 2/3=黑体/14pt，均 `ascii=Times New Roman`，主题字体属性已清除
- 全文 `微软雅黑` 命中数 = 0（docx 所有 xml 部件）
- 可见段落回归：30 个非空段 0 异常（字体/字号/西文与改前一致）
- `verify_docx.py`：表格数、无空表格、标题数全部 PASS
- **WPS 真机渲染**：`KWPS.Application` COM 导出 PDF → 3 页全部目视核对通过（标题居中、正文缩进、三种标号顶格、表格表头加粗无底色、页脚「第 X 页」）

**回滚**：`scripts/article_style.py.bak-20260910-preNormalFix`（改动前副本，同目录）。

## 2026-09-10 11:23:20 · 统一排版规范（取消会议纪要「公文体」分支）

**变更指令**：分工红线改为「文章/制度/论文/报告/方案/会议纪要统一走 article_style.py 规范；删除 fangong_style.py；meeting-notes-expert 技能指向 article_style.py 规范」。

**变更前状态**：文章类文档走 `article-format`（`md2docx.py` + `article_style.py`，黑体标题/宋体正文/1.3 倍行距）；会议纪要另走「公文体」（`fangong_style.py`，宋体二号/三号 + 固定 28 磅行距 + 仿宋层标题），两套样式体系分设。

**变更后状态**：全部「文章类」文档（含会议纪要）统一走 `article-format` 一套规范与脚本；`fangong_style.py` 已删除，不再存在第二套样式体系。

### 改动文件清单（5 处）

| # | 文件 | 改动内容 |
|---|---|---|
| 1 | `skills/article-format/SKILL.md` | 前言/概述/执行步骤/分工红线共 5 处：删除「不用于会议纪要公文体」，改为「含会议纪要，已并入本规范」；分工红线段改为统一走本技能 |
| 2 | `skills/article-format/article-format.yaml` | 注释「生效范围」行：删除「会议纪要公文体走 fangong_style.py，不读本配置」，改为「含会议纪要——全部文章类文档统一读本配置」 |
| 3 | `scripts/article-default.js` | SessionStart 常驻规则：文档类型清单加入「会议纪要」；删除「会议纪要公文体用 tools/fangong_style.py」例外句，改为「会议纪要同样走本规范（已取消公文体分支）」 |
| 4 | `skills/meeting-notes-expert/SKILL.md` | 模板节标题 `一、`…`五、` 改为 `1`…`5`（与 article-format 标题序号约定一致）；「排版规范（公文格式）」整节重写为「排版规范（统一走 article-format 标准）」；工作流程第 5 步与约束节同步更新，补「表格不冻结窗格」 |
| 5 | `skills/SKILL-TRIGGERS.md` | 第 297 行 meeting-notes-expert 行说明由「含公文排版版」改为「排版统一走 article-format 规范」 |

### 删除文件

- `%USERPROFILE%\.zcode\tmp\AZY01-tools-backup-20260909\fangong_style.py`（5639 字节，当时唯一残存副本）

### 验证证据

- JS 语法：`node --check scripts/article-default.js` → 通过；实际运行输出合法 JSON（exit 0）
- YAML 解析：`yaml.safe_load(article-format.yaml)` → 通过，6 个顶层键完整
- 全链路冒烟：会议纪要样稿（5 节 + 1 表）经 `md2docx.py` → `article_style.py` → `verify_docx.py` 全部通过（exit 0；表格数一致、无空表格、标题数吻合）
- 样式抽查：主标题/一级 15pt/二级 14pt 标题黑体、正文宋体 12pt、西文 Times New Roman；Heading 1/2/3 的 outlineLvl = 0/1/2；正文首行缩进 firstLineChars=200；自动编号项 ind left=0 hanging=0（顶格）；页脚宋体 10.5pt
- 残留检索：活跃配置（skills / scripts / AGENTS.md / .agents / 工作区）内 `fangong` 零命中

### 回滚方式

各文件改动均为小范围文本替换。如需回退：
1. `SKILL-TRIGGERS.md`：`skills/SKILL-TRIGGERS.md.bak-20260910-110741-predeadfix` 含修改前该行原文（注意该备份早于同期新增的 dashi-ppt 段，勿整文件覆盖）。
2. 其余 4 个文件：按上表「改动内容」反做替换即可复原（原文均记录于本表与 2026-09-10 会话记录）。
3. `fangong_style.py` 如需恢复：可从 `%TEMP%` 或平台会话 artifact 中检索其原文重建；本记录保留其原始规格说明（宋体二号/三号 + 固定 28 磅行距 + 仿宋层标题）。
