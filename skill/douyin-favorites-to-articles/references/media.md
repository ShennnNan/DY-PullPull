# 媒体下载与本地转写

v0.2 通过 yt-dlp 下载媒体、faster-whisper 本地转写，把单条抖音链接自动变成文章请求。

## 依赖

- 下载与转写：`pip install -e ".[media]"`（包含 `yt-dlp`、`faster-whisper`）。
- GPU 加速（可选）：`pip install -e ".[gpu]"`（`nvidia-cublas-cu12`、`nvidia-cudnn-cu12`）。
- 无需单独安装系统 FFmpeg：faster-whisper 通过内置 PyAV 直接解码下载的媒体文件。FFmpeg 仅在后续版本的关键帧/OCR 中需要。

## 设备与模型配置

转写设备、模型、计算精度可用环境变量或命令行覆盖：

- `DFA_WHISPER_DEVICE`：`cuda` 或 `cpu`（对应 `transcribe --device`）。
- `DFA_WHISPER_MODEL`：如 `large-v3` / `medium` / `small`（对应 `transcribe --model`）。
- `DFA_WHISPER_COMPUTE`：如 `int8_float16` / `float16` / `int8`。

默认：探测到 CUDA 时用 `large-v3` / `int8_float16`（适配 8GB 显存）；否则用 `small` / `int8`。
任何 CUDA 失败都会自动回退 CPU，CLI 输出会注明实际使用的设备与模型。

## GPU 运行库故障

若转写报 `cublas64_*.dll is not found` 之类错误，说明缺少 CUDA 运行库：

1. 安装 GPU 依赖组：`pip install -e ".[gpu]"`。
2. CTranslate2 在 Windows 上可能需要把 `nvidia/cublas/bin`、`nvidia/cudnn/bin`（位于 venv 的 site-packages 内）加入 DLL 搜索路径（`os.add_dll_directory`）。
3. 仍失败时用 `transcribe --device cpu` 强制 CPU，先保证产出，再排查 GPU。

## 合规

- 仅下载用户本人合法可访问的内容。需登录的内容用 `--cookies-from-browser <浏览器>` 复用用户本人浏览器登录态，不保存密码、不绕过验证码或风控。
- 媒体文件仅作临时分析输入，`finalize` 成功后随临时目录一并删除。
