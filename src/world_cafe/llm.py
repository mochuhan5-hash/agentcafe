from __future__ import annotations

import hashlib
import json
import os
import asyncio
from dataclasses import dataclass
from typing import Protocol

import httpx

from world_cafe.state import TABLEMEMORY_USAGE_DESCRIPTION


DEFAULT_OPENAI_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_OPENAI_MODEL = "qwen-plus"


def auth_tokens_from_env() -> list[str]:
    return _split_auth_tokens(
        os.getenv("OPENAI_API_KEYS"),
        os.getenv("DASHSCOPE_API_KEYS"),
        os.getenv("ANTHROPIC_AUTH_TOKENS"),
        os.getenv("OPENAI_API_KEY"),
        os.getenv("DASHSCOPE_API_KEY"),
        os.getenv("ANTHROPIC_AUTH_TOKEN"),
    )


def configured_auth_token_count() -> int:
    return len(auth_tokens_from_env())


def base_url_from_env() -> str:
    return (
        os.getenv("OPENAI_BASE_URL")
        or os.getenv("DASHSCOPE_BASE_URL")
        or os.getenv("ANTHROPIC_BASE_URL")
        or DEFAULT_OPENAI_BASE_URL
    )


def model_from_env() -> str:
    return (
        os.getenv("OPENAI_MODEL")
        or os.getenv("DASHSCOPE_MODEL")
        or os.getenv("ANTHROPIC_MODEL")
        or DEFAULT_OPENAI_MODEL
    )


def _split_auth_tokens(*values: str | None) -> list[str]:
    tokens: list[str] = []
    for value in values:
        if not value:
            continue
        raw_value = value.strip()
        if not raw_value:
            continue
        candidates: list[str]
        if raw_value.startswith("["):
            try:
                loaded = json.loads(raw_value)
            except json.JSONDecodeError:
                loaded = None
            if isinstance(loaded, list):
                candidates = [str(item) for item in loaded]
            else:
                candidates = [raw_value]
        else:
            normalized = raw_value.replace(";", ",").replace("\n", ",")
            candidates = normalized.split(",")
        for candidate in candidates:
            token = candidate.strip().strip('"').strip("'")
            if token and token not in tokens:
                tokens.append(token)
    return tokens


class CafeLLM(Protocol):
    async def agenerate(self, system: str, user: str) -> str:
        """Generate text for a world-cafe step."""


@dataclass
class DryRunCafeLLM:
    """Deterministic local model for smoke tests and demos without API keys."""

    async def agenerate(self, system: str, user: str) -> str:
        digest = hashlib.sha1(f"{system}\n{user}".encode("utf-8")).hexdigest()[:8]
        if "## opening" in user:
            return (
                "## opening\n"
                "- Which user situations are most likely to be hidden by average descriptions?\n"
                f"- Which disagreement could most change how we understand the problem? (trace {digest})\n\n"
                "## question_seeds\n"
                "- Which user situations are most likely to be hidden by average descriptions?\n"
                "- Which disagreement could most change how we understand the problem?\n"
            )
        if "visible closing note" in system or "closing note" in user:
            return (
                "- Settling: the discussion is moving abstract judgments into observable situations.\n"
                "- Unclear: evidence strength, edge users, and stakeholder boundaries need sharper treatment.\n"
                "- Tension: quick convergence is still pulling against keeping disagreement alive.\n"
                f"- Carry forward: next round should ask which weak signal can open a **new design opportunity**. (trace {digest})"
            )
        if '"formatmemory"' in user:
            return json.dumps(
                {
                    "tablememory_usage_description": TABLEMEMORY_USAGE_DESCRIPTION,
                    "formatmemory": {
                        "table_question": "Original table question",
                        "round_index": 1,
                        "repeated_themes": ["Evidence, situations, and constraints need to be discussed together."],
                        "minority_inspiring_views": ["A minority view warns against averaging every user journey."],
                        "unresolved_tensions": ["There is tension between creative divergence and practical constraints."],
                    },
                    "next_round_question_seeds": ["Which weak signal could open a new problem reframe?"],
                },
                ensure_ascii=False,
            )
        if '"agent_generated_memory"' in user:
            return json.dumps(
                {
                    "agent": {
                        "id": "agent",
                        "name": "speaking agent",
                        "role": "participant",
                        "skills": ["reframing"],
                    },
                    "agent_generated_memory": {
                        "skill_lens": "reframing",
                        "personal_insight": "Do not treat the previous table's consensus as the next table's premise.",
                    },
                },
                ensure_ascii=False,
            )
        if "global harvest" in system.lower():
            return (
                "Design Insights:\n"
                "### Insight 1\n"
                "1. User need: Users need abstract issues translated into testable actions without repeating the same discussion in later rounds.\n"
                "2. Reframed design problem: How might open exploration preserve edge-user signals and turn them into testable **design opportunities**?\n"
                "3. Up to three next design directions:\n"
                "- Select one edge-user breakdown as the entry point for reframing.\n"
                "- Define a minimum viable experiment and observation metric for each table.\n"
            )
        return (
            f"I will push the discussion one step forward. The most useful move here is to turn an abstract judgment into a small testable hypothesis. "
            f"World Cafe is valuable because different experiences collide before the group converges, leaving clues for the next experiment. (trace {digest})"
        )


class OpenAICafeLLM:
    """Minimal OpenAI-compatible Chat Completions client."""

    def __init__(
        self,
        *,
        auth_token: str = "",
        auth_tokens: list[str] | tuple[str, ...] | None = None,
        base_url: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1600,
        timeout: float = 120.0,
        concurrency: int = 3,
        retries: int = 2,
    ) -> None:
        tokens = _split_auth_tokens(auth_token, *(auth_tokens or []))
        if not tokens:
            raise ValueError("OPENAI_API_KEY or OPENAI_API_KEYS is required")
        self.auth_tokens = tokens
        self.auth_token = tokens[0]
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.retries = retries
        self._semaphore = asyncio.Semaphore(max(1, concurrency))
        self._auth_token_index = 0
        self._auth_token_lock = asyncio.Lock()

    @classmethod
    def from_env(
        cls,
        *,
        temperature: float = 0.7,
        max_tokens: int = 1600,
        timeout: float | None = None,
    ) -> "OpenAICafeLLM":
        return cls(
            auth_tokens=auth_tokens_from_env(),
            base_url=base_url_from_env(),
            model=model_from_env(),
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout if timeout is not None else float(os.getenv("WORLD_CAFE_LLM_TIMEOUT", "180")),
            concurrency=int(os.getenv("WORLD_CAFE_LLM_CONCURRENCY", "3")),
            retries=int(os.getenv("WORLD_CAFE_LLM_RETRIES", "2")),
        )

    async def agenerate(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        async with self._semaphore:
            auth_token = await self._next_auth_token()
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {auth_token}",
            }
            response = await self._post_with_retries(payload, headers)
        data = response.json()
        return _extract_text(data)

    async def _next_auth_token(self) -> str:
        if len(self.auth_tokens) == 1:
            return self.auth_tokens[0]
        async with self._auth_token_lock:
            token = self.auth_tokens[self._auth_token_index % len(self.auth_tokens)]
            self._auth_token_index += 1
            return token

    async def _post_with_retries(self, payload: dict, headers: dict[str, str]) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                chat_url = self._chat_completions_url()
                response = await asyncio.to_thread(
                    self._post_sync,
                    chat_url,
                    payload,
                    headers,
                )
                if response.status_code in (401, 403, 429, 500, 502, 503):
                    # Try next API key on auth/rate/server errors
                    if len(self.auth_tokens) > 1 and attempt < self.retries:
                        next_token = await self._next_auth_token()
                        headers = {**headers, "authorization": f"Bearer {next_token}"}
                        last_error = RuntimeError(
                            f"AI API request failed with HTTP {response.status_code}, "
                            f"retrying with next key (attempt {attempt + 1}/{self.retries + 1})"
                        )
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                    raise RuntimeError(
                        "AI API request failed "
                        f"with HTTP {response.status_code}: {response.text[:500]}"
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
                if len(self.auth_tokens) > 1:
                    next_token = await self._next_auth_token()
                    headers = {**headers, "authorization": f"Bearer {next_token}"}
                await asyncio.sleep(1.5 * (attempt + 1))
        if last_error is None:
            raise RuntimeError("AI API request failed for an unknown reason")
        raise last_error

    def _chat_completions_url(self) -> str:
        base_url = self.base_url.rstrip("/")
        if base_url.endswith("/v1"):
            return f"{base_url}/chat/completions"
        return f"{base_url}/v1/chat/completions"

    def _post_sync(self, url: str, payload: dict, headers: dict[str, str]) -> httpx.Response:
        with httpx.Client(timeout=self.timeout) as client:
            return client.post(url, json=payload, headers=headers)


AnthropicCafeLLM = OpenAICafeLLM


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
