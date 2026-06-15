from dfa.devices import WhisperConfig, resolve_whisper_config


def test_default_prefers_cuda_large_when_available():
    config = resolve_whisper_config(env={}, cuda_available=True)
    assert config.device == "cuda"
    assert config.model == "large-v3"
    assert config.compute_type == "int8_float16"


def test_default_falls_back_to_cpu_small_without_cuda():
    config = resolve_whisper_config(env={}, cuda_available=False)
    assert config.device == "cpu"
    assert config.model == "small"
    assert config.compute_type == "int8"


def test_env_overrides_model_and_compute():
    config = resolve_whisper_config(
        env={"DFA_WHISPER_MODEL": "medium", "DFA_WHISPER_COMPUTE": "float16"},
        cuda_available=True,
    )
    assert config.device == "cuda"
    assert config.model == "medium"
    assert config.compute_type == "float16"


def test_explicit_cpu_device_env_ignores_cuda_availability():
    config = resolve_whisper_config(env={"DFA_WHISPER_DEVICE": "cpu"}, cuda_available=True)
    assert config.device == "cpu"
    assert config.model == "small"
    assert config.compute_type == "int8"


def test_explicit_cuda_device_env_overrides_unavailable_probe():
    # 用户强制 cuda：尊重其选择，由运行时回退兜底，而非在配置阶段否决。
    config = resolve_whisper_config(env={"DFA_WHISPER_DEVICE": "cuda"}, cuda_available=False)
    assert config.device == "cuda"
    assert config.model == "large-v3"


def test_cpu_fallback_keeps_model_overridable():
    config = resolve_whisper_config(env={}, cuda_available=True)
    fallback = config.cpu_fallback()
    assert fallback.device == "cpu"
    assert fallback.compute_type == "int8"
    assert fallback.model == "small"


def test_cpu_fallback_respects_explicit_model():
    config = resolve_whisper_config(env={"DFA_WHISPER_MODEL": "medium"}, cuda_available=True)
    fallback = config.cpu_fallback()
    assert fallback.device == "cpu"
    assert fallback.model == "medium"
