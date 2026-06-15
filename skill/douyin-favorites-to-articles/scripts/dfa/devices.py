from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

# 各设备的默认模型与计算精度。
# CUDA 默认用 large-v3 量化（适配 8GB 显存，质量优先）；CPU 默认用 small（速度优先）。
_CUDA_DEFAULT_MODEL = "large-v3"
_CUDA_DEFAULT_COMPUTE = "int8_float16"
_CPU_DEFAULT_MODEL = "small"
_CPU_DEFAULT_COMPUTE = "int8"


def _default_model(device: str) -> str:
    return _CUDA_DEFAULT_MODEL if device == "cuda" else _CPU_DEFAULT_MODEL


def _default_compute(device: str) -> str:
    return _CUDA_DEFAULT_COMPUTE if device == "cuda" else _CPU_DEFAULT_COMPUTE


@dataclass(frozen=True)
class WhisperConfig:
    device: str
    model: str
    compute_type: str
    # 用户是否通过 env 显式指定了模型。回退到 CPU 时，显式模型保留，
    # 否则改用 CPU 默认模型（避免在 CPU 上硬跑 large-v3 拖垮速度）。
    model_explicit: bool = False

    def cpu_fallback(self) -> "WhisperConfig":
        model = self.model if self.model_explicit else _CPU_DEFAULT_MODEL
        return WhisperConfig(
            device="cpu",
            model=model,
            compute_type=_CPU_DEFAULT_COMPUTE,
            model_explicit=self.model_explicit,
        )


def resolve_whisper_config(
    env: Mapping[str, str],
    cuda_available: bool,
) -> WhisperConfig:
    """根据环境变量与 CUDA 探测结果决定使用的设备、模型与计算精度。

    优先级：显式 env > 按设备的默认值。显式指定 device=cuda 即使探测不可用也尊重，
    由运行时转写回退兜底，而不在配置阶段否决用户选择。
    """
    device = env.get("DFA_WHISPER_DEVICE") or ("cuda" if cuda_available else "cpu")

    model_override = env.get("DFA_WHISPER_MODEL")
    model = model_override or _default_model(device)
    compute_type = env.get("DFA_WHISPER_COMPUTE") or _default_compute(device)

    return WhisperConfig(
        device=device,
        model=model,
        compute_type=compute_type,
        model_explicit=model_override is not None,
    )
