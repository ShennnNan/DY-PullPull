# DY-PullPull 工作日志

## 项目概览

- **项目名**：DY-PullPull
- **目标**：两个最终目标 —— (1) 直接读取用户的公开收藏，把全部收藏内容的文本整理到本地；(2) 读取指定账户的全部原创视频，把每条的文本原文与总结整理到本地。
- **交付形态**：首版为 Windows Codex Skill。
- **数据边界**：GitHub 只保存代码、Skill、模板和文档；登录态、数据库、文章和媒体留在本机。
- **当前阶段**：v0.1 Foundation 与 v0.2 Local Media 已完成（单链接 → yt-dlp 下载 → faster-whisper 本地转写 → Markdown 文章已跑通）；批量采集（收藏页 / 账户作品）尚未开始。

## 2026-06-08：需求澄清

通过 Superpowers brainstorming 流程逐项确认了以下决策：

1. GitHub 不保存原始视频或私人分析数据。
2. 使用独立浏览器配置目录，用户首次扫码登录，后续复用登录态。
3. 收藏采用增量同步，以视频 ID 去重并支持断点续跑。
4. 分析结果使用 SQLite 保存结构化索引，每条视频生成一篇 Markdown。
5. 转写采用本地方案，优先使用 RTX 4060 Laptop 的 CUDA 能力，并提供 CPU 回退。
6. 最终长期保存文章，不保存原视频；音频和关键帧仅作为临时分析输入。
7. 每篇文章包含来源信息、摘要、整理后的正文、关键词、行动要点和提取说明。
8. 首版面向 Windows 10/11、Codex 用户和 100 条以内收藏。
9. 商品交付最初计划为闲鱼成交后发送 Skill ZIP，不建设授权服务器。
10. 仓库先私有开发，后续决策调整为公开展示。

同时评估过 BibiGPT 等链接总结服务。考虑 API 费用、隐私和长期可控性后，最终选择本地 Whisper/OCR 路线，由 Codex 完成文章整理。

## 2026-06-08：架构设计

批准的核心数据流：

```text
扫码登录
  -> 低频滚动收藏页
  -> 采集视频元数据
  -> 临时准备音频与关键帧
  -> faster-whisper + OCR
  -> Codex 生成 Markdown
  -> SQLite 更新状态
  -> 删除临时媒体
```

设计拆分为以下模块：

- `SKILL.md`：识别用户意图并编排工作流。
- `setup`：环境检测与初始化。
- `collector`：浏览器登录和收藏采集。
- `media`：临时媒体准备。
- `extractor`：Whisper 与 OCR。
- `writer`：Codex 文章整理。
- `storage`：SQLite、去重和状态管理。
- `doctor`：安装、登录、CUDA 和依赖诊断。
- `privacy`：本地数据隔离和发布排除规则。

设计文档提交：

- `6bf3fa0 docs: add douyin favorites skill design`

## 2026-06-08：实施计划

按照 Superpowers writing-plans 流程，将完整项目拆为四个可独立验收的版本：

1. **v0.1 Foundation**
   - Skill 骨架。
   - 抖音 URL 规范化和稳定视频 ID。
   - SQLite 状态机。
   - 临时工作区。
   - 本地转写文本到 Markdown 文章的 Codex 契约。
   - CLI 闭环和回归测试。

2. **v0.2 Local Media**
   - FFmpeg。
   - CUDA 检测。
   - `faster-whisper`。
   - CPU 回退和模型配置。

3. **v0.3 Favorites Collection**
   - 独立浏览器配置。
   - 手动扫码登录。
   - 收藏页增量采集。
   - 验证码与风控暂停。
   - 关键帧和 OCR。

4. **v0.4 Commercial Release**
   - `doctor`。
   - 敏感数据扫描。
   - 发布 ZIP。
   - 新 Windows 环境验收。

v0.1 计划包含逐步 TDD 测试、精确文件路径、验证命令和分任务提交说明。

实施计划提交：

- `a22eb8e docs: add v0.1 implementation plan`

## 2026-06-09：隔离开发环境

根据 Superpowers using-git-worktrees 流程：

- 在 `.gitignore` 中加入 `.worktrees/`。
- 创建分支 `codex/v0.1-foundation`。
- 创建隔离 worktree `.worktrees/v0.1-foundation`。

安全配置提交：

- `056079f chore: ignore local worktrees`

随后选择 Subagent-Driven Development 执行 Task 1。子代理在开始写代码前因使用额度限制中断，因此：

- 没有生成生产代码。
- 没有生成测试代码。
- 没有产生待合并提交。
- 主分支和隔离分支仍停留在 `056079f`。

## 2026-06-11：公开仓库准备

用户将仓库名称确定为 **DY-PullPull**，并要求建立公开 GitHub 项目。

本次公开化工作包括：

- 新增根目录 README，明确产品目标、范围和真实完成状态。
- 新增本工作日志。
- 将本机用户名和绝对路径从公开实施计划中移除。
- 扩充 `.gitignore`，排除登录态、密钥、数据库、日志、文章和媒体。
- 添加源码可见但保留全部权利的专有许可证。
- 准备将默认分支改为 `main` 并发布到 GitHub。

公开化材料提交：

- `d25349f docs: prepare DY-PullPull public project`

本地默认分支已由 `master` 更名为 `main`。GitHub 连接账户为
`ShennnNan`，检查时没有发现同名的 `DY-PullPull` 仓库。

GitHub 登录完成后，已创建公共仓库：

- https://github.com/ShennnNan/DY-PullPull

本地仓库已添加 `origin`，`main` 已推送并设置为跟踪
`origin/main`。公开仓库包含从设计、计划到公开化准备的完整提交历史。

## 2026-06-11：v0.1 Foundation 完成

环境准备：

- 安装 Python 3.12.10，并将开发目录迁出云同步盘，避免虚拟环境和 SQLite 锁文件与同步冲突。
- 重建分支 `codex/v0.1-foundation` 与隔离 worktree（上次中断时分支没有产生任何提交，无内容损失）。

按 v0.1 实施计划完成全部 9 个任务，每个任务先写失败测试、再实现、逐任务提交：

1. Skill 骨架与 Python 测试配置（`0354407`）。
2. 隔离本地数据路径（`d21fce7`）。
3. 抖音 URL 规范化与稳定视频 ID（`93d9d2d`）。
4. SQLite 幂等状态库（`3275ce5`）。
5. 临时工作区生命周期（`3bf5328`）。
6. 文章请求、校验、发布与索引契约（`b885f79`）。
7. 转写文本到文章的 CLI 闭环（`fd68766`）。
8. SKILL.md、参考文档与隐私说明（`ecad53e`）。
9. 失败保留现场的边界回归测试（`94835d5`）。

验收结果：

- 18 个自动测试全部通过。
- skill-creator `quick_validate.py` 校验通过。
- 一次性目录冒烟测试产出符合契约的 `article-request.json`。

执行中发现并修复的真实问题：

- skill-creator 的官方脚本按系统默认编码读取文件，在中文 Windows 上解码 UTF-8 中文文档会失败；调用时需使用 Python 的 UTF-8 模式（`-X utf8`）。
- Windows 工具写出的 UTF-8 转写文本通常带 BOM，原实现会把 `U+FEFF` 混入文章请求；改用 `utf-8-sig` 读取并补充回归测试。

分支已合并回 `main` 并推送。

## 2026-06-15：v0.2 媒体获取决策与端到端验证

确定 v0.2 的媒体获取方式。用户明确目标是"只给一个网页链接即可自动归档"，不接受手动提供视频文件，且后续要扩展到批量采集账户内容。

评估了四种"链接 → 本地音频"的获取手段：用户手动提供文件、浏览器辅助捕获、`yt-dlp`、系统音频环回录制。结论：

- 采用 **`yt-dlp`** 作为下载引擎。它专为"给链接取视频"设计，内置抖音解析器，单条与账户批量都支持；处理需要登录的收藏时复用用户本人浏览器 Cookie，属于用户合法访问范围，不绕过验证码或风控。
- 排除第三方"去水印"解析服务（隐私与可控性差），排除把浏览器基础设施提前到 v0.2（属于 v0.3 范围）。
- 架构上把"获取 URL 列表"与"下载单条"解耦，下载引擎统一为 `yt-dlp`：v0.2 处理单条链接，v0.3 负责账户作品枚举与收藏页采集，再逐条复用同一下载器。

端到端真实验证（一次性临时目录，未污染仓库）：以一条公开抖音链接跑通"yt-dlp 下载 → faster-whisper 转写 → v0.1 CLI 注册/准备/发布 → Markdown 文章"，最终状态 `completed`，临时媒体自动清除，合集索引刷新。

验证暴露的 v0.2 课题：

- CUDA 路径在转写迭代时报 `cublas64_12.dll not found`：本机有显卡驱动但缺 cuBLAS/cuDNN 运行库。v0.2 的 setup/doctor 需检测并引导安装相应运行库；回退逻辑要包住转写迭代而非仅模型加载。
- `faster-whisper` small 模型 CPU 模式：约 201 秒音频转写约 114 秒，出现较多同音字错误、连续重复幻觉段以及约 20 秒漏转写。v0.2 应在 GPU 可用时使用更大模型提升质量。
- `yt-dlp` 的中文元数据经 PowerShell 管道会按 GBK 乱码，应使用 `--write-info-json` 落盘后再读取。

## 2026-06-15：项目目录迁移

将工作目录完整迁移到 `D:\AI Skill\DY-pullpull`（此前为 `D:\DY-Pullpull`）。迁移前确认主分支干净、无未推送提交、v0.1 隔离 worktree 已合并；移除该 worktree 后整体搬迁，并在新位置重建虚拟环境，重新跑通全部 18 个测试，git 远端与历史完好。

## 2026-06-15：v0.2 Local Media 完成

按 v0.2 实施计划完成全部 8 个任务，沿用 v0.1 的 TDD + 逐任务提交节奏，在隔离 worktree `codex/v0.2-local-media` 上进行：

1. media/gpu 可选依赖组与依赖可用性测试（`3f74f37`）。
2. `devices.py` 设备/模型选择与 CPU 回退决策（`fa79b99`）。
3. `media.py` yt-dlp 下载封装与错误码映射（`ed41a8d`）。
4. `storage.update_metadata` 采集元数据回填（`84d6704`）。
5. `extractor.py` faster-whisper 转写封装，CUDA 失败在首次迭代处回退 CPU（`227bef0`）。
6. CLI `fetch` / `transcribe` / 一键 `pull` 命令与编排（`43331d4`）。
7. SKILL.md、错误码、`references/media.md` 文档与 Skill 校验（`11f1d8e`）。
8. 边界验收与日志同步（本条）。

关键设计决策：

- 下载引擎采用 `yt-dlp` 的 Python API（非外部二进制），需登录内容用 `--cookies-from-browser` 复用用户本人登录态。
- 基于演示发现 faster-whisper 通过内置 PyAV 直接解码下载的媒体，v0.2 **不再单独调用 FFmpeg 抽音频**；FFmpeg 推迟到 v0.3 关键帧/OCR。
- 设备/模型/精度可经 env 或命令行覆盖；默认 CUDA→large-v3/int8_float16，CPU→small/int8；任何 CUDA 失败自动回退 CPU 并在输出注明实际设备。
- `published_at` 经 workspace 元数据透传到文章请求，未改动 `videos` 表结构。

验收结果：

- 46 个单元测试通过、1 个真实下载集成测试默认跳过；外部工具在单测中以 fake 注入。
- 真实端到端：`pull <公开链接>` 实际下载 + 转写（本机缺 cuBLAS/cuDNN，CUDA 尝试后自动回退 cpu/small）→ 元数据回填标题/作者/发布日期 → 生成文章请求 → 写文章 → `finalize` → `completed`、临时媒体清除。
- Skill `quick_validate.py` 校验通过。

已知遗留（留待 v0.2 后续小迭代或 v0.4 doctor 处理）：本机缺 cuBLAS/cuDNN 运行库，GPU 加速尚未真正生效（当前全部走 CPU 回退）；`references/media.md` 已记录安装与排查方法。

分支已合并回 `main`。

## 2026-06-16：最终目标确认

用户明确了项目的两个最终目标，作为 v0.3 及后续范围的验收基准：

1. **公开收藏归档**：直接读取用户的公开收藏列表，把其中全部收藏内容的文本整理并保存到本地。
2. **账户作品归档**：读取指定账户的全部原创视频，对每条同时产出"文本原文"与"总结文本"，整理保存到本地。

与现有路线的关系：

- 两个目标都复用 v0.2 已完成的单链接管线（yt-dlp 下载 → faster-whisper 转写 → 文章生成），差异只在"如何枚举出待处理的 URL 列表"。
- 目标 1 对应原 v0.3 收藏采集，但优先走"公开收藏页"路径，尽量减少登录依赖；最终是否仍需扫码登录，取决于目标收藏是否对外公开，留待 v0.3 采集 spike 验证。
- 目标 2 是账户主页全部作品的枚举，属于 v0.3 批量采集范围的扩展。
- 交付物契约需调整：目标 2 要求把"转写原文"与"总结"作为两段分别保存，现有 article-format 以摘要 + 正文为主，需在 v0.3 设计时扩展文章模板。

本条目仅更新日志，不涉及代码改动。

## 2026-06-16：转写引擎决策（FunASR paraformer-zh 主，faster-whisper 备选）

当前优先级：先做出一套能用的系统、快速输出结果，质量靠后续迭代与 AI 后处理补足，而非一步到位追求最高转写精度。基于此调整转写引擎策略：

- **主引擎改为 FunASR `paraformer-zh`**：非自回归模型，在无 GPU 运行库的 CPU 环境也能快速产出中文结果，自带 VAD 与标点（ct-punc）；模型体积小，吞吐高。
- **faster-whisper 降为备选 / 回退**：GPU large-v3 在转写质量和中英混读上更强，保留用于后续质量迭代或特定场景。
- **转写出入交由 AI 填补**：转写文本若有同音字、漏字、英文术语音译等出入，由 Codex/AI 在文章整理阶段填补与校正，不要求 ASR 一次到位。

理由：

- 目标 2（账户全部作品批量）对吞吐敏感，paraformer-zh 在当前 CPU 环境即可快速出结果。
- 本机暂缺 cuBLAS/cuDNN，faster-whisper 现全程 CPU 回退；在补齐 GPU 前，paraformer-zh 是更快的 CPU 默认。
- 同为中文 + CPU 的实测对比中，paraformer-zh 用更小模型即获得比 whisper-small 更干净可用的结果。
- "速度优先 + AI 后处理纠错"符合"先能用、再迭代"的路线。

影响（待后续实施，本条仅为决策记录，代码尚未改动）：

- `extractor` 需新增 paraformer-zh 转写路径，引擎可配置；现有 faster-whisper 实现保留为 fallback。
- 依赖新增 `funasr` / `torch` / `torchaudio`；保留 faster-whisper 为可选组。
- `writer` / 文章契约强化"基于可能含错的转写做填补与校正"的提示约定。

## 2026-06-16：转向轻量可实现路径（原设计降为备选）

决定把项目主线从原 v0.1–v0.4 重设计，转为"今天已验证能跑通的轻量路径"，优先快速做出一套能用的系统，再迭代。

主线架构（保留 v0.2 的 yt-dlp，换掉转写引擎）：

```text
输入（单链接 / 账户主页 / 公开收藏页）
  -> 枚举视频 URL 列表
  -> 逐条：yt-dlp 下载 -> FunASR paraformer-zh 转写 -> AI 整理（原文清洗 + 总结）
  -> 保存本地 Markdown（原文 + 总结 + 来源）+ 索引去重 / 断点续跑
```

确认的取舍：

- 下载与枚举统一用 `yt-dlp`（账户与列表枚举是批量关键，原项目 v0.2 已在用）；今天试过的 majin72 parse 脚本留作单链接备用。
- 存储先用"文件夹 + 每条一份 `.md` + `index.json`"最简方案，暂不上 SQLite。
- 转写出入交由 AI 在整理阶段填补校正（见上一条引擎决策）。
- 原重设计（浏览器扫码登录、SQLite 状态机、OCR 关键帧、doctor、商业发布 ZIP、worktree/Subagent TDD 全流程）降为**备选计划**，当收藏必须登录或要做成商品时再启用。

阶段拆分（替换原 v0.1–v0.4，详见 `docs/PLAN.md`）：

- **P1 单条闭环**：link → 一份含转写的 md。
- **P2 AI 整理**：原文清洗 + 总结两段。
- **P3 目标 2（账户全部作品）**：yt-dlp 账户枚举 + 批量 + 索引断点续跑。
- **P4 目标 1（公开收藏）**：收藏页枚举（先做免登录可行性 spike）。

本条仅为方向与计划记录，代码尚未按新路径改动。

## 2026-06-16：P1 单条闭环完成

新建轻量包 `pullpull`（与重设计的 `dfa` 并存，复用其 `media`/`urls`/`models`，不引入 SQLite）：

- `pullpull/transcribe.py`：FunASR `paraformer-zh` 转写器，模型懒加载，导入不依赖 funasr，便于注入假实现做单测。
- `pullpull/pull.py`：单条编排 `下载 → 转写 → 写 md`，临时媒体用 `TemporaryDirectory` 用后即删；产物 ID 取 yt-dlp 落盘的真实视频 ID。
- `pullpull/cli.py` + `pullpull_cli.py`：命令行入口 `<url> --out <dir> [--cookies-from-browser]`。
- 下载复用 v0.2 的 `dfa.media`（yt-dlp + 依赖注入），转写引擎换成 FunASR。
- 产物为单份 Markdown：来源 frontmatter + 标题 + `## 原文`；`## 总结`留待 P2。

验收：

- 新增 3 个单元测试（render、下载+转写+写盘、临时媒体清理），用 FakeRunner / FakeTranscriber 注入；全套 51 passed / 2 skipped。
- 真实端到端（公开链接，输出在仓库外、不入库）：yt-dlp 取得真实 `video_id` / 作者 / 发布日期 → FunASR 转写 → 写出 md，临时媒体清除。
- **CPU 转写性能实测 RTF ≈ 0.17**（约 145 秒语音 24 秒转完），印证"FunASR 在 CPU 也快"的引擎决策。
- 开发环境：因原 `D:\AI Skill\DY-pullpull` 已不存在，在 `D:\AI Skills\DY PULLPULL\DY-PullPull` 重建检出；复用既有 FunASR venv，补装 yt-dlp / pytest / faster-whisper（备选引擎）。

## 2026-06-16：P2 整理契约与代码就绪（代理 handoff 进行中）

P2 的"AI 整理"后端选定**代理直接做**（Codex/Claude 充当整理器，零成本零安装，符合原项目避开付费 API 的取舍）。代码不能自己调模型，故采用**请求/响应文件契约**——既能让代理现在手动填，也能在 P3 让自动后端（Ollama/API）填同一份契约。

新增 `pullpull/article.py`：

- `RefineRequest` / `RefinedArticle` 数据契约 + `Refiner` 协议（自动后端的接口）。
- `DEFAULT_INSTRUCTIONS`：整理指令（不改原意、不增删事实，只清洗同音字/英文术语/断句 + 出中文要点总结）。
- `request_from_collected`、`write_request`/`read_request`、`parse_refined`（响应校验）、`render_article`（总结 + 原文两段）、`finalize`、`finalize_with_refiner`。

`pull.py` 重构：抽出 `collect()`（下载+转写，不落盘），`pull()`（P1）与 P2 的 `request` 流程共用。

CLI 改为子命令：`pull`（P1 原文 md）/ `request`（P2-A：链接 → 转写 → `<id>.request.json`）/ `finalize`（P2-B：request + response → 文章 md）。

进度与验收：

- 单元测试新增 8 个（契约往返、响应校验拒绝缺字段、render 总结在原文之前、finalize、自动后端 `finalize_with_refiner` 用假 refiner）；全套 **60 passed / 2 skipped**，P1 未回归。
- 真实代理 handoff 演示**进行到一半**：已生成真实视频的 `request.json`（含 855 字转写），**尚未**写 `response.json`、**尚未** `finalize`。

## 下一步

1. **收尾 P2 代理 handoff**：读 `request.json` → 代理写 `response.json`（summary + cleaned_transcript）→ `finalize` 产出文章 md，确认"原文 + 总结"两段成立。
2. **P3 目标 2（账户批量）**：用 yt-dlp 枚举账户主页全部作品，逐条复用 `collect` + 整理契约，加 `index.json` 去重与断点续跑。
3. （可选）补齐本机 cuBLAS/cuDNN，让 faster-whisper 备选档在 GPU 上可用。
