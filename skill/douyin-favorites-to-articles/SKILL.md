---
name: douyin-favorites-to-articles
description: 将用户本人可访问的抖音收藏或抖音分享链接增量整理为本地 Markdown 文章。用于首次初始化、添加链接、准备文章、校验并发布文章、查看处理状态、重试失败项目或清理临时数据。仅处理用户合法访问的内容；不得绕过登录、验证码、风控或访问控制。
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

## v0.1 单链接流程

1. 使用 `add-url <抖音链接> [--title 标题] [--author 作者]` 注册链接。
2. v0.1 仅接受已经存在的本地 UTF-8 转写文本。使用 `prepare <video-id> --transcript <文本路径>` 生成 `article-request.json`。
3. 读取 `article-request.json`。写文章前读取 [references/article-format.md](references/article-format.md)。
4. 将文章写入同一临时目录的 `article.md`。
5. 运行 `finalize <video-id> --article <article.md 路径>`。
6. 只有 CLI 输出 `completed` 后才向用户报告完成。

不要声称 v0.1 已经支持视频下载、Whisper、OCR 或收藏页自动抓取。

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
