import pytest

from backend.config import Settings, load_settings


def test_settings_default_to_the_captured_release_model() -> None:
    settings = Settings(gemini_api_key="test-key", _env_file=None)

    assert settings.gemini_model == "gemini-3.5-flash"


def test_settings_accepts_a_gemini_model() -> None:
    settings = Settings(
        gemini_api_key="test-key",
        gemini_model="gemini-3.5-flash",
        _env_file=None,
    )

    assert settings.gemini_model == "gemini-3.5-flash"
    assert settings.gemini_thinking_level == "low"
    assert settings.gemini_request_timeout_ms == 180_000


def test_settings_rejects_a_non_gemini_model_id() -> None:
    with pytest.raises(ValueError, match="Gemini model ID"):
        Settings(
            gemini_api_key="test-key",
            gemini_model="other-provider-model",
            _env_file=None,
        )


def test_settings_normalises_a_supported_thinking_level() -> None:
    settings = Settings(
        gemini_api_key="test-key",
        gemini_thinking_level=" LOW ",
        _env_file=None,
    )

    assert settings.gemini_thinking_level == "low"


def test_settings_rejects_an_invalid_thinking_level() -> None:
    with pytest.raises(ValueError, match="GEMINI_THINKING_LEVEL"):
        Settings(
            gemini_api_key="test-key",
            gemini_thinking_level="off",
            _env_file=None,
        )


def test_settings_rejects_a_non_positive_request_timeout() -> None:
    with pytest.raises(ValueError, match="GEMINI_REQUEST_TIMEOUT_MS"):
        Settings(
            gemini_api_key="test-key",
            gemini_request_timeout_ms=0,
            _env_file=None,
        )


def test_missing_settings_have_a_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_THINKING_LEVEL", raising=False)
    monkeypatch.delenv("GEMINI_REQUEST_TIMEOUT_MS", raising=False)

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        load_settings(env_file=None)
