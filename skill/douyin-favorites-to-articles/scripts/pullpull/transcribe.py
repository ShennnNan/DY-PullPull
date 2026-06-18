from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Protocol


class Transcriber(Protocol):
    def transcribe(self, media_path: Path) -> str: ...


class FunasrTranscriber:
    """FunASR paraformer-zh 转写器；首次调用时加载模型并复用。

    模型在第一次 transcribe 时才加载，导入本模块不需要安装 funasr，
    便于在不触碰真实模型的情况下做单元测试（注入假的 Transcriber）。
    """

    def __init__(
        self,
        model: str = "paraformer-zh",
        vad_model: str = "fsmn-vad",
        punc_model: str = "ct-punc",
    ):
        self.model = model
        self.vad_model = vad_model
        self.punc_model = punc_model
        self._engine = None

    def _load(self):
        from funasr import AutoModel

        return AutoModel(
            model=self.model,
            vad_model=self.vad_model,
            punc_model=self.punc_model,
            disable_update=True,
        )

    def transcribe(self, media_path: Path) -> str:
        if self._engine is None:
            self._engine = self._load()
        with tempfile.TemporaryDirectory(prefix="pullpull-audio-") as tmp:
            input_path = _prepare_funasr_input(media_path, Path(tmp))
            result = self._engine.generate(input=str(input_path))
        if not result:
            return ""
        return str(result[0].get("text", "")).strip()


def _prepare_funasr_input(media_path: Path, workspace: Path) -> Path:
    """Return a WAV path FunASR can read without requiring system ffmpeg."""
    if media_path.suffix.lower() == ".wav":
        return media_path
    target = workspace / f"{media_path.stem}.wav"
    _convert_media_to_wav(media_path, target)
    return target


def _convert_media_to_wav(media_path: Path, target: Path) -> None:
    import av
    import numpy as np
    import soundfile as sf

    chunks = []
    with av.open(str(media_path)) as container:
        stream = next(
            (candidate for candidate in container.streams if candidate.type == "audio"),
            None,
        )
        if stream is None:
            raise ValueError(f"媒体文件没有可转写的音频轨：{media_path}")

        resampler = av.audio.resampler.AudioResampler(
            format="s16",
            layout="mono",
            rate=16000,
        )
        for packet in container.demux(stream):
            for frame in packet.decode():
                for resampled in resampler.resample(frame):
                    audio = resampled.to_ndarray()
                    if audio.ndim == 2:
                        audio = audio[0]
                    chunks.append(audio)

    if not chunks:
        raise ValueError(f"媒体文件未解码出音频：{media_path}")

    pcm = np.concatenate(chunks)
    sf.write(str(target), pcm, 16000, subtype="PCM_16")
