# 错误码

- `ARTICLE_VALIDATION_FAILED`：文章缺少必要章节、一级标题或原链接。根据 CLI 输出补齐文章，再重新执行 `finalize`。
- `AUTH_REQUIRED`：登录态不存在或已失效。后续浏览器版本必须暂停并要求用户手动登录。
- `HUMAN_VERIFICATION_REQUIRED`：出现验证码或风控。禁止自动绕过，等待用户手动处理。
- `SOURCE_UNAVAILABLE`：视频失效、私密或当前账号不可访问。`fetch` 时由 yt-dlp 判定。需登录的内容可加 `--cookies-from-browser <浏览器>` 复用用户本人登录态后重试；确属私密/失效则跳过该条。
- `MEDIA_PREPARE_FAILED`：下载失败或下载完成后未找到媒体文件。检查网络与链接有效性、确认 yt-dlp 为最新版本后重跑 `fetch`。抖音页面结构变化也可能触发，需升级 yt-dlp。
- `TRANSCRIPTION_FAILED`：faster-whisper 转写失败（CUDA 与 CPU 路径均失败）。检查依赖安装；GPU 运行库问题见 [media.md](media.md)，可用 `--device cpu` 强制 CPU 重试。
- `OCR_FAILED`：后续 OCR 版本提取失败；纯语音内容仍可继续。
