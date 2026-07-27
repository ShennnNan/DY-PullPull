from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Callable, Protocol
from urllib.request import Request, urlopen

from pullpull.article import RefinedArticle, RefineRequest, parse_refined


class JsonChatClient(Protocol):
    def complete_json(self, system_prompt: str, user_prompt: str) -> dict: ...


def _urlopen_bytes(request: Request, timeout: float) -> bytes:
    with urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.read()


@dataclass
class DeepSeekChatClient:
    api_key: str
    model: str = "deepseek-v4-pro"
    base_url: str = "https://api.deepseek.com"
    timeout: float = 300.0
    transport: Callable[[Request, float], bytes] = _urlopen_bytes

    @classmethod
    def from_environment(cls) -> "DeepSeekChatClient":
        api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("环境变量 DEEPSEEK_API_KEY 未配置")
        return cls(
            api_key=api_key,
            model=os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro"),
        )

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "thinking": {"type": "disabled"},
            "response_format": {"type": "json_object"},
            "max_tokens": 32768,
        }
        request = Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        envelope = json.loads(self.transport(request, self.timeout).decode("utf-8"))
        choices = envelope.get("choices") or []
        if not choices:
            raise RuntimeError("AI 响应缺少 choices")
        choice = choices[0]
        finish_reason = choice.get("finish_reason")
        if finish_reason not in (None, "stop"):
            raise RuntimeError(f"AI 响应未完整结束：{finish_reason}")
        content = str((choice.get("message") or {}).get("content") or "").strip()
        if not content:
            raise RuntimeError("AI 响应内容为空")
        result = json.loads(content)
        if not isinstance(result, dict):
            raise RuntimeError("AI 响应不是 JSON 对象")
        return result


class DeepSeekRefiner:
    SYSTEM_PROMPT = (
        "你是中文口述稿编辑。把输入中的 ASR 转写整理成严格 JSON。"
        "cleaned_transcript 必须保留全部实质信息和原有顺序，只修正明显同音字、"
        "英文术语、重复识别、漏字和断句；不得扩写、删减论点或加入外部事实。"
        "summary 用简体中文要点式概括核心观点，只能依据转写。"
        "输出键只能是 summary 和 cleaned_transcript。"
    )

    def __init__(self, client: JsonChatClient):
        self.client = client

    @classmethod
    def from_environment(cls) -> "DeepSeekRefiner":
        return cls(DeepSeekChatClient.from_environment())

    def refine(self, request: RefineRequest) -> RefinedArticle:
        user_prompt = json.dumps(
            {
                "title": request.title,
                "raw_transcript": request.raw_transcript,
                "required_json": {
                    "summary": "要点式核心观点",
                    "cleaned_transcript": "完整清洗原文",
                },
            },
            ensure_ascii=False,
        )
        return parse_refined(
            self.client.complete_json(self.SYSTEM_PROMPT, user_prompt)
        )
