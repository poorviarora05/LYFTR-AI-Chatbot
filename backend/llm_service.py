import os
import time
import logging

import litellm

from dotenv import load_dotenv
from litellm.caching import Cache

load_dotenv()

logger = logging.getLogger(__name__)

litellm.suppress_debug_info = True
litellm.set_verbose = False


# Load API keys
API_KEYS = [
    key.strip()
    for key in os.getenv("LLM_API_KEYS", "").split(",")
    if key.strip()
]


# Load model configuration
MODEL = os.getenv(
    "LLM_MODEL",
    "gemini/gemini-2.5-flash"
).strip()


# Enable failure simulation
ENABLE_FAILURE_SIMULATION = (
    os.getenv(
        "ENABLE_FAILURE_SIMULATION",
        "false"
    ).lower() == "true"
)


# Default system prompt
DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful AI assistant. "
    "Provide clear, accurate and concise answers. "
    "Remember the context of the conversation."
)


# Enable LiteLLM built-in cache
litellm.cache = Cache(type="local")


class AllProvidersUnavailable(Exception):
    pass


def get_key_count():
    return len(API_KEYS)


def parse_failure_header(header):

    failures = {}

    if not ENABLE_FAILURE_SIMULATION or not header:
        return failures

    for item in header.split(","):

        try:
            key_id, status = item.strip().split("=")
            status = int(status)
            key_id = key_id.strip()

            if status in [429, 500, 502, 503]:
                failures[key_id] = status

        except ValueError:
            continue

    return failures


def generate_response(messages, failure_header=None):

    start_time = time.perf_counter()

    failures = parse_failure_header(failure_header)

    fallback_attempts = 0

    if not API_KEYS:
        logger.error("No API credentials configured")

        raise AllProvidersUnavailable(
            "all providers unavailable"
        )

    for index, api_key in enumerate(API_KEYS):

        key_id = f"key_{index + 1}"

        # Check simulated failures
        simulated_status = failures.get(
            key_id,
            failures.get("*")
        )

        if simulated_status:

            fallback_attempts += 1

            logger.warning(
                "%s simulated failure: %s",
                key_id,
                simulated_status
            )

            continue

        try:

            logger.info(
                "Attempting inference with %s",
                key_id
            )

            # Generate response through LiteLLM
            response = litellm.completion(
                model=MODEL,
                messages=messages,
                api_key=api_key,
                temperature=0.3,
                max_tokens=2048,
                timeout=30,
                num_retries=0,
                caching=not bool(failures),
                cache={
                    "no-cache": bool(failures),
                    "no-store": bool(failures)
                }
            )

            reply = response.choices[0].message.content

            if not reply or not reply.strip():

                fallback_attempts += 1

                logger.warning(
                    "%s returned an empty response",
                    key_id
                )

                continue

            # Detect cache hit
            hidden_params = (
                getattr(response, "_hidden_params", {})
                or {}
            )

            cache_hit = bool(
                hidden_params.get("cache_hit", False)
            )

            # Extract token usage
            usage = getattr(response, "usage", None)

            input_tokens = int(
                getattr(usage, "prompt_tokens", 0) or 0
            )

            output_tokens = int(
                getattr(usage, "completion_tokens", 0) or 0
            )

            # Calculate latency
            latency_ms = int(
                (time.perf_counter() - start_time) * 1000
            )

            metadata = {
                "resolution_source": (
                    "LLM_CACHE"
                    if cache_hit
                    else "LIVE_INFERENCE"
                ),

                "model": MODEL,

                "latency_ms": latency_ms,

                "input_tokens": input_tokens,

                "output_tokens": output_tokens,

                "key_id": (
                    None if cache_hit else key_id
                ),

                "fallback_attempts": (
                    0 if cache_hit else fallback_attempts
                )
            }

            logger.info(
                "Response successful | Source: %s | "
                "Latency: %s ms",
                metadata["resolution_source"],
                latency_ms
            )

            return {
                "reply": reply,
                "metadata": metadata
            }

        except Exception as error:

            fallback_attempts += 1

            status_code = getattr(
                error,
                "status_code",
                "unknown"
            )

            logger.warning(
                "%s failed: %s | Status: %s | Model: %s",
                key_id,
                type(error).__name__,
                status_code,
                MODEL
            )

            provider_response = getattr(
                error,
                "response",
                None
            )

            if provider_response is not None:

                logger.warning(
                    "Provider HTTP status: %s",
                    getattr(
                        provider_response,
                        "status_code",
                        "unknown"
                    )
                )

            if status_code == 404:

                logger.error(
                    "Configured model or provider endpoint "
                    "could not be found."
                )

            elif status_code == 401:

                logger.error(
                    "Provider authentication failed."
                )

            elif status_code == 429:

                logger.warning(
                    "Provider rate limit exceeded."
                )

            continue

    logger.error(
        "All configured providers failed. Attempts: %s",
        fallback_attempts
    )

    raise AllProvidersUnavailable(
        "all providers unavailable"
    )