import pytest

from dfa.devices import WhisperConfig
from dfa.extractor import ExtractionError, ExtractionResult, transcribe


class _Segment:
    def __init__(self, text):
        self.text = text


class _Info:
    def __init__(self, duration):
        self.duration = duration


class _Model:
    """伪模型。fail_on_device 指定的设备会在『迭代 segments』时抛错，模拟惰性 CUDA 失败。"""

    def __init__(self, device, fail_on_device):
        self.device = device
        self.fail_on_device = fail_on_device

    def transcribe(self, path, **kwargs):
        if self.fail_on_device and self.device == self.fail_on_device:
            def _raise():
                raise RuntimeError("Library cublas64_12.dll is not found")
                yield  # pragma: no cover

            return _raise(), _Info(0.0)
        return iter([_Segment(" 第一句 "), _Segment("第二句")]), _Info(12.5)


class FakeFactory:
    def __init__(self, fail_on_device=None):
        self.fail_on_device = fail_on_device
        self.calls = []

    def __call__(self, model, device, compute_type):
        self.calls.append((model, device, compute_type))
        return _Model(device=device, fail_on_device=self.fail_on_device)


CPU = WhisperConfig(device="cpu", model="small", compute_type="int8")
CUDA = WhisperConfig(device="cuda", model="large-v3", compute_type="int8_float16")


def test_transcribe_joins_segments_and_reports_metadata(tmp_path):
    media = tmp_path / "v.mp4"
    media.write_text("x", encoding="utf-8")
    factory = FakeFactory()

    result = transcribe(media, CPU, model_factory=factory)

    assert isinstance(result, ExtractionResult)
    assert result.transcript == "第一句\n第二句\n"
    assert result.device == "cpu"
    assert result.model == "small"
    assert result.duration == 12.5


def test_transcribe_falls_back_to_cpu_on_cuda_failure(tmp_path):
    media = tmp_path / "v.mp4"
    media.write_text("x", encoding="utf-8")
    factory = FakeFactory(fail_on_device="cuda")

    result = transcribe(media, CUDA, model_factory=factory)

    # 回退后设备为 cpu、模型为 cpu 默认；工厂被调用两次（先 cuda 后 cpu）
    assert result.device == "cpu"
    assert result.model == "small"
    assert [c[1] for c in factory.calls] == ["cuda", "cpu"]
    assert result.transcript == "第一句\n第二句\n"


def test_transcribe_raises_when_cpu_path_fails(tmp_path):
    media = tmp_path / "v.mp4"
    media.write_text("x", encoding="utf-8")
    factory = FakeFactory(fail_on_device="cpu")

    with pytest.raises(ExtractionError) as excinfo:
        transcribe(media, CPU, model_factory=factory)

    assert excinfo.value.code == "TRANSCRIPTION_FAILED"


def test_transcribe_raises_when_both_cuda_and_cpu_fail(tmp_path):
    media = tmp_path / "v.mp4"
    media.write_text("x", encoding="utf-8")

    class AlwaysFail(FakeFactory):
        def __call__(self, model, device, compute_type):
            self.calls.append((model, device, compute_type))
            return _Model(device=device, fail_on_device=device)

    factory = AlwaysFail()
    with pytest.raises(ExtractionError) as excinfo:
        transcribe(media, CUDA, model_factory=factory)

    assert excinfo.value.code == "TRANSCRIPTION_FAILED"
    assert [c[1] for c in factory.calls] == ["cuda", "cpu"]
