"""Explicit opt-in HTTP transport. Credentials never enter config or artifacts."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from dataclasses import replace
from pathlib import Path

from memory_validation.network import disable_proxy_environment
from memory_validation.schemas import ModelConfig, canonical
from memory_validation.telemetry import CallUsage, UsageTracker


class ProviderError(RuntimeError):
    pass


def load_key(env_file: Path | None = None) -> str:
    """Read only DEEPSEEK_KEY, without shell evaluation or modifying os.environ."""
    key = os.environ.get("DEEPSEEK_KEY", "").strip()
    if not key and env_file is not None:
        try:
            for line in env_file.read_text().splitlines():
                name, separator, value = line.strip().removeprefix("export ").partition("=")
                if separator and name.strip() == "DEEPSEEK_KEY":
                    key = value.strip().strip("\"'")
        except OSError:
            raise ProviderError("Cannot read credential file") from None
    if not key:
        raise ProviderError("DEEPSEEK_KEY is not configured")
    return key


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProviderError("Provider redirect refused")


class DeepSeekHTTPTransport:
    def __init__(self, *, allow_network: bool = False, env_file: Path | None = None):
        if not allow_network:
            raise ProviderError("Real provider transport requires explicit network opt-in")
        disable_proxy_environment()
        self.__key = load_key(env_file)

    def __call__(self, payload: dict) -> dict:
        request = urllib.request.Request(
            "https://api.deepseek.com/chat/completions",
            data=canonical(payload).encode(),
            headers={"Authorization": "Bearer " + self.__key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect()).open(
                request, timeout=60
            ) as response:
                raw = response.read().decode()
            # A credential echoed by a remote service must not reach callers.
            parsed = json.loads(raw)
            if self.__key in raw or self.__key in canonical(parsed):
                raise ProviderError("Unsafe provider response")
            return parsed
        except Exception:
            # Never propagate response bodies, headers, URLs or original exceptions.
            raise ProviderError("DeepSeek request failed; response details withheld") from None


def visible_message(message: dict) -> dict:
    """Allowlist content/tool calls; discard reasoning_content and provider internals."""
    result = {
        key: message[key] for key in ("role", "content", "tool_call_id", "name") if key in message
    }
    if message.get("tool_calls") is not None:
        result["tool_calls"] = [
            {
                "id": item.get("id"),
                "type": item.get("type"),
                "function": {k: item.get("function", {}).get(k) for k in ("name", "arguments")},
            }
            for item in message["tool_calls"]
        ]
    elif "tool_calls" in message:
        result["tool_calls"] = None
    return json.loads(canonical(result))


def visible_tools(tools: list) -> list:
    return json.loads(
        canonical(
            [
                {
                    "type": tool.get("type"),
                    "function": {
                        key: tool.get("function", {})[key]
                        for key in ("name", "description", "parameters", "strict")
                        if key in tool.get("function", {})
                    },
                }
                for tool in tools
            ]
        )
    )


def parse_usage(response: dict, latency: float, **metadata) -> CallUsage:
    """Keep independently valid counts; never serialize invalid provider values."""
    issues = []
    raw = response.get("usage")
    if not isinstance(raw, dict):
        issues.append("usage_missing_or_invalid")
        raw = {}

    def count(name, value, required=False):
        if value is None:
            if required:
                issues.append(name + "_missing")
            return None
        if type(value) is not int or value < 0:
            issues.append(name + "_invalid")
            return None
        return value

    input_tokens = count("input_tokens", raw.get("prompt_tokens"), True)
    output_tokens = count("output_tokens", raw.get("completion_tokens"), True)
    cached = raw.get("prompt_cache_hit_tokens")
    if cached is None:
        details = raw.get("prompt_tokens_details")
        if isinstance(details, dict):
            cached = details.get("cached_tokens")
        elif details is not None:
            issues.append("prompt_tokens_details_invalid")
    cached = count("cached_input_tokens", cached)
    if cached is not None and input_tokens is not None and cached > input_tokens:
        issues.append("cached_input_tokens_exceed_input")
        cached = None
    model = response.get("model")
    return CallUsage(
        input_tokens,
        output_tokens,
        cached,
        latency,
        resolved_model=model if isinstance(model, str) else None,
        accounting_trusted=not issues,
        usage_issues=tuple(issues),
        status="usage_uncertain" if issues else "completed",
        **metadata,
    )


class DeepSeekProvider:
    def __init__(self, transport, config: ModelConfig = ModelConfig(), *, accepted_models=None):
        self.transport, self.config = transport, config
        self.accepted_models = accepted_models

    def complete(
        self,
        messages: list[dict],
        usage: UsageTracker,
        *,
        max_tokens: int = 128,
        input_upper_bound: int = 1_048_576,
        tools: list | None = None,
        on_visible=None,
        phase: str = "unspecified",
        synthetic: bool = False,
    ) -> dict:
        """Caller supplies a verified token upper bound or reserves the context cap.

        A serialized-byte heuristic is NOT a proven tokenizer bound. Reserving the
        entire context is the conservative default. No automatic retries.
        """
        if type(max_tokens) is not int or not 1 <= max_tokens <= 393216:
            raise ValueError("Invalid output cap")
        payload = {
            "model": self.config.model,
            "thinking": {"type": "disabled"},
            "temperature": 0,
            "max_tokens": max_tokens,
            "stream": False,
            "messages": [visible_message(message) for message in messages],
        }
        if tools is not None:
            payload["tools"] = visible_tools(tools)
        usage.before_call(input_upper_bound, max_tokens)
        metadata = {"call_id": usage.new_call_id(), "phase": phase, "synthetic": synthetic}
        # Persist before entering transport. This event records intent, not proof
        # of server receipt; only usage records count transport entries.
        usage.emit_event({**metadata, "event": "request", "request": payload})
        started = time.monotonic()
        call = None
        try:
            try:
                response = self.transport(payload)
            except KeyboardInterrupt:
                raise KeyboardInterrupt() from None
            except Exception:
                raise ProviderError("Provider call failed; usage unavailable") from None
            # Accounting validation is independent of visible response delivery.
            if isinstance(response, dict):
                call = parse_usage(response, time.monotonic() - started, **metadata)
                if (
                    self.accepted_models is not None
                    and call.resolved_model is not None
                    and call.resolved_model not in self.accepted_models
                ):
                    call = replace(
                        call,
                        accounting_trusted=False,
                        status="failed",
                        error_category="model_mismatch",
                        usage_issues=(*call.usage_issues, "model_price_unknown"),
                    )
            try:
                message = visible_message(response["choices"][0]["message"])
            except Exception:
                raise ProviderError("Visible provider response is invalid") from None
            usage.emit_event({**metadata, "event": "response", "message": message})
            if call is not None and call.error_category == "model_mismatch":
                raise ProviderError("Generation resolved model mismatch")
            if on_visible is not None:
                on_visible(message)
        finally:
            if call is None:
                call = CallUsage(
                    None,
                    None,
                    None,
                    time.monotonic() - started,
                    status="failed_usage_unavailable",
                    accounting_trusted=False,
                    usage_issues=("usage_unavailable",),
                    **metadata,
                )
            # Single accounting site, including BaseException/KeyboardInterrupt.
            interrupted = isinstance(sys.exc_info()[1], KeyboardInterrupt)
            try:
                usage.record(call)
            except Exception:
                if not interrupted:
                    raise
        if not call.accounting_trusted:
            raise ProviderError("Provider response has no usable token accounting")
        return message
