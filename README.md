# DY-PullPull

DY-PullPull 是一个正在设计中的 Windows Codex Skill，目标是把用户本人可访问的抖音收藏内容整理为本地 Markdown 文章。

计划中的完整流程：

```text
扫码登录
  -> 增量读取收藏链接
  -> 临时提取音频与关键帧
  -> 本地 Whisper / OCR
  -> Codex 提炼文章
  -> Markdown + SQLite
  -> 删除临时媒体
```

## 当前状态

项目目前处于 **设计与实施规划阶段**，尚未提供可运行的 Skill。

已经完成：

- 明确产品目标、用户范围与隐私边界。
- 完成总体架构、模块、数据流和测试设计。
- 完成 v0.1 基础闭环的 TDD 实施计划。
- 建立隔离开发分支，但尚未开始生产代码。

详细进展见 [工作日志](docs/WORKLOG.md)。

## 首版范围

- Windows 10/11。
- Codex Skill。
- 100 条以内个人收藏。
- 每条视频生成一篇 Markdown 文章。
- SQLite 增量状态与去重。
- NVIDIA CUDA 优先，CPU 回退。
- 原视频、音频和关键帧仅临时使用，成功后删除。

## 开发路线

1. **v0.1 Foundation**：链接入库、SQLite 状态、文章契约和临时数据清理。
2. **v0.2 Local Media**：FFmpeg、`faster-whisper`、CUDA 检测和 CPU 回退。
3. **v0.3 Favorites Collection**：独立浏览器登录、增量收藏采集、关键帧和 OCR。
4. **v0.4 Commercial Release**：环境诊断、敏感数据扫描、发布 ZIP 和干净 Windows 验收。

设计文档：

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
