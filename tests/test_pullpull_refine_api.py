import json

from pullpull.article import RefineRequest
from pullpull.refine_api import DeepSeekChatClient, DeepSeekRefiner


def _request():
    return RefineRequest(
        video_id="123",
        title="标题",
        source_url="https://www.douyin.com/video/123",
        author="作者",
        published_at="20260727",
        raw_transcript="这是原始转写",
    )


def test_deepseek_client_requests_json_without_exposing_key():
    seen = {}

    def transport(request, timeout):
        seen["url"] = request.full_url
        seen["headers"] = dict(request.header_items())
        seen["body"] = json.loads(request.data.decode("utf-8"))
        seen["timeout"] = timeout
        return json.dumps(
            {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                {
                                    "summary": "总结",
                                    "cleaned_transcript": "原文",
                                },
                                ensure_ascii=False,
                            )
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ).encode("utf-8")

    client = DeepSeekChatClient(
        api_key="secret",
        model="deepseek-v4-pro",
        transport=transport,
    )
    result = client.complete_json("system json", "user")

    assert result == {"summary": "总结", "cleaned_transcript": "原文"}
    assert seen["url"] == "https://api.deepseek.com/chat/completions"
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert seen["body"]["model"] == "deepseek-v4-pro"
    assert "secret" not in json.dumps(seen["body"])


def test_deepseek_refiner_maps_json_to_refined_article():
    class FakeClient:
        def complete_json(self, system_prompt, user_prompt):
            assert "JSON" in system_prompt
            assert "这是原始转写" in user_prompt
            return {"summary": "核心观点", "cleaned_transcript": "清理后的原文"}

    refined = DeepSeekRefiner(FakeClient()).refine(_request())

    assert refined.summary == "核心观点"
    assert refined.cleaned_transcript == "清理后的原文"
