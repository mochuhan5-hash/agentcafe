from __future__ import annotations

import hashlib
import json
import os
import asyncio
from dataclasses import dataclass
from typing import Protocol

import httpx


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
                "- 哪些使用者处境最容易被平均化描述遮住？\n"
                f"- 哪个分歧最可能改变我们理解问题的方式？（trace {digest}）\n\n"
                "## question_seeds\n"
                "- 哪些使用者处境最容易被平均化描述遮住？\n"
                "- 哪个分歧最可能改变我们理解问题的方式？\n"
            )
        if "本轮可见结束语" in system or "本轮结束语" in user:
            return (
                "- 成形：讨论开始把抽象判断落到可观察情境。\n"
                "- 模糊：证据强度、边缘用户和利益相关者边界还没说透。\n"
                "- 冲突：快速收束和保留分歧之间仍有拉扯。\n"
                f"- 带走：下一轮追问哪个弱信号能打开**新的设计机会**？（trace {digest}）"
            )
        if "host_memory_update_instruction" in user:
            return json.dumps(
                {
                    "synthesis": f"本轮桌面记忆显示，参与者正在把抽象判断转成可观察的情境差异。（trace {digest}）",
                    "key_insights": [
                        "把问题拆成参与者、场景、约束和可行动假设。",
                        "让分歧显性化，比过早达成共识更有价值。",
                    ],
                    "stable_patterns": ["证据、场景和约束需要一起讨论。"],
                    "incomplete_or_weak_patterns": ["边缘用户的差异仍缺少具体证据。"],
                    "contested_points": ["先收束行动假设，还是继续保留分歧。"],
                    "open_questions": [
                        "哪些利益相关者还没有被纳入？",
                        "哪个假设最值得优先验证？",
                    ],
                    "tensions": ["创造性发散与落地约束之间存在张力。"],
                    "blind_spots_or_ambiguities": ["未纳入角色是否会改变问题边界。"],
                    "source_context_anchor": ["用户上传材料中的任务背景与用户痛点。"],
                    "host_memory_update_instruction": "下一轮优先观察重复主题是否转化为新的问题重构方向。",
                    "llm_generated_table_memory_template": {
                        "template_name": "dynamic_table_memory",
                        "fields": {
                            "resonant_patterns": "跨发言重复出现的模式",
                            "minority_shifts": "少数但改变理解方向的观点",
                        },
                    },
                    "host_generated_table_memory": {
                        "resonant_patterns": ["证据、场景和约束需要一起讨论。"],
                        "minority_shifts": ["少数观点提醒不要把所有用户旅程平均化。"],
                    },
                    "cumulative_pattern_evolution": "本桌正从抽象问题判断，逐步演化到围绕证据、场景、约束和未纳入角色来重构问题。",
                    "recurring_patterns_across_rounds": ["证据、场景和约束需要一起讨论。"],
                    "emerging_or_fading_signals": ["少数观点提醒不要把所有用户旅程平均化。"],
                    "unresolved_tensions_over_time": ["创造性发散与落地约束之间存在张力。"],
                    "round_pattern_delta": "本轮相对累计历史的新变化是：从泛泛问题判断转向可观察证据和未纳入角色。",
                    "next_round_question_seeds": ["哪个弱信号可能打开新的问题重构？"],
                },
                ensure_ascii=False,
            )
        if "memory_update_instruction" in user and "bridge_intent" in user:
            return json.dumps(
                {
                    "memory_update_instruction": "只保留这个 agent 亲自参与后形成的迁移洞见。",
                    "llm_generated_memory_template": {
                        "template_name": "dynamic_agent_migrant_memory",
                        "fields": {
                            "personal_shift": "本轮改变了 agent 判断的内容",
                            "bridge_test": "到下一桌准备测试的连接",
                        },
                    },
                    "agent_generated_memory": {
                        "personal_shift": "不要把上一桌的共识当成新桌前提。",
                        "bridge_test": "测试用户旅程分歧是否能解释当前桌的系统张力。",
                    },
                    "bridge_intent": "把上一桌的用户旅程分歧带到下一桌，看看它是否揭示新的问题重构方向。",
                },
                ensure_ascii=False,
            )
        if "全局 harvest" in system or "global harvest" in system.lower():
            return (
                "## Shared Patterns\n"
                "- 多桌都在从抽象议题转向可验证行动。\n"
                "- 桌长记忆帮助后续轮次避免重复讨论。\n\n"
                "## Weak Signals\n"
                "- 少数观点提示：被平均化的边缘用户可能暴露新的设计机会。\n\n"
                "## Cross-table Tensions\n"
                "- 开放探索与阶段性收束需要节奏控制。\n\n"
                "## Next Experiments\n"
                "- 每桌选择一个最小可行实验，并定义观察指标。\n"
            )
        return (
            f"我先接着现场的讨论往前推一步。当前问题里最值得抓住的，是把抽象判断转成一个可验证的小假设。"
            f"世界咖啡的价值不在于马上统一意见，而在于让不同经验彼此碰撞，留下下一步可以试的线索。（trace {digest}）"
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
        retries: int = 1,
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
            retries=int(os.getenv("WORLD_CAFE_LLM_RETRIES", "1")),
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
