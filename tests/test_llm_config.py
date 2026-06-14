import asyncio

import httpx
import pytest

from world_cafe.llm import (
    DEFAULT_OPENAI_BASE_URL,
    DEFAULT_OPENAI_MODEL,
    OpenAICafeLLM,
    auth_tokens_from_env,
    base_url_from_env,
    model_from_env,
)


def test_dashscope_defaults_are_used_without_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "OPENAI_BASE_URL",
        "DASHSCOPE_BASE_URL",
        "ANTHROPIC_BASE_URL",
        "OPENAI_MODEL",
        "DASHSCOPE_MODEL",
        "ANTHROPIC_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)

    assert base_url_from_env() == DEFAULT_OPENAI_BASE_URL
    assert model_from_env() == DEFAULT_OPENAI_MODEL


def test_auth_tokens_from_env_accepts_comma_separated_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEYS", "key-a, key-b; key-c")
    monkeypatch.setenv("OPENAI_API_KEY", "key-a")

    assert auth_tokens_from_env() == ["key-a", "key-b", "key-c"]


@pytest.mark.asyncio
async def test_openai_client_rotates_auth_tokens() -> None:
    seen_tokens: list[str] = []
    llm = OpenAICafeLLM(
        auth_tokens=["key-a", "key-b", "key-c"],
        base_url="https://example.test/v1",
        model="qwen-plus",
    )

    async def fake_post(_payload: dict, headers: dict[str, str]) -> httpx.Response:
        seen_tokens.append(headers["authorization"].removeprefix("Bearer "))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
            request=httpx.Request("POST", "https://example.test/v1/chat/completions"),
        )

    llm._post_with_retries = fake_post  # type: ignore[method-assign]

    await asyncio.gather(*(llm.agenerate("system", "user") for _ in range(5)))

    assert seen_tokens == ["key-a", "key-b", "key-c", "key-a", "key-b"]
