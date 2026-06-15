---
name: douyin-favorites-to-articles
description: 将用户本人可访问的抖音分享链接增量整理为本地 Markdown 文章。只需给出一条链接，即自动用 yt-dlp 下载视频、faster-whisper 本地转写（GPU 优先、CPU 回退），再生成文章。用于初始化、一键 pull、分步下载/转写、准备文章、校验并发布、查看状态、重试失败或清理临时数据。仅处理用户合法访问的内容；不得绕过登录、验证码、风控或访问控制。
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

## 分步命令（失败重试 / 断点续跑）

`pull` 等价于依次执行下列步骤；任一步失败后可单独重跑该步：

1. `add-url <抖音链接> [--title 标题] [--author 作者]`：注册链接。
2. `fetch <video-id> [--cookies-from-browser <浏览器>]`：下载媒体并回填标题/作者，状态置 `media_prepared`。
3. `transcribe <video-id> [--model <模型>] [--device <cuda|cpu>]`：本地转写，状态置 `extracted`，并生成 `article-request.json`。CLI 会打印实际使用的设备与模型。
4. `prepare <video-id> --transcript <文本路径>`：手动覆盖路径，当用户已有现成转写文本、想跳过自动转写时使用。

## 能力边界

- v0.2 已支持：单链接自动下载（yt-dlp）+ 本地语音转写（faster-whisper，GPU 优先、CPU 回退）。
- v0.2 尚未支持：收藏页/账户的批量自动采集、关键帧与 OCR。不要声称这些已可用。
- GPU 不可用时会自动回退 CPU，并在输出中注明实际设备。

## 状态与清理

- 使用 `status` 查看已注册条目。
- 使用 `cleanup --older-than-hours 24` 清理过期临时目录。
- `finalize` 成功后会立即删除该视频的临时目录。
- `finalize` 失败时读取 [references/error-codes.md](references/error-codes.md)，修复文章后重试。

## 内容约束

- 仅依据转写和 OCR 材料整理。
- 保留原链接。
- 不猜测缺失事实。
- 不发布、转载或上传视频内容。
- 遇到验证码或风控时暂停，要求用户手动处理。
