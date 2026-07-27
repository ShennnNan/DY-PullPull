# DY-PullPull 本地使用手册

这份手册按本机路径写，适合直接在 Windows PowerShell 里试验。

## 1. 基础路径

```powershell
$REPO = "D:\AI Skill\DY-pullpull"
$PYTHON = "$REPO\.venv\Scripts\python.exe"
$CLI = "$REPO\skill\douyin-favorites-to-articles\scripts\pullpull_cli.py"
cd $REPO
```

默认内容存放根目录：

```text
D:\AI Skill\content-workspace\samples
```

账号批量命令如果不写 `--out`，会自动写到：

```text
D:\AI Skill\content-workspace\samples\<账号名>
```

如果 yt-dlp 没拿到账号名，会写到稳定兜底目录：

```text
D:\AI Skill\content-workspace\samples\account-<12位hash>
```

命令运行后会打印实际目录：

```text
out: D:\AI Skill\content-workspace\samples\<账号名>
total: ...
completed: ...
skipped: ...
failed: ...
```

## 2. 配置 AI 整理后端

自动批量整理使用环境变量中的 DeepSeek API key。不要把 key 写进仓库或文章目录：

```powershell
$env:DEEPSEEK_API_KEY = "<你的 key>"
```

默认模型为 `deepseek-v4-pro`；需要覆盖时设置 `DEEPSEEK_MODEL`。

## 3. 先尝试 yt-dlp 直接账户流程

需要“核心观点 + 完整原文”时运行：

```powershell
& $PYTHON $CLI account "<抖音账号主页URL>" --mode summary --out "<账户目录>" --cookies-from-browser edge
```

只需要 AI 清洗后的完整原文时把模式改成 `transcript`。如果浏览器数据库被锁，可关闭浏览器后重试，或使用未锁定的专用配置目录：

```powershell
--cookies-from-browser "edge:D:\path\to\profile"
```

## 4. yt-dlp 不支持主页时的可行流程

1. 用 Codex 打开用户本人可访问的账户主页，滚动作品列表直到“暂时没有更多了”。
2. 把可见的 `/video/<id>` 链接、标题和作者写入 `account-manifest.json`。
3. 清单同时记录页面显示的 `declared_count` 和实际采集的 `accessible_count`；有差额时只记录，不猜测不可访问内容。
4. 先跑 2 条样本：

```powershell
& $PYTHON $CLI account-prepare "<account-manifest.json>" --mode summary --out "<账户目录>" --limit 2 --cookies-from-browser "edge:D:\path\to\profile"
& $PYTHON $CLI account-refine --mode summary --out "<账户目录>"
```

5. 检查样本的来源、发布日期、核心观点和完整原文。通过后移除 `--limit`，续跑全量：

```powershell
& $PYTHON $CLI account-prepare "<account-manifest.json>" --mode summary --out "<账户目录>" --cookies-from-browser "edge:D:\path\to\profile"
& $PYTHON $CLI account-refine --mode summary --out "<账户目录>"
```

`index.json` 会跳过已准备或已完成条目；失败项记录 `stage` 和 `error`，修复后重跑相同命令即可。

如果没有自动 AI 后端，由 Codex 读取 `.requests\*.request.json`，写出包含 `core_viewpoints` 和 `cleaned_transcript` 的 response JSON，再逐条运行 `account-finalize`。

## 5. 输出文件和命名

账户目录结构：

```text
account-manifest.json
index.json
.requests\
<视频标题>.md
```

- `account-manifest.json`：账户清单与页面计数差额。
- `index.json`：状态、去重和断点续跑记录。
- `.requests\<video_id>.<mode>.request.json`：原始 ASR 和整理请求。
- `.requests\<video_id>.<mode>.response.json`：AI 清洗原文和总结。
- `<视频标题>.md`：最终文章；技术索引仍保留视频 ID，但面向用户的 Markdown 使用标题文件名。

Windows 不允许的半角标点会换成等义全角标点；标题过长会安全截断；同名作品用 ` (2)` 等序号区分。旧归档可迁移并同步 `index.json`：

```powershell
& $PYTHON $CLI account-rename-articles --out "<账户目录>"
```

转写期间的音视频只存在于临时目录，完成后自动删除。

## 6. 单条视频试跑

只生成原始 ASR Markdown：

```powershell
& $PYTHON $CLI pull "<抖音视频链接>" --out "D:\AI Skill\content-workspace\samples\_single"
```

生成 AI 整理请求：

```powershell
& $PYTHON $CLI request "<抖音视频链接>" --out "D:\AI Skill\content-workspace\samples\_single"
```

手动或由 AI 写同名响应 JSON，例如 `123.response.json`：

```json
{
  "cleaned_transcript": "清洗后的顺畅原文",
  "summary": "核心观点总结"
}
```

只输出顺畅原文：

```powershell
& $PYTHON $CLI finalize "D:\AI Skill\content-workspace\samples\_single\123.request.json" "D:\AI Skill\content-workspace\samples\_single\123.response.json" --mode transcript --out "D:\AI Skill\content-workspace\samples\_single"
```

输出核心观点 + 顺畅原文：

```powershell
& $PYTHON $CLI finalize "D:\AI Skill\content-workspace\samples\_single\123.request.json" "D:\AI Skill\content-workspace\samples\_single\123.response.json" --mode summary --out "D:\AI Skill\content-workspace\samples\_single"
```

## 7. 自检命令

查看账号命令帮助：

```powershell
& $PYTHON $CLI account --help
```

查看 finalize 命令帮助：

```powershell
& $PYTHON $CLI finalize --help
```

跑测试：

```powershell
& $PYTHON -m pytest -q
```

## 8. 失败时发给我的信息

如果你试跑失败，把这些内容发给我即可：

```text
账号主页 URL：
运行的完整命令：
命令输出的 failed / error：
输出目录里的 index.json：
.requests 目录里对应的 request.json：
是否用了 --cookies-from-browser：
```

这样我可以直接接着定位是账号枚举、cookies、下载、转写还是 AI Refiner 边界的问题。
