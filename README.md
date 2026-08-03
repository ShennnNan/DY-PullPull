# DY-PullPull

DY-PullPull 是一个 Windows Codex Skill。两个最终目标：

1. **公开收藏归档**：直接读取用户的公开收藏，把全部收藏内容的文本整理到本地。
2. **账户作品归档**：读取指定账户的全部原创视频，把每条的文本原文与总结整理到本地。

两者都复用同一条单链接管线（下载 → 本地转写 → 整理），差异只在如何枚举出待处理的链接。

当前主线流程（轻量可实现路径）：

```text
输入（单链接 / 账户主页 / 公开收藏页）
  -> 枚举视频 URL 列表
  -> 逐条：yt-dlp 下载 -> FunASR 本地转写 -> AI 整理（原文清洗 + 总结）
  -> 保存本地 Markdown（原文 + 总结 + 来源）+ 索引去重
```

> 原"扫码登录 + SQLite + OCR + 商业发布"的完整设计已降为备选计划，详见 [docs/PLAN.md](docs/PLAN.md)。

## 当前状态

项目当前主线已经从早期重设计切换为 **轻量可实现路径**：

- **P1 单条闭环已完成**：一条抖音视频链接可以自动经 `yt-dlp` 下载、FunASR `paraformer-zh` 本地转写，并生成含 `## 原文` 的 Markdown。
- **P2 AI 整理契约已完成**：`request` / `finalize` 流程支持把原始转写交给代理或后端清洗，生成 `## 核心观点` + `## 原文`。
- **P3 账户作品归档已跑通**：支持账号主页枚举或浏览器清单回退、批量下载、FunASR 转写、DeepSeek 自动整理、`index.json` 断点续跑及标题文件名。
- **媒体兼容性已增强**：无系统 FFmpeg 时，会用 PyAV 将视频音频转为 16k WAV 再交给 FunASR。

真实账户验收已完成：主页显示 13 条作品，浏览器实际枚举到 12 条可访问作品；12 条均完成转写、总结和本地归档，0 失败。不可访问的差额只记录，不猜测内容。

已经完成的主要模块：

- 明确产品目标、用户范围与隐私边界。
- 完成 v0.1 Foundation：Skill 骨架、URL 规范化、SQLite 状态机、临时工作区、文章契约与 CLI 闭环。
- 完成 v0.2 Local Media：`yt-dlp` 下载、媒体元数据回填、本地 ASR 转写、端到端文章产出。
- 完成轻量 `pullpull` 主线：FunASR 单条闭环、AI 整理契约、账号枚举与批处理基础。

详细进展见 [工作日志](docs/WORKLOG.md)。

## 首版范围

- Windows 10/11。
- Codex Skill。
- 100 条以内个人收藏。
- 每条视频生成一篇 Markdown 文章。
- SQLite 增量状态与去重。
- NVIDIA CUDA 优先，CPU 回退。
- 原视频、音频和关键帧仅临时使用，成功后删除。

## 开发路线（当前主线）

1. **P1 单条闭环**：链接 → 一份含转写的 Markdown。
2. **P2 AI 整理**：原文清洗纠错 + 生成总结，两段分别保存。
3. **P3 账户批量（目标 2）**：已完成；yt-dlp 账户枚举或浏览器清单回退 + 批量逐条 + AI 整理 + 索引去重、断点续跑。
4. **P4 公开收藏（目标 1）**：收藏页枚举（先做免登录可行性 spike）。

文档：

- [当前计划 PLAN.md](docs/PLAN.md)（主线）
- [工作日志 WORKLOG.md](docs/WORKLOG.md)
- [本地使用手册](docs/customer/local-usage.md)

已完成的早期成果（v0.1/v0.2）见工作日志。

## 当前可用命令

在 Skill 根目录下使用：

```powershell
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" pull <抖音视频链接> --out ./articles
```

生成一份含原始 FunASR 转写的 Markdown。

```powershell
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" request <抖音视频链接> --out ./articles
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" finalize <id>.request.json <id>.response.json --mode summary --out ./articles
```

生成整理请求 JSON，再用代理或后端写响应 JSON。`--mode transcript` 只输出清洗原文；`--mode summary` 输出核心观点和清洗原文。

配置 `DEEPSEEK_API_KEY` 后，先尝试直接账户流程：

```powershell
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" account <抖音账号主页URL> --mode summary --out <账户目录> --cookies-from-browser edge
```

若当前 yt-dlp 不支持账户主页 URL，则由 Codex 使用用户现有浏览器登录态滚动作品页，生成同时记录 `declared_count` / `accessible_count` 的 `account-manifest.json`，再执行可验收、可续跑的两阶段流程：

```powershell
# 先试 2 条
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" account-prepare <account-manifest.json> --mode summary --out <账户目录> --limit 2 --cookies-from-browser "edge:D:\path\to\profile"
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" account-refine --mode summary --out <账户目录>

# 样本通过后续跑全量；前 2 条自动跳过
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" account-prepare <account-manifest.json> --mode summary --out <账户目录> --cookies-from-browser "edge:D:\path\to\profile"
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" account-refine --mode summary --out <账户目录>
```

每条最终保存为 `<视频标题>.md`，包含来源、发布日期、`## 核心观点` 和 `## 原文`。Windows 非法文件名符号会替换为等义全角符号；同名作品使用 ` (2)` 后缀，不会相互覆盖。历史 `<video_id>.md` 可迁移：

```powershell
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" account-rename-articles --out <账户目录>
```

完整本地操作与故障恢复见 [本地使用手册](docs/customer/local-usage.md)。

### 备选计划（原重设计）

原"扫码登录 + SQLite 状态机 + OCR 关键帧 + 环境诊断 + 商业发布 ZIP"的 v0.1–v0.4 完整设计已降为备选，当收藏必须登录或需做成商品时再启用：

- [完整设计](docs/superpowers/specs/2026-06-08-douyin-favorites-codex-skill-design.md)
- [v0.1 实施计划](docs/superpowers/plans/2026-06-08-douyin-favorites-v0.1-foundation.md)

## 隐私与合规

- 仅处理用户本人合法访问的内容。
- 不保存抖音密码，不绕过验证码、风控或访问控制。
- 登录态、数据库、文章、日志和临时媒体不得提交到仓库。
- 项目不提供自动转载、二次上传或规避平台限制的功能。
- 使用者应自行遵守平台条款、版权和隐私要求。

## 许可证

仓库公开仅用于展示和协作评估，当前不是开源软件。除非另有书面授权，不得复制、再分发、转售或用于商业交付。详见 [LICENSE](LICENSE)。
