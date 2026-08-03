---
name: douyin-favorites-to-articles
description: 将用户本人可访问的抖音单条视频或指定账户的全部可枚举作品，增量整理为本地 Markdown 文章。支持 yt-dlp 下载、FunASR 本地转写、AI 清洗原文与总结、账户清单、样本验收和断点续跑。用于账户作品归档、单链接提炼、失败重试和临时数据清理。仅处理用户合法访问的内容；不得绕过登录、验证码、风控或访问控制。
---

# 抖音收藏文章提炼

将 Skill 根目录记为 `$SKILL_ROOT`。先解析可用的 Python：优先使用系统 `python`；如果系统命令不存在，使用 Codex 工作区依赖定位工具返回的 Python 可执行文件。将结果记为 `$PYTHON`。

使用：

```powershell
& $PYTHON "$SKILL_ROOT\scripts\dfa_cli.py" <参数>
```

## 初始化

先运行：

```powershell
& $PYTHON "$SKILL_ROOT\scripts\dfa_cli.py" init
```

默认数据保存在 `%LOCALAPPDATA%\DouyinFavoritesToArticles`。除非用户明确指定测试目录，不要把数据写入 Skill 或 Git 仓库。

## 单链接自动流程（推荐）

用户只需提供一条抖音视频链接。媒体与转写配置见 [references/media.md](references/media.md)。

1. 运行 `pull <抖音链接> [--cookies-from-browser <浏览器>]`：自动注册链接、用 yt-dlp 下载媒体、用 faster-whisper 本地转写，生成 `article-request.json`。处理需要登录的内容时，`--cookies-from-browser chrome`（或 edge/firefox）复用用户本人浏览器登录态。
2. 读取 `article-request.json`。写文章前读取 [references/article-format.md](references/article-format.md)。
3. 将文章写入同一临时目录的 `article.md`。
4. 运行 `finalize <video-id> --article <article.md 路径>`。
5. 只有 CLI 输出 `completed` 后才向用户报告完成。

## 账户作品归档

目标是把指定账户的全部可访问作品保存为一视频一篇 Markdown，文件名使用视频标题；`summary` 模式包含 `## 核心观点` 和 `## 原文`。

先尝试用 yt-dlp 直接枚举账户主页：

```powershell
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" account <账号主页URL> --mode transcript
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" account <账号主页URL> --mode summary
```

直接账户命令使用 `DEEPSEEK_API_KEY` 配置的后端整理文本；未配置时改用下述两阶段流程，并由当前代理生成 response。

若当前 yt-dlp 不支持该主页 URL，则用用户现有登录态打开账户主页，滚动作品列表至“暂时没有更多了”，采集可见的 `/video/<id>` 链接、标题与作者，写成 `account-manifest.json`。不得把页面作品计数误当成已采集数量；清单必须同时记录 `declared_count` 和 `accessible_count`，并明确任何差额。不要猜测或伪造不可访问作品。

对清单采用两阶段流程，先用少量样本验收，再移除 `--limit` 断点续跑全量：

```powershell
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" account-prepare <account-manifest.json> --mode summary --out <账户目录> --limit 3 --cookies-from-browser "edge:D:\path\to\profile"
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" account-refine --mode summary --out <账户目录>
```

`account-prepare` 逐条下载和转写，写入 `.requests/<id>.<mode>.request.json`；媒体仅在临时目录存在，转写结束即删除。读取 request 后生成同目录 response JSON：

```json
{
  "core_viewpoints": "仅依据转写整理的简洁总结",
  "cleaned_transcript": "纠正明显同音错字并整理断句后的完整原文"
}
```

若环境变量 `DEEPSEEK_API_KEY` 已配置，优先运行 `account-refine` 自动生成 response 并逐条定稿；默认模型是 `deepseek-v4-pro`，可用 `DEEPSEEK_MODEL` 覆盖。不得打印 API key。没有自动后端时，按上述 JSON 格式手动写 response，再逐条执行 `account-finalize`。

样本合格后，对同一输出目录重跑 `account-prepare` 且不传 `--limit`，再运行 `account-refine`；`index.json` 会跳过已准备或已完成的条目。失败条目保留阶段和错误信息，可在问题修复后重跑。

最终文章使用 `<视频标题>.md`。Windows 禁止的半角标点替换为等义全角标点，标题超过安全长度时截断并加省略号；同名视频使用 ` (2)` 等序号防止覆盖。旧版 `<video_id>.md` 用以下命令迁移并同步 `index.json`：

```powershell
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" account-rename-articles --out <账户目录>
```

- `transcript`：ASR 后用 AI 清洗错字、错句和断句，最终文章只输出 `## 原文`。
- `summary`：在 `transcript` 基础上总结核心观点，最终文章输出 `## 核心观点` 和 `## 原文`。
- 默认模式是 `transcript`。
- 始终尊重用户指定的输出目录；未指定时才使用 CLI 默认值。
- 批量任务会写 `index.json` 用于去重和断点续跑。
- 需要登录态时使用 `--cookies-from-browser chrome`、`edge`，或 `browser:profile-path` 指定未锁定的专用浏览器配置目录。只复用用户本人已有的登录态，不读取或展示 cookie 值。
- 不要把未经 AI 清洗的 ASR 原文伪装成最终文章；只有 `account-finalize` 成功且索引状态为 `completed` 才算完成。

手动整理单条 request 时，`finalize` 也支持同样的模式：

```powershell
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" finalize <id>.request.json <id>.response.json --mode transcript
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" finalize <id>.request.json <id>.response.json --mode summary
```

## 分步命令（失败重试 / 断点续跑）

`pull` 等价于依次执行下列步骤；任一步失败后可单独重跑该步：

1. `add-url <抖音链接> [--title 标题] [--author 作者]`：注册链接。
2. `fetch <video-id> [--cookies-from-browser <浏览器>]`：下载媒体并回填标题/作者，状态置 `media_prepared`。
3. `transcribe <video-id> [--model <模型>] [--device <cuda|cpu>]`：本地转写，状态置 `extracted`，并生成 `article-request.json`。CLI 会打印实际使用的设备与模型。
4. `prepare <video-id> --transcript <文本路径>`：手动覆盖路径，当用户已有现成转写文本、想跳过自动转写时使用。

## 能力边界

- v0.2 已支持：单链接自动下载（yt-dlp）+ 本地语音转写（faster-whisper，GPU 优先、CPU 回退）。
- 已支持：账户主页直接枚举，或在 yt-dlp 不支持主页时从浏览器生成清单；账户批量转写、AI 整理、断点续跑和逐条归档。
- 尚未支持：从页面计数恢复不可访问作品、关键帧与 OCR。不要声称这些已可用。
- GPU 不可用时会自动回退 CPU，并在输出中注明实际设备。

## 状态与清理

- 使用 `status` 查看已注册条目。
- 使用 `cleanup --older-than-hours 24` 清理过期临时目录。
- `finalize` 成功后会立即删除该视频的临时目录。
- `finalize` 失败时读取 [references/error-codes.md](references/error-codes.md)，修复文章后重试。

## 内容约束

- 仅依据转写材料整理；未启用 OCR 时不补写画面中才出现的信息。
- 保留原链接。
- 不猜测缺失事实。
- 不发布、转载或上传视频内容。
- 遇到验证码或风控时暂停，要求用户手动处理。
