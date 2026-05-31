from __future__ import annotations

import hashlib
import json
import os
import asyncio
from dataclasses import dataclass
from typing import Protocol

import httpx


class CafeLLM(Protocol):
    async def agenerate(self, system: str, user: str) -> str:
        """Generate text for a world-cafe step."""


@dataclass
class DryRunCafeLLM:
    """Deterministic local model for smoke tests and demos without API keys."""

    async def agenerate(self, system: str, user: str) -> str:
        digest = hashlib.sha1(f"{system}\n{user}".encode("utf-8")).hexdigest()[:8]
        if "桌长" in system or "host" in system.lower():
            return (
                "## synthesis\n"
                f"本轮形成了一个可继续推进的综合观点：先识别真实参与者，再围绕问题建立可验证的小实验。（trace {digest}）\n\n"
                "## key_insights\n"
                "- 把问题拆成参与者、场景、约束和可行动假设。\n"
                "- 让分歧显性化，比过早达成共识更有价值。\n"
                "- 下一轮需要把洞察连接到可观察证据。\n\n"
                "## open_questions\n"
                "- 哪些利益相关者还没有被纳入？\n"
                "- 哪个假设最值得优先验证？\n\n"
                "## tensions\n"
                "- 创造性发散与落地约束之间存在张力。\n"
            )
        if "全局 harvest" in system or "global harvest" in system.lower():
            return (
                "## Shared Patterns\n"
                "- 多桌都在从抽象议题转向可验证行动。\n"
                "- 桌长记忆帮助后续轮次避免重复讨论。\n\n"
                "## Cross-table Tensions\n"
                "- 开放探索与阶段性收束需要节奏控制。\n\n"
                "## Next Experiments\n"
                "- 每桌选择一个最小可行实验，并定义观察指标。\n"
            )
        return (
            f"我先接着现场的讨论往前推一步。当前问题里最值得抓住的，是把抽象判断转成一个可验证的小假设。"
            f"世界咖啡的价值不在于马上统一意见，而在于让不同经验彼此碰撞，留下下一步可以试的线索。（trace {digest}）"
        )


class AnthropicCafeLLM:
    """Minimal Anthropic Messages client for Anthropic-compatible gateways."""

    def __init__(
        self,
        *,
        auth_token: str,
        base_url: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1600,
        timeout: float = 120.0,
        concurrency: int = 3,
        retries: int = 1,
    ) -> None:
        if not auth_token:
            raise ValueError("ANTHROPIC_AUTH_TOKEN is required")
        self.auth_token = auth_token
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.retries = retries
        self._semaphore = asyncio.Semaphore(max(1, concurrency))

    @classmethod
    def from_env(cls, *, temperature: float = 0.7, max_tokens: int = 1600) -> "AnthropicCafeLLM":
        return cls(
            auth_token=os.getenv("ANTHROPIC_AUTH_TOKEN", ""),
            base_url=os.getenv("ANTHROPIC_BASE_URL", "http://143.198.222.179:8317"),
            model=os.getenv("ANTHROPIC_MODEL", "gpt-5.5"),
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=float(os.getenv("WORLD_CAFE_LLM_TIMEOUT", "180")),
            concurrency=int(os.getenv("WORLD_CAFE_LLM_CONCURRENCY", "3")),
            retries=int(os.getenv("WORLD_CAFE_LLM_RETRIES", "1")),
        )

    async def agenerate(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
            "x-api-key": self.auth_token,
            "authorization": f"Bearer {self.auth_token}",
        }
        async with self._semaphore:
            response = await self._post_with_retries(payload, headers)
        data = response.json()
        return _extract_text(data)

    async def _post_with_retries(self, payload: dict, headers: dict[str, str]) -> httpx.Response:
        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.retries + 1):
                try:
                    response = await client.post(
                        f"{self.base_url}/v1/messages",
                        json=payload,
                        headers=headers,
                    )
                    if response.status_code >= 400:
                        raise RuntimeError(
                            "AI API request failed "
                            f"with HTTP {response.status_code}: {response.text[:500]}"
                        )
                    return response
                except httpx.TimeoutException as exc:
                    last_error = TimeoutError(
                        f"AI API request timed out after {self.timeout:.0f}s "
                        f"(attempt {attempt + 1}/{self.retries + 1}, model={self.model})"
                    )
                except httpx.HTTPError as exc:
                    last_error = RuntimeError(f"AI API request failed: {exc!r}")
                if attempt < self.retries:
                    await asyncio.sleep(1.5 * (attempt + 1))
        if last_error is None:
            raise RuntimeError("AI API request failed for an unknown reason")
        raise last_error


class LangChainCafeLLM:
    def __init__(self, model: str, temperature: float = 0.7):
        from langchain.chat_models import init_chat_model

        self.model_name = model
        self.model = init_chat_model(model, temperature=temperature)

    async def agenerate(self, system: str, user: str) -> str:
        response = await self.model.ainvoke(
            [
                ("system", system),
                ("user", user),
            ]
        )
        content = response.content
        if isinstance(content, str):
            return content
        return json.dumps(content, ensure_ascii=False)


def _extract_text(data: dict) -> str:
    if isinstance(data.get("content"), str):
        return data["content"]
    content = data.get("content")
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif isinstance(item.get("content"), str):
                    parts.append(item["content"])
            elif isinstance(item, str):
                parts.append(item)
        if parts:
            return "\n".join(parts)

    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message", {})
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"]
            if isinstance(first.get("text"), str):
                return first["text"]

    return json.dumps(data, ensure_ascii=False)
