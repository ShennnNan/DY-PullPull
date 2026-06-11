# 错误码

- `ARTICLE_VALIDATION_FAILED`：文章缺少必要章节、一级标题或原链接。根据 CLI 输出补齐文章，再重新执行 `finalize`。
- `AUTH_REQUIRED`：登录态不存在或已失效。后续浏览器版本必须暂停并要求用户手动登录。
- `HUMAN_VERIFICATION_REQUIRED`：出现验证码或风控。禁止自动绕过，等待用户手动处理。
- `SOURCE_UNAVAILABLE`：视频失效、私密或当前账号不可访问。
- `MEDIA_PREPARE_FAILED`：后续媒体版本无法生成临时音频或关键帧。
- `TRANSCRIPTION_FAILED`：后续 Whisper 版本转写失败。
- `OCR_FAILED`：后续 OCR 版本提取失败；纯语音内容仍可继续。
