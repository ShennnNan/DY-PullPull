from __future__ import annotations

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
        result = self._engine.generate(input=str(media_path))
        if not result:
            return ""
        return str(result[0].get("text", "")).strip()
