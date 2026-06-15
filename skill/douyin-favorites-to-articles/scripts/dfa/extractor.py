from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from dfa.devices import WhisperConfig


class ExtractionError(Exception):
    """携带稳定错误码的转写失败。"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ExtractionResult:
    transcript: str
    device: str
    model: str
    duration: float


class _Model(Protocol):
    def transcribe(self, path: str, **kwargs): ...


# model_factory(model, device, compute_type) -> 一个带 .transcribe 的模型对象。
ModelFactory = Callable[[str, str, str], _Model]


def _default_factory(model: str, device: str, compute_type: str) -> _Model:
    from faster_whisper import WhisperModel

    return WhisperModel(model, device=device, compute_type=compute_type)


def _run(media_path: Path, config: WhisperConfig, factory: ModelFactory) -> ExtractionResult:
    model = factory(config.model, config.device, config.compute_type)
    segments, info = model.transcribe(str(media_path), language="zh", beam_size=5)
    # 必须在此处真正迭代 segments：CUDA 运行库缺失等错误是惰性的，只有迭代时才抛出。
    lines = [segment.text.strip() for segment in segments]
    transcript = "\n".join(lines)
    if transcript:
        transcript += "\n"
    return ExtractionResult(
        transcript=transcript,
        device=config.device,
        model=config.model,
        duration=float(info.duration),
    )


def transcribe(
    media_path: Path,
    config: WhisperConfig,
    *,
    model_factory: ModelFactory = _default_factory,
) -> ExtractionResult:
    """转写媒体文件。GPU 路径失败时自动以 CPU 重试；都失败则报 TRANSCRIPTION_FAILED。"""
    try:
        return _run(media_path, config, model_factory)
    except Exception as error:  # noqa: BLE001
        if config.device == "cuda":
            try:
                return _run(media_path, config.cpu_fallback(), model_factory)
            except Exception as cpu_error:  # noqa: BLE001
                raise ExtractionError(
                    "TRANSCRIPTION_FAILED", f"CUDA 与 CPU 转写均失败：{cpu_error}"
                ) from cpu_error
        raise ExtractionError("TRANSCRIPTION_FAILED", f"转写失败：{error}") from error
