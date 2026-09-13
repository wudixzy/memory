"""DashScope embedding substitution; no credentials or network at import time."""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass

from memory_validation.network import disable_proxy_environment
from memory_validation.provider import ProviderError, _NoRedirect
from memory_validation.schemas import canonical
from memory_validation.telemetry import CallUsage


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str = "dashscope"
    region: str = "beijing"
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: str = "text-embedding-v4"
    dimensions: int = 1024
    encoding_format: str = "float"
    api_key_env: str = "DASHSCOPE_API_KEY"

    def __post_init__(self):
        expected = (
            "dashscope",
            "beijing",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "text-embedding-v4",
            1024,
            "float",
            "DASHSCOPE_API_KEY",
        )
        if tuple(asdict(self).values()) != expected or type(self.dimensions) is not int:
            raise ValueError("Embedding policy mismatch")

    @property
    def identity(self):
        return hashlib.sha256(canonical(asdict(self)).encode()).hexdigest()


PRICE = {
    "currency": "CNY",
    "input_per_million": 0.5,
    "queried": "2026-09-11",
    "source": "https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api",
    "free_allowance_assumed": False,
}


class DashScopeHTTPTransport:
    def __init__(self, *, allow_network=False, env_file=None, config=EmbeddingConfig()):
        if not allow_network:
            raise ProviderError("Embedding transport requires explicit network opt-in")
        disable_proxy_environment()
        key = os.environ.get(config.api_key_env, "").strip()
        if not key and env_file is not None:
            try:
                for line in env_file.read_text().splitlines():
                    name, sep, value = line.strip().removeprefix("export ").partition("=")
                    if sep and name.strip() == config.api_key_env:
                        key = value.strip().strip("\"'")
            except OSError:
                raise ProviderError("Cannot read credential file") from None
        if not key:
            raise ProviderError("DASHSCOPE_API_KEY is not configured")
        self.__key, self.config = key, config

    def __call__(self, payload):
        request = urllib.request.Request(
            self.config.base_url + "/embeddings",
            data=canonical(payload).encode(),
            method="POST",
            headers={"Authorization": "Bearer " + self.__key, "Content-Type": "application/json"},
        )
        try:
            # Explicit direct TLS connection, redirects refused, zero retries.
            with urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect()).open(
                request, timeout=30
            ) as response:
                raw = response.read().decode()
            parsed = json.loads(raw)
            if self.__key in raw or self.__key in canonical(parsed):
                raise ProviderError("Unsafe embedding response")
            return parsed
        except Exception:
            raise ProviderError("Embedding request failed; details withheld") from None


def vectors(response, count, dimensions):
    try:
        data = response["data"]
        if not isinstance(data, list) or len(data) != count:
            raise ValueError()
        ordered = {}
        for item in data:
            index, vector = item["index"], item["embedding"]
            if type(index) is not int or index not in range(count) or index in ordered:
                raise ValueError()
            if not isinstance(vector, list) or len(vector) != dimensions:
                raise ValueError()
            if any(type(v) not in (int, float) or not math.isfinite(v) for v in vector):
                raise ValueError()
            ordered[index] = vector
        return [ordered[i] for i in range(count)]
    except Exception:
        raise ProviderError("Invalid embedding shape, index or numeric value") from None


class EmbeddingProvider:
    def __init__(self, transport, config=EmbeddingConfig()):
        self.transport, self.config = transport, config

    def embed(self, texts, usage, *, phase="embedding", synthetic=False):
        if (
            not isinstance(texts, list)
            or not 1 <= len(texts) <= 10
            or any(not isinstance(t, str) or not t for t in texts)
        ):
            raise ValueError("Embedding requires 1 to 10 nonempty strings; no truncation")
        # Reserve documented maximum per item, not a guessed tokenizer count.
        usage.before_call(len(texts) * 8192, 0, embedding_cny=len(texts) * 8192 * 0.5 / 1e6)
        metadata = {"call_id": usage.new_call_id(), "phase": phase, "synthetic": synthetic}
        payload = {
            "model": self.config.model,
            "dimensions": self.config.dimensions,
            "encoding_format": self.config.encoding_format,
            "input": list(texts),
        }
        usage.emit_event(
            {
                **metadata,
                "event": "embedding_request",
                "request": payload,
                "embedding_identity": self.config.identity,
            }
        )
        started = time.monotonic()
        tokens, resolved, trusted = None, None, False
        issues = ("usage_unavailable",)
        status, error_category = "failed", "transport_error"
        model_matches = True
        try:
            try:
                response = self.transport(payload)
            except KeyboardInterrupt:
                raise KeyboardInterrupt() from None
            except Exception:
                raise ProviderError("Embedding transport failed; usage unavailable") from None
            raw = response.get("usage") if isinstance(response, dict) else None
            if isinstance(raw, dict):
                token_value = raw.get("prompt_tokens", raw.get("total_tokens"))
                if type(token_value) is int and token_value >= 0:
                    tokens, trusted, issues = token_value, True, ()
                else:
                    issues = ("input_tokens_missing_or_invalid",)
                if "total_tokens" in raw and (
                    type(raw["total_tokens"]) is not int or raw["total_tokens"] != tokens
                ):
                    trusted, issues = False, ("total_tokens_invalid_or_inconsistent",)
            if isinstance(response, dict) and isinstance(response.get("model"), str):
                resolved = response["model"]
            # Absent identity stays unavailable; an explicit different identity
            # invalidates the requested-model price, independently of token usage.
            model_matches = resolved is None or resolved == self.config.model
            error_category = "invalid_vectors" if model_matches else "model_mismatch"
            output = vectors(response, len(texts), self.config.dimensions)
            error_category = "response_logging_failed" if model_matches else "model_mismatch"
            usage.emit_event(
                {
                    **metadata,
                    "event": "embedding_response",
                    "vectors": output,
                    "embedding_identity": self.config.identity,
                }
            )
            if not model_matches:
                raise ProviderError("Embedding resolved model mismatch")
            status = "completed" if trusted else "usage_uncertain"
            error_category = None if trusted else "usage_unavailable_or_invalid"
        finally:
            interrupted = isinstance(sys.exc_info()[1], KeyboardInterrupt)
            if interrupted:
                status, error_category = "interrupted", "interrupted"
            accounting_trusted = trusted and model_matches
            call = CallUsage(
                tokens,
                0,
                0,
                time.monotonic() - started,
                provider="dashscope",
                requested_model=self.config.model,
                resolved_model=resolved,
                kind="embedding",
                currency="CNY",
                pricing_source=PRICE["source"]
                + " (2026-09-11; CNY 0.5/million input; no free allowance)",
                input_count=len(texts),
                estimated_cost_cny=(0 if synthetic else tokens * 0.5 / 1e6)
                if accounting_trusted
                else None,
                accounting_trusted=accounting_trusted,
                token_usage_trusted=trusted,
                error_category=error_category,
                usage_issues=issues,
                status=status,
                **metadata,
            )
            try:
                usage.record(call)
            except Exception:
                if not interrupted:
                    raise
        if not trusted:
            raise ProviderError("Embedding accounting unavailable; further calls blocked")
        return output


def langchain_embedding(provider, usage, *, synthetic=False):
    """Only import the installed upstream dependency when explicitly connecting it."""
    from langchain_core.embeddings import Embeddings

    class Bridge(Embeddings):
        identity = provider.config.identity

        def embed_documents(self, texts):
            if provider.config.identity != self.identity:
                raise ProviderError("Embedding retrieval identity changed")
            # Explicit counted batching; no truncation, normalization or cache.
            return [
                v
                for i in range(0, len(texts), 10)
                for v in provider.embed(
                    texts[i : i + 10], usage, phase="skill_documents", synthetic=synthetic
                )
            ]

        def embed_query(self, text):
            if provider.config.identity != self.identity:
                raise ProviderError("Embedding retrieval identity changed")
            return provider.embed([text], usage, phase="skill_query", synthetic=synthetic)[0]

    return Bridge()
