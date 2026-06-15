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

项目已完成 **v0.2 Local Media**：Skill 现在只需一条抖音链接，即可自动用 yt-dlp 下载视频、faster-whisper 本地转写（GPU 优先、CPU 回退），生成 Markdown 文章。收藏页/账户批量采集与 OCR（v0.3）尚未开始。

> 2026-06-16 起，项目转向轻量可实现路径，转写主引擎改为 FunASR `paraformer-zh`（faster-whisper 备选），按 P1–P4 推进，详见 [docs/PLAN.md](docs/PLAN.md)。上述 v0.1/v0.2 代码现状仍为 faster-whisper，新路径尚未实施。

已经完成：

- 明确产品目标、用户范围与隐私边界。
- 完成总体架构、模块、数据流和测试设计。
- 完成 v0.1 Foundation：Skill 骨架、URL 规范化、SQLite 状态机、临时工作区、文章契约与 CLI 闭环。
- 完成 v0.2 Local Media：一键 `pull` 自动下载（yt-dlp）+ 本地语音转写（faster-whisper，CUDA→CPU 回退），元数据自动回填，端到端验证产出文章。

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
