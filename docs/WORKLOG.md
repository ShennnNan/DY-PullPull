# DY-PullPull 工作日志

## 项目概览

- **项目名**：DY-PullPull
- **目标**：将用户本人可访问的抖音收藏内容增量整理为本地 Markdown 文章。
- **交付形态**：首版为 Windows Codex Skill。
- **数据边界**：GitHub 只保存代码、Skill、模板和文档；登录态、数据库、文章和媒体留在本机。
- **当前阶段**：设计与实施规划完成，生产代码尚未开始。

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

## 下一步

按既定路线进入 v0.2 Local Media 的准备：

1. 先决策"从分享链接到本地音频的合法获取手段"，这决定 v0.2 的范围边界。
2. 按 Superpowers writing-plans 流程撰写 v0.2 详细实施计划（FFmpeg、CUDA 检测、`faster-whisper`、CPU 回退）。
3. 安装 FFmpeg 等 v0.2 运行依赖。
