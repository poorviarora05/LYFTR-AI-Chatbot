from unittest.mock import patch
from types import SimpleNamespace

import llm_service


def mock_response():
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="This is a simulated AI response."
                )
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=12,
            completion_tokens=8
        ),
        _hidden_params={"cache_hit": False}
    )


MESSAGES = [
    {"role": "user", "content": "Hello"}
]


def test_successful_response():
    with patch.object(
        llm_service, "API_KEYS", ["test1", "test2"]
    ), patch(
        "llm_service.litellm.completion",
        return_value=mock_response()
    ):
        result = llm_service.generate_response(MESSAGES)

        assert result["reply"]
        assert result["metadata"]["key_id"] == "key_1"
        assert result["metadata"]["input_tokens"] == 12
        assert result["metadata"]["output_tokens"] == 8


def test_successful_failover():
    with patch.object(
        llm_service, "API_KEYS", ["test1", "test2"]
    ), patch.object(
        llm_service, "ENABLE_FAILURE_SIMULATION", True
    ), patch(
        "llm_service.litellm.completion",
        return_value=mock_response()
    ):
        result = llm_service.generate_response(
            MESSAGES, "key_1=429"
        )

        assert result["metadata"]["key_id"] == "key_2"
        assert result["metadata"]["fallback_attempts"] == 1


def test_cache_metadata():
    response = mock_response()
    response._hidden_params["cache_hit"] = True

    with patch.object(
        llm_service, "API_KEYS", ["test1", "test2"]
    ), patch(
        "llm_service.litellm.completion",
        return_value=response
    ):
        result = llm_service.generate_response(MESSAGES)

        assert result["metadata"]["resolution_source"] == "LLM_CACHE"
        assert result["metadata"]["key_id"] is None
        assert result["metadata"]["fallback_attempts"] == 0