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

## 2. 账号批量：只要顺畅原文

用于你的当前任务：拿一个账号主页链接，处理账号旗下可枚举视频，目标输出 AI 清洗后的顺畅原文。

```powershell
& $PYTHON $CLI account "<抖音账号主页URL>" --mode transcript
```

指定存放目录：

```powershell
& $PYTHON $CLI account "<抖音账号主页URL>" --mode transcript --out "D:\AI Skill\content-workspace\samples\李海涛（直男）"
```

需要复用浏览器登录态时：

```powershell
& $PYTHON $CLI account "<抖音账号主页URL>" --mode transcript --cookies-from-browser chrome
```

如果 Chrome cookies 被锁，先完全关闭 Chrome 再试。Edge 同理：

```powershell
& $PYTHON $CLI account "<抖音账号主页URL>" --mode transcript --cookies-from-browser edge
```

## 3. 账号批量：原文 + AI 总结

用于同时要核心观点和顺畅原文：

```powershell
& $PYTHON $CLI account "<抖音账号主页URL>" --mode summary
```

指定目录：

```powershell
& $PYTHON $CLI account "<抖音账号主页URL>" --mode summary --out "D:\AI Skill\content-workspace\samples\<账号名>"
```

最终文章结构：

```markdown
## 核心观点

...

## 原文

...
```

## 4. 输出文件怎么看

账号批量目录里会出现：

```text
index.json
.requests\
<video_id>.md
```

- `index.json`：批量状态、去重、断点续跑记录。
- `.requests\<video_id>.<mode>.request.json`：原始 ASR + AI 整理指令。
- `<video_id>.md`：最终文章。`transcript` 模式只有 `## 原文`；`summary` 模式有 `## 核心观点` 和 `## 原文`。

同一个目录、同一个模式重复运行时，已完成视频会跳过，失败视频会重试。

## 5. 当前重要边界

账号批量已经具备：账号枚举、逐条下载、FunASR 本地转写、请求文件写入、`index.json` 断点续跑。

但默认 CLI 还没有接入自动 AI Refiner。也就是说，直接运行 `account` 时，如果进入 AI 清洗阶段，当前会明确记录失败，避免把未经 AI 清洗的 ASR 原文当成最终原文。

现阶段可用两种方式完成最终文章：

1. 由 Codex 代理读取 `.requests` 里的整理请求，批量写响应并 finalize。
2. 下一步接入 OpenAI、本地模型或 Codex 文件流 Refiner，让 `account` 命令全自动产出最终文章。

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
