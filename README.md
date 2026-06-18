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
- **P3 账户批量基础已完成**：已新增账号主页枚举、批量 runner、`index.json` 去重与断点续跑、`transcript` / `summary` 两种任务模式。
- **媒体兼容性已增强**：无系统 FFmpeg 时，会用 PyAV 将视频音频转为 16k WAV 再交给 FunASR。

当前仍未完成的是自动 AI 后端接入：账号批量流程已经强制走 `Refiner` 接口，但默认 CLI 只保留明确失败边界，避免把未经 AI 清洗的 ASR 原文伪装成最终文章。

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
3. **P3 账户批量（目标 2）**：yt-dlp 账户枚举 + 批量逐条 + 索引去重、断点续跑。
4. **P4 公开收藏（目标 1）**：收藏页枚举（先做免登录可行性 spike）。

文档：

- [当前计划 PLAN.md](docs/PLAN.md)（主线）
- [工作日志 WORKLOG.md](docs/WORKLOG.md)

已完成的早期成果（v0.1/v0.2）见工作日志。

## 当前可用命令

在 Skill 根目录下使用：

```powershell
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" pull <抖音视频链接> --out ./articles
```

生成一份含原始 FunASR 转写的 Markdown。

```powershell
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" request <抖音视频链接> --out ./articles
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" finalize <id>.request.json <id>.response.json --out ./articles
```

生成整理请求 JSON，再用代理或后端写响应 JSON，最终输出含核心观点和清洗原文的文章。

```powershell
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" account <抖音账号主页URL> --mode transcript --out ./articles
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" account <抖音账号主页URL> --mode summary --out ./articles
```

枚举账号主页视频并批量处理。`transcript` 产出 AI 清洗后的顺畅原文；`summary` 额外产出核心观点。当前批量命令需要接入自动 `Refiner` 后端后才能直接产出最终文章，否则会明确失败。

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
